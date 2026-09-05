"""LangGraph case organization: fetch_tools -> perceive -> retrieve -> adjudicate.

Memory rule (the whole design): anything a later node needs lives in
CaseState = shared memory, persisted per case by AsyncSqliteSaver at
storage/memory/graph.sqlite with thread_id = the content sha (so a repeat
submission resumes the same thread). Anything bulky or private — raw bytes,
frames, full-res arrays, retry counters — stays in the closure `ctx` dict
= non-shared memory and MUST never enter state. Nodes are thin wrappers
around the existing agent modules; stage logic lives in pipeline.run_*.
"""

from __future__ import annotations

import asyncio
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.features.analysis.agents import audio as audio_agent
from app.features.analysis.agents import forensics, meta, muse_client, sarvam, synthid
from app.features.analysis.agents import pipeline
from app.features.analysis.agents import visual as visual_agent


class CaseState(TypedDict, total=False):
    """Shared memory: only small JSON-safe values cross node boundaries."""

    modality: str
    source: str
    claimed_date: str | None
    caption: str
    entities: list[str]
    ocr_text: str
    perceptual: dict
    meta: dict
    tool: dict | None
    provenance: dict | None
    sarvam: dict | None
    search: dict
    shaped: dict
    errors: Annotated[list[str], add]


def _memory_path() -> Path:
    path = Path("storage/memory/graph.sqlite")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


