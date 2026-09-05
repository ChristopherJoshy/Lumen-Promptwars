"""Twilio REST client wrapper for outbound verdict replies (checkpoint 6)."""
from __future__ import annotations

import httpx

from app.core.config import settings


async def send_verdict(to: str, text: str, report_url: str) -> None:
    """Send a verdict reply via the Twilio Messages API.

    Args:
        to: Destination WhatsApp number (From of the inbound message).
        text: Reply body built with messages.format_verdict/format_failure.
        report_url: Full-report link (logged with the send for traceability).

    Raises:
        ValueError: Twilio credentials missing or the send fails loudly.
    """
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    sender = settings.twilio_whatsapp_number
    if not sid or not token or not sender:
        raise ValueError("Twilio credentials are not configured.")
    if not sender.startswith("whatsapp:"):
        raise ValueError(
            "TWILIO_WHATSAPP_NUMBER must look like whatsapp:+14155238886 (whatsapp: prefix required)."
        )
    _ = report_url
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=20, auth=(sid, token)) as client:
            resp = await client.post(
                url, data={"From": sender, "To": to, "Body": text}
            )
    except httpx.HTTPError as exc:
        raise ValueError(f"Twilio send failed: {type(exc).__name__}") from exc
    if resp.status_code >= 400:
        try:
            detail = resp.json()
            code = detail.get("code", "?")
            message = detail.get("message", "")[:160]
        except ValueError:
            code, message = "?", resp.text[:160]
        raise ValueError(f"Twilio send failed (HTTP {resp.status_code}, code {code}): {message}")
