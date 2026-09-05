"""Agentic multi-signal pipeline (agentic-v1): one path for every modality.

Step 0 probe verdicts (2026-09-05, muse-spark-1.3-contributor-free via Zen
Responses API): text-only 200; vision 200 with normalized JPEG (>= 64px,
detail low, input_image/image_url) — tiny 1x1 JPEGs 500 upstream, so every
image is Pillow-normalized before sending; audio 200 with
input_audio/audio_url (data:audio/wav;base64 sine-tone probe returned valid
JSON with empty transcript, as expected). No fallback caps engaged: visual
and audio agents send real bytes. Text-only needs max_output_tokens >= 800
because reasoning tokens consume the headroom.

WhatsApp parity: forwards ride this identical pipeline with
source="whatsapp"; links pasted in chat go through analyze_link with the
same source. Unresolved link extractions are capped (never verified) and
run searcher-only on title/description/URL.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import subprocess
import tempfile
import time
from pathlib import Path

from app.core.config import settings
from app.features.analysis.agents import audio as audio_agent
from app.features.analysis.agents import judge, links, meta, muse_client, searcher, temporal
from app.features.analysis.agents import visual as visual_agent

PIPELINE_VERSION = "agentic-v1"

_WEB_IMAGE_MAX = 25 * 1024 * 1024
_WHATSAPP_MAX = 16 * 1024 * 1024
_VIDEO_MAX_S = 120

_IMAGE_MIMES = ("image/jpeg", "image/png", "image/webp")
_VIDEO_MIMES = ("video/mp4", "video/mov", "video/webm")
_AUDIO_MIMES = ("audio/mpeg", "audio/wav", "audio/x-m4a", "audio/ogg", "audio/mp4")


class AnalysisError(Exception):
    """Loud pipeline failure: surfaces as a visible job error, never a fake verdict."""


def _cache_dir() -> Path:
    d = Path("storage/agentic_cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_get(key: str) -> dict | None:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if payload.get("model") != settings.muse_model or payload.get("version") != PIPELINE_VERSION:
        return None
    if time.time() - float(payload.get("saved_at", 0)) > 7 * 24 * 3600:
        return None
    result = payload.get("result")
    if isinstance(result, dict):
        result = dict(result)
        result["cached"] = True
        return result
    return None


def _cache_put(key: str, result: dict) -> None:
    path = _cache_dir() / f"{key}.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "model": settings.muse_model,
                    "version": PIPELINE_VERSION,
                    "saved_at": time.time(),
                    "result": result,
                }
            )
        )
    except OSError:
        pass


def _guard_bytes(data: bytes, *, source: str, kind: str) -> None:
    if not data:
        raise AnalysisError("Empty file: nothing to analyze.")
    if kind == "audio":
        cap_mb = settings.agent_max_audio_mb
        if len(data) > cap_mb * 1024 * 1024:
            raise AnalysisError(
                f"Audio is {len(data) // (1024 * 1024)} MB, over the {cap_mb} MB cap."
            )
        return
    if source == "whatsapp" and len(data) > _WHATSAPP_MAX:
        raise AnalysisError("File is over 16 MB — use the web upload instead.")
    if len(data) > _WEB_IMAGE_MAX:
        raise AnalysisError("File is over the 25 MB web-upload cap.")


def _normalize_image(data: bytes) -> bytes:
    """RGB, thumbnail 1024px, JPEG q80 re-encode (also upscales tiny probes)."""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGB")
            if img.width < 64 or img.height < 64:
                img = img.resize((max(64, img.width * 4), max(64, img.height * 4)), Image.NEAREST)
            img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80)
            return buf.getvalue()
    except Exception as exc:
        raise AnalysisError(f"Unreadable image: {exc}") from exc


def _extract_frames(data: bytes, max_frames: int) -> list[bytes]:
    """Evenly spaced JPEG frames at ~1fps via the imageio-ffmpeg binary."""
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError as exc:
        raise AnalysisError(
            "imageio-ffmpeg is not installed; see https://ffmpeg.org/download.html."
        ) from exc
    with tempfile.TemporaryDirectory(prefix="lumen-frames-") as tmpdir:
        src = Path(tmpdir) / "src.mp4"
        src.write_bytes(data)
        out = str(Path(tmpdir) / "f%03d.jpg")
        proc = subprocess.run(
            [
                get_ffmpeg_exe(),
                "-y",
                "-i",
                str(src),
                "-vf",
                "fps=1",
                "-frames:v",
                str(max_frames),
                "-q:v",
                "3",
                out,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        if proc.returncode != 0:
            raise AnalysisError(f"Frame extraction failed: {proc.stderr.decode(errors='replace')[:300]}")
        frames: list[bytes] = []
        for path in sorted(Path(tmpdir).glob("f*.jpg"))[:max_frames]:
            try:
                frames.append(_normalize_image(path.read_bytes()))
            except AnalysisError:
                continue
        if not frames:
            raise AnalysisError("No frames could be extracted from this video.")
        return frames


def _apply_temporal_override(fused: dict, temporal_result: dict) -> dict:
    if temporal_result.get("flag") and fused.get("verdict") == "verified":
        fused = dict(fused)
        fused["verdict"] = "contradiction_detected"
        reasons = list(fused.get("reasons", []))
        reasons.append(f"Temporal check: {temporal_result.get('note', '')}")
        fused["reasons"] = reasons
    return fused


def _shape_result(
    *,
    verdict: str,
    confidence: float,
    explanation: str,
    reasons: list[str],
    signals: dict,
    sha256: str,
    caption: str,
    cached: bool = False,
) -> dict:
    return {
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "reasons": reasons,
        "signals": signals,
        "model_version": f"{settings.muse_model}@{PIPELINE_VERSION}",
        "evidence": {"sha256": sha256, "caption": caption},
        "cached": cached,
    }


async def _run_tail(
    *,
    modality: str,
    perceptual: dict,
    meta_info: dict,
    caption: str,
    entities: list[str],
    ocr_text: str,
    claimed_date: str | None,
    source: str,
) -> dict:
    try:
        search_result = await searcher.search(caption, entities, ocr_text)
    except Exception as exc:
        raise AnalysisError(f"Search failed: {exc}") from exc
    meta_dates = {
        "exif_date": (meta_info.get("exif") or {}).get("306"),
        "upload_date": meta_info.get("upload_date"),
    }
    temporal_result = temporal.check(
        meta_dates, search_result.get("exa_hits", []) + search_result.get("ddg_hits", []), claimed_date
    )
    signals = {
        "modality": modality,
        "perceptual": perceptual,
        "meta": meta_info,
        "search": search_result,
        "temporal": temporal_result,
    }
    try:
        fused = await judge.fuse(signals, source)
    except muse_client.MuseError as exc:
        raise AnalysisError(f"Fusion failed: {exc}") from exc
    fused = _apply_temporal_override(fused, temporal_result)
    return _shape_result(
        verdict=fused["verdict"],
        confidence=fused["confidence"],
        explanation=fused["explanation"],
        reasons=fused["reasons"],
        signals=signals,
        sha256=meta_info.get("sha256", ""),
        caption=caption,
    )


async def analyze_image(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Run the full image pipeline: visual + meta -> search -> judge."""
    if mime not in _IMAGE_MIMES:
        raise AnalysisError(f"Unsupported image MIME: {mime}")
    _guard_bytes(data, source=source, kind="image")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:img:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    jpeg = _normalize_image(data)
    try:
        perceptual, meta_info = await asyncio.gather(
            visual_agent.analyze(jpeg),
            asyncio.to_thread(meta.read, data, mime),
        )
    except muse_client.MuseError as exc:
        raise AnalysisError(f"Visual analysis failed: {exc}") from exc
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc
    result = await _run_tail(
        modality="image",
        perceptual=perceptual,
        meta_info=meta_info,
        caption=perceptual.get("caption", ""),
        entities=perceptual.get("entities", []),
        ocr_text=perceptual.get("ocr_text", ""),
        claimed_date=claimed_date,
        source=source,
    )
    _cache_put(cache_key, result)
    return result


