"""WhatsApp reply copy: verdict-first, plain-language, link-out.

Design: chat is the front door, not the dossier. The reply carries the
verdict label, one concrete sentence (artifacts/dates/fact-check hits, never
generic hedging), an optional one-line reason, and the full-report link.
Detail lives on the web; the disclaimer rides along because forwards travel
without the report page attached.
"""
from __future__ import annotations

DISCLAIMER = "Lumen is a probabilistic aid, not proof."

VERDICT_LINES = {
    "verified": "Verified — no signs of AI generation found.",
    "contradiction_detected": "Contradiction detected — the file's story and its pixels disagree.",
    "likely_synthetic": "Likely synthetic — multiple signals point to AI generation.",
    "insufficient_evidence": "Insufficient evidence — no clear signal either way.",
}


def format_verdict(verdict: str, reason: str, report_url: str) -> str:
    """Build the outbound WhatsApp verdict text for a finished case."""
    first = VERDICT_LINES.get(verdict, VERDICT_LINES["insufficient_evidence"])
    parts = [f"*{first}*"]
    if reason.strip():
        parts.append(f"Why: {reason.strip()}")
    parts.append(f"Full evidence: {report_url}")
    parts.append(DISCLAIMER)
    return "\n\n".join(parts)


def format_failure(reason: str = "") -> str:
    """Build the honest error reply when analysis cannot finish."""
    body = "Analysis hit a snag — reply RETRY or use the web upload. "
    if reason.strip():
        body += f"Reason: {reason.strip()[:160]} "
    body += "No verdict was reached, so nothing here is a result.\n\n" + DISCLAIMER
    return body
