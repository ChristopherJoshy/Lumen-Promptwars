"""Debate critic: steelman-then-attack the judge's proposal, one round.

Single bounded round: review() challenges the proposal; the judge gets one
reconsideration and has the last word. Low thinking throughout (1000 output
tokens, reasoning low). A critic failure never fails the verdict — the
proposal stands with a skipped-debate note.
"""

from __future__ import annotations

import json

from app.features.analysis.agents import judge, muse_client

_SYSTEM = (
    "You are the dissent critic for Lumen, a misinformation checker. A judge "
    "proposes a verdict on media with signals attached. Steelman the proposal "
    "in one sentence, then attack it: missing evidence, over-read signals, "
    "cheaper explanations (old-but-real, satire, compression). Keep thinking "
    "short. Return JSON ONLY with exactly these keys: "
    '{"agree": bool, "counter_reasons": [str], "suggested_verdict": str}. '
    "suggested_verdict is verbatim one of: verified | contradiction_detected "
    "| likely_synthetic | insufficient_evidence."
)


async def review(proposal: dict, signals: dict, source: str) -> dict:
    """Challenge a proposed verdict.

    Returns {agree, counter_reasons, suggested_verdict}.
    Raises muse_client.MuseError / ValueError on bad input or bad JSON.
    """
    if not isinstance(proposal, dict) or not isinstance(signals, dict):
        raise ValueError("critic.review requires proposal and signals dicts.")
    user_text = (
        f"source: {source}\n"
        f"proposed: {json.dumps(proposal, default=str)[:2000]}\n"
        f"signals: {json.dumps(signals, default=str)[:4000]}\n"
        "Attack the proposal. Return JSON only."
    )
    result = await muse_client.respond(
        _SYSTEM, [{"type": "input_text", "text": user_text}], max_output_tokens=1000
    )
    for key in ("agree", "counter_reasons", "suggested_verdict"):
        if key not in result:
            raise muse_client.MuseError(f"Critic omitted key: {key}")
    suggested = str(result["suggested_verdict"])
    if suggested not in judge.VERDICTS:
        raise muse_client.MuseError(f"Critic suggested unknown verdict: {suggested[:100]}")
    return {
        "agree": bool(result["agree"]),
        "counter_reasons": [str(r) for r in result["counter_reasons"]],
        "suggested_verdict": suggested,
    }
