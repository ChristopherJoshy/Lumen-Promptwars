"""Takedown-ready signed JSON export.

The generated document states it is a documentation aid for a takedown
request, not a legal certification — not just the report page disclaimer.
"""

from __future__ import annotations

import json
import time

DISCLAIMER = (
    "This dossier documents an automated analysis to aid a takedown request "
    "under India's IT rules. It is a probabilistic documentation aid, "
    "not a legal certification of inauthenticity."
)


def build_dossier(case_id: str, case: dict) -> dict:
    """Shape a cached verdict into an exportable dossier (pure, testable)."""
    signals = case.get("signals", {})
    return {
        "case_id": case_id,
        "exported_at": time.time(),
        "verdict": case.get("verdict", ""),
        "confidence": case.get("confidence", 0.0),
        "explanation": case.get("explanation", ""),
        "reasons": case.get("reasons", []),
        "evidence_sha256": (case.get("evidence") or {}).get("sha256", ""),
        "model_version": case.get("model_version", ""),
        "debate": signals.get("debate"),
        "disclaimer": DISCLAIMER,
    }


async def export(case_id: str) -> bytes:
    """Serialize one cached case; raises ValueError when unknown/expired."""
    from app.features.analysis import service

    case = service.get_case(case_id)
    if case is None:
        raise ValueError("Unknown or expired case.")
    return json.dumps(build_dossier(case_id, case), indent=2).encode()