async def analyze_video(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Run the video pipeline: N frame visuals aggregated, then the image tail."""
    if mime not in _VIDEO_MIMES:
        raise AnalysisError(f"Unsupported video MIME: {mime}")
    _guard_bytes(data, source=source, kind="video")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:vid:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    try:
        meta_info = await asyncio.to_thread(meta.read, data, mime)
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc
    duration = meta_info.get("duration_s")
    if duration and duration > _VIDEO_MAX_S:
        raise AnalysisError(f"Video is {duration:.0f}s, over the {_VIDEO_MAX_S}s cap.")
    frames = await asyncio.to_thread(_extract_frames, data, settings.agent_max_frames)
    try:
        per_frame = list(
            await asyncio.gather(*[visual_agent.analyze(frame) for frame in frames])
        )
    except muse_client.MuseError as exc:
        raise AnalysisError(f"Video frame analysis failed: {exc}") from exc
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
    result = await _run_tail(
        modality="video",
        perceptual=perceptual,
        meta_info=meta_info,
        caption=perceptual["caption"],
        entities=perceptual["entities"],
        ocr_text=perceptual["ocr_text"],
        claimed_date=claimed_date,
        source=source,
    )
    _cache_put(cache_key, result)
    return result


async def analyze_audio(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Run the audio pipeline: voice forensics + meta -> search -> judge."""
    if mime not in _AUDIO_MIMES:
        raise AnalysisError(f"Unsupported audio MIME: {mime}")
    _guard_bytes(data, source=source, kind="audio")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:aud:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    try:
        perceptual, meta_info = await asyncio.gather(
            audio_agent.analyze(data, mime),
            asyncio.to_thread(meta.read, data, mime),
        )
    except muse_client.MuseError as exc:
        raise AnalysisError(f"Audio analysis failed: {exc}") from exc
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc
    duration = meta_info.get("duration_s")
    if duration and duration > settings.agent_max_audio_s:
        raise AnalysisError(
            f"Audio is {duration:.0f}s, over the {settings.agent_max_audio_s}s cap."
        )
    result = await _run_tail(
        modality="audio",
        perceptual=perceptual,
        meta_info=meta_info,
        caption=perceptual.get("transcript_hint", ""),
        entities=perceptual.get("entities", []),
        ocr_text=perceptual.get("transcript_hint", ""),
        claimed_date=claimed_date,
        source=source,
    )
    _cache_put(cache_key, result)
    return result


async def analyze_link(url: str, *, source: str) -> dict:
    """Resolve a link, then dispatch on kind; unresolved stays searcher-only."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise AnalysisError("Link must start with http(s)://")
    cache_key = hashlib.sha256(
        f"{settings.muse_model}@{PIPELINE_VERSION}:link:{url}".encode()
    ).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    resolved = await links.resolve(url)
    kind = resolved.get("kind")
    metadata = resolved.get("metadata", {})
    if kind == "unresolved" or not resolved.get("data"):
        title = str(metadata.get("title") or "")
        desc = str(metadata.get("description") or "")
        caption_seed = " ".join([title, desc, url])[:2000]
        try:
            search_result = await searcher.search(caption_seed, [], caption_seed)
        except Exception as exc:
            raise AnalysisError(f"Search failed: {exc}") from exc
        temporal_result = temporal.check(
            {"upload_date": metadata.get("upload_date")},
            search_result.get("exa_hits", []) + search_result.get("ddg_hits", []),
            metadata.get("upload_date"),
        )
        signals = {
            "modality": "link",
            "perceptual": {"note": resolved.get("note", "")},
            "meta": {"url": url, **metadata},
            "search": search_result,
            "temporal": temporal_result,
        }
        try:
            fused = await judge.fuse(signals, source)
        except muse_client.MuseError as exc:
            raise AnalysisError(f"Fusion failed: {exc}") from exc
        if fused.get("verdict") == "verified":
            fused = dict(fused)
            fused["verdict"] = "insufficient_evidence"
            fused["reasons"] = list(fused.get("reasons", [])) + [
                f"Unresolved extraction ({metadata.get('platform', 'unknown')}): "
                "no bytes to inspect, so verification is impossible."
            ]
        fused = _apply_temporal_override(fused, temporal_result)
        result = _shape_result(
            verdict=fused["verdict"],
            confidence=fused["confidence"],
            explanation=fused["explanation"],
            reasons=fused["reasons"],
            signals=signals,
            sha256=hashlib.sha256(url.encode()).hexdigest(),
            caption=caption_seed[:500],
        )
        _cache_put(cache_key, result)
        return result
    data = resolved["data"]
    mime = resolved.get("mime") or "video/mp4"
    claimed = metadata.get("upload_date")
    if kind == "image":
        return await analyze_image(data, mime=mime, source=source, claimed_date=claimed)
    if kind == "audio":
        return await analyze_audio(data, mime=mime, source=source, claimed_date=claimed)
    return await analyze_video(data, mime=mime, source=source, claimed_date=claimed)
