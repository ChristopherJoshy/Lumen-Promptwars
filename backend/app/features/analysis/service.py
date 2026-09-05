"""Report serving: cached case verdicts, signal rows, forensic heatmaps.

Reads the pipeline disk cache (storage/agentic_cache/<case_id>.json);
unknown or expired cases are 404, never a fallback verdict.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_CASE_RE = re.compile(r"^[0-9a-f]{64}$")
_FORENSIC_NAMES = ("ela", "dct", "noise", "copymove")


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
    perceptual = signals.get("perceptual", {})
    if perceptual:
        rows.append(
            {
                "name": "perceptual",
                "finding": f"artifact_score {perceptual.get('artifact_score', '?')}; "
                f"{len(perceptual.get('observations', []))} observations",
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
        india = search.get("india_hits", [])
        total = len(search.get("exa_hits", [])) + len(search.get("ddg_hits", []))
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
