"""Judge role: fuse every signal into one verdict + confidence + reasons."""
from __future__ import annotations

import json

from app.features.analysis.agents import muse_client

_VERDICTS = ("verified", "contradiction_detected", "likely_synthetic", "insufficient_evidence")

_SYSTEM = (
    "You are the fusion judge for Lumen, a misinformation checker. Given "
    "perceptual forensics (artifact scores, observations), file metadata, "
    "web search hits (Indian fact-checkers weighted first), and a temporal "
    "check, output ONE verdict. Choose verbatim from: "
    "verified | contradiction_detected | likely_synthetic | "
    "insufficient_evidence. verified means no manipulation signs and no "
    "contradicting evidence. contradiction_detected means the file's story "
    "(caption/dates/claims) disagrees with pixels, metadata, or dated hits. "
    "likely_synthetic means multiple perceptual signals point to AI "
    "generation. insufficient_evidence means signals are thin or conflict "
    "without a winner — say so explicitly. Return JSON ONLY: "
    '{"verdict": str, "confidence": float 0..1, "explanation": str 2-4 sentences, '
    '"reasons": [str]}. Reference concrete artifacts, dates, and hit URLs; '
    "never hedge generically."
)


async def fuse(signals: dict, source: str) -> dict:
    """Fuse pipeline signals into the final verdict.

    Args:
        signals: Mapping with modality, perceptual, meta, search, temporal.
        source: upload | link | whatsapp (WhatsApp forwards get no
            claimed-date benefit of the doubt).

    Returns:
        Dict with verdict, confidence, explanation, reasons.

    Raises:
        muse_client.MuseError: Zen call failed or returned bad JSON/enum.
    """
    if not isinstance(signals, dict):
        raise ValueError("judge.fuse requires a signals dict.")
    user_text = (
        f"source: {source}\n"
        f"signals: {json.dumps(signals, default=str)[:6000]}\n"
        "Fuse now. Return JSON only."
    )
    result = await muse_client.respond(
        _SYSTEM, [{"type": "input_text", "text": user_text}], max_output_tokens=4096
    )
    verdict = str(result.get("verdict", ""))
    if verdict not in _VERDICTS:
        raise muse_client.MuseError(f"Judge returned unknown verdict: {verdict[:100]}")
    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError) as exc:
        raise muse_client.MuseError("Judge confidence is not a number.") from exc
    if not 0.0 <= confidence <= 1.0:
        raise muse_client.MuseError("Judge confidence outside 0..1.")
    explanation = str(result.get("explanation", ""))
    reasons = list(result.get("reasons", []) or [])
    if not explanation.strip() or not reasons:
        raise muse_client.MuseError("Judge omitted explanation or reasons.")
    return {
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "reasons": [str(r) for r in reasons],
    }