async def run_case(
    *,
    modality: str,
    data: bytes,
    mime: str,
    source: str,
    claimed_date: str | None,
    thread_id: str,
    pre_sarvam: dict | None = None,
    progress: dict | None = None,
) -> dict:
    """Run one case through the graph; returns the shaped verdict dict.

    progress, when given, is a caller-owned mutable mapping updated with
    {"stage": ...} as each node completes — polled by the jobs endpoint.
    """
    ctx = {"data": data, "mime": mime, "frames": [], "frame_tools": []}

    def _mark(stage: str) -> None:
        if progress is not None:
            progress["stage"] = stage

    async def fetch_tools(state: CaseState) -> dict:
        warnings: list[str] = []
        _mark("fetch_tools")
        if modality == "video":
            try:
                meta_info = await asyncio.to_thread(meta.read, ctx["data"], ctx["mime"])
            except ValueError as exc:
                raise pipeline.AnalysisError(str(exc)) from exc
            duration = meta_info.get("duration_s")
            if duration and duration > pipeline._VIDEO_MAX_S:
                raise pipeline.AnalysisError(
                    f"Video is {duration:.0f}s, over the {pipeline._VIDEO_MAX_S}s cap."
                )
            frames = await asyncio.to_thread(
                pipeline._extract_frames, ctx["data"], settings.agent_max_frames
            )
            ctx["frames"] = frames
            frame_tools = list(
                await asyncio.gather(
                    *[asyncio.to_thread(forensics.examine, f) for f in frames]
                )
            )
            ctx["frame_tools"] = frame_tools
            provenance = await asyncio.to_thread(synthid.scan, frames[0]) if frames else None
            agg = {
                name: round(
                    sum(float((t.get("scores") or {}).get(name, 0.0)) for t in frame_tools)
                    / len(frame_tools),
                    3,
                )
                for name in ("ela", "dct", "noise", "copymove", "ghost", "blockiness", "spectrum", "fused_mean")
            }
            fused = [float((t.get("scores") or {}).get("fused_mean", 0.0)) for t in frame_tools]
            worst = frame_tools[max(range(len(frame_tools)), key=lambda i: fused[i])]
            tool = {
                "scores": agg,
                "artifacts": worst.get("artifacts", {}),
                "note": f"Mean over {len(frames)} frames; heatmaps from the worst frame.",
            }
            return {"meta": meta_info, "tool": tool, "provenance": provenance, "errors": warnings}
        if modality == "audio":
            sarvam_result = pre_sarvam
            if sarvam_result is None and settings.sarvam_api_key:
                try:
                    sarvam_result = await sarvam.transcribe(
                        ctx["data"], filename=pipeline._sarvam_filename(ctx["mime"])
                    )
                except sarvam.SarvamError as exc:
                    warnings.append(f"sarvam degraded to Muse-only: {exc}")
            elif sarvam_result is None:
                warnings.append("sarvam skipped: no key")
            try:
                meta_info = await asyncio.to_thread(meta.read, ctx["data"], ctx["mime"])
            except ValueError as exc:
                raise pipeline.AnalysisError(str(exc)) from exc
            duration = meta_info.get("duration_s")
            if duration and duration > settings.agent_max_audio_s:
                raise pipeline.AnalysisError(
                    f"Audio is {duration:.0f}s, over the {settings.agent_max_audio_s}s cap."
                )
            return {"meta": meta_info, "sarvam": sarvam_result, "errors": warnings}
        try:
            tool, meta_info, provenance = await asyncio.gather(
                asyncio.to_thread(forensics.examine, ctx["data"]),
                asyncio.to_thread(meta.read, ctx["data"], ctx["mime"]),
                asyncio.to_thread(synthid.scan, ctx["data"]),
            )
        except ValueError as exc:
            raise pipeline.AnalysisError(str(exc)) from exc
        return {"meta": meta_info, "tool": tool, "provenance": provenance, "errors": warnings}

    async def perceive(state: CaseState) -> dict:
        _mark("perceive")
        try:
            if modality == "video":
                per_frame = list(
                    await asyncio.gather(
                        *[
                            visual_agent.analyze(frame, tool_data=tools)
                            for frame, tools in zip(ctx["frames"], ctx["frame_tools"])
                        ]
                    )
                )
                mean_score = sum(f["artifact_score"] for f in per_frame) / len(per_frame)
                best = max(per_frame, key=lambda f: f["artifact_score"])
                observations: list[str] = []
                entities: list[str] = []
                for frame in per_frame:
                    observations.extend(frame.get("observations", []))
                    entities.extend(frame.get("entities", []))
                perceptual = {
                    "observations": observations,
                    "artifact_score": mean_score,
                    "caption": best.get("caption", ""),
                    "entities": sorted(set(entities)),
                    "ocr_text": " ".join(f.get("ocr_text", "") for f in per_frame).strip(),
                    "frames": len(per_frame),
                }
            elif modality == "audio":
                perceptual = await audio_agent.analyze(
                    ctx["data"], ctx["mime"], sarvam_hint=state.get("sarvam")
                )
                perceptual = dict(perceptual)
            else:
                jpeg = pipeline._normalize_image(ctx["data"])
                perceptual = await visual_agent.analyze(
                    jpeg, tool_data=state.get("tool"), provenance=state.get("provenance")
                )
        except muse_client.MuseError as exc:
            raise pipeline.AnalysisError(f"Perception failed: {exc}") from exc
        except ValueError as exc:
            raise pipeline.AnalysisError(str(exc)) from exc
        if modality == "audio":
            caption = perceptual.get("transcript_hint", "")
            ocr_text = caption
        else:
            caption = perceptual.get("caption", "")
            ocr_text = perceptual.get("ocr_text", "")
        return {
            "perceptual": perceptual,
            "caption": caption,
            "entities": perceptual.get("entities", []),
            "ocr_text": ocr_text,
        }

    async def retrieve(state: CaseState) -> dict:
        _mark("retrieve")
        search_result = await pipeline.run_search(
            caption=state.get("caption", ""),
            entities=state.get("entities", []),
            ocr_text=state.get("ocr_text", ""),
        )
        return {"search": search_result}

    async def adjudicate(state: CaseState) -> dict:
        _mark("adjudicate")
        tool = state.get("tool")
        sarvam_result = state.get("sarvam")
        sarvam_entry = None
        if state.get("modality") == "audio":
            warning = next(
                (w for w in state.get("errors", []) if w.startswith("sarvam")), None
            )
            sarvam_entry = {"result": sarvam_result, "warning": warning}
        shaped = await pipeline.run_fusion(
            modality=state.get("modality", modality),
            perceptual=state.get("perceptual", {}),
            meta_info=state.get("meta", {}),
            search_result=state.get("search", {}),
            claimed_date=state.get("claimed_date"),
            source=state.get("source", source),
            forensics_result=tool if modality in ("image", "video") else None,
            provenance_result=state.get("provenance"),
            sarvam_entry=sarvam_entry,
            caption=(state.get("caption", "") or "")[:500],
        )
        return {"shaped": shaped}

    builder = StateGraph(CaseState)
    builder.add_node("fetch_tools", fetch_tools)
    builder.add_node("perceive", perceive)
    builder.add_node("retrieve", retrieve)
    builder.add_node("adjudicate", adjudicate)
    builder.add_edge(START, "fetch_tools")
    builder.add_edge("fetch_tools", "perceive")
    builder.add_edge("perceive", "retrieve")
    builder.add_edge("retrieve", "adjudicate")
    builder.add_edge("adjudicate", END)
    async with AsyncSqliteSaver.from_conn_string(str(_memory_path())) as saver:
        compiled = builder.compile(checkpointer=saver)
        final = await compiled.ainvoke(
            {
                "modality": modality,
                "source": source,
                "claimed_date": claimed_date,
                "errors": [],
            },
            {"configurable": {"thread_id": thread_id}},
        )
    shaped = final.get("shaped")
    if not isinstance(shaped, dict):
        raise pipeline.AnalysisError("Graph finished without a verdict.")
    return shaped
