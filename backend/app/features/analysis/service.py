"""Report serving: cached case verdicts, signal rows, forensic heatmaps.

Reads the pipeline disk cache (storage/agentic_cache/<case_id>.json);
unknown or expired cases are 404, never a fallback verdict.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


async def answer_question(case_id: str, question: str) -> str:
    """Answer one grounded follow-up about a cached case.

    Raises ValueError on unknown cases, empty/oversize questions, or an
    unparsable model answer. Shared by the web ask route and WhatsApp
    conversations — one implementation, no duplicated prompts.
    """
    from app.features.analysis.agents import muse_client

    case = get_case(case_id)
    if case is None:
        raise ValueError("Unknown or expired case.")
    question = question.strip()
    if not question:
        raise ValueError("Ask a non-empty question.")
    if len(question) > 500:
        raise ValueError("Keep the question under 500 characters.")
    system = (
        "You answer follow-up questions about one Lumen media-verdict report. "
        "Ground every claim in the case JSON below; say 'not in this report' "
        "when the answer is not there. Plain language, 2-5 sentences, no new "
        "verdict. Return JSON ONLY: {\"answer\": str}."
    )
    try:
        result = await muse_client.respond(
            system,
            [{"type": "input_text", "text": f"question: {question}\ncase: {json.dumps(case, default=str)[:6000]}"}],
            max_output_tokens=800,
        )
    except muse_client.MuseError as exc:
        raise ValueError(f"Answer failed: {exc}") from exc
    if "answer" not in result:
        raise ValueError("Answer came back unparsable.")
    return str(result["answer"])


_CASE_RE = re.compile(r"^[0-9a-f]{64}$")
_FORENSIC_NAMES = ("ela", "dct", "noise", "copymove", "ghost", "blockiness", "spectrum")

def _cache_path(case_id: str) -> Path | None:
    if not _CASE_RE.match(case_id):
        return None
    return Path("storage/agentic_cache") / f"{case_id}.json"


def get_case(case_id: str) -> dict | None:
    """Return the shaped verdict dict for a case, or None when unknown."""
    path = _cache_path(case_id)
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


def list_signals(case_id: str) -> list[dict] | None:
    """Map a case's signals to {name, finding} rows for the report page."""
    case = get_case(case_id)
    if case is None:
        return None
    signals = case.get("signals", {})
    rows: list[dict] = []
    perceptual = signals.get("perceptual", {}) or {}
    if perceptual:
        rows.append(
            {
                "name": "perceptual",
                "finding": f"artifact_score {perceptual.get('artifact_score', '?')}; "
                f"{len(perceptual.get('observations', []) or [])} observations",
            }
        )
        audio_tools = perceptual.get("audio_tools")
        if audio_tools:
            rows.append(
                {
                    "name": "audio_tools",
                    "finding": (
                        f"clip {audio_tools.get('clip', '?')}; "
                        f"gaps {audio_tools.get('gaps', '?')}; "
                        f"dr {audio_tools.get('dr', '?')}"
                    ),
                }
            )
    forensics = signals.get("forensics")
    if forensics:
        scores = forensics.get("scores", {})
        rows.append(
            {
                "name": "forensics",
                "finding": "instrument scores: "
                + ", ".join(f"{k}={scores.get(k, '?')}" for k in (*_FORENSIC_NAMES, "fused_mean")),
            }
        )
    sarvam = signals.get("sarvam")
    if sarvam:
        res = sarvam.get("result") or {}
        rows.append(
            {
                "name": "voice",
                "finding": (
                    f"language {res.get('detected_language', '?')}; "
                    f"transcript: {(res.get('transcript') or '')[:300]}"
                    if res.get("transcript")
                    else (sarvam.get("warning") or "no transcript")
                ),
            }
        )
    search = signals.get("search", {})
    if search:
        india = search.get("india_hits", []) or []
        total = len(search.get("exa_hits", []) or []) + len(search.get("ddg_hits", []) or [])
        rows.append(
            {"name": "context", "finding": f"{total} web hits, {len(india)} India fact-checker hits"}
        )
    temporal = signals.get("temporal", {})
    if temporal:
        rows.append(
            {
                "name": "temporal",
                "finding": str(temporal.get("note") or "no flags")
                + (" [FLAGGED]" if temporal.get("flag") else ""),
            }
        )
    provenance = signals.get("provenance")
    if provenance:
        markers = provenance.get("markers", []) or []
        rows.append(
            {
                "name": "provenance",
                "finding": (
                    f"generator {provenance.get('generator', '?')}; "
                    f"{len(markers)} markers; c2pa {provenance.get('c2pa', '?')}"
                ),
            }
        )
    debate = signals.get("debate")
    if debate:
        if debate.get("agreed") is True:
            finding = "judge and critic agreed"
        elif debate.get("agreed") is False:
            counters = debate.get("counter_reasons", []) or []
            finding = "critic dissented: " + ("; ".join(str(c) for c in counters) or "no reasons given")
        else:
            finding = str(debate.get("note") or "debate skipped")
        rows.append({"name": "debate", "finding": finding})
    return rows


def forensics_path(case_id: str, name: str) -> Path | None:
    """Resolve a heatmap PNG for a case; allowlisted names, directory-pinned."""
    if name not in _FORENSIC_NAMES:
        return None
    case = get_case(case_id)
    if case is None:
        return None
    raw = ((case.get("signals", {}).get("forensics") or {}).get("artifacts") or {}).get(name)
    if not raw:
        return None
    base = Path("storage/forensics").resolve()
    try:
        path = Path(raw).resolve()
    except OSError:
        return None
    if path.parent != base or not path.is_file():
        return None
    return path
