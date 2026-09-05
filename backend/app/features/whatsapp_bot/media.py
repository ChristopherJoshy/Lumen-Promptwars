"""Authenticated Twilio media download (Basic Auth on MediaUrl0).

Same analysis pipeline as direct upload — never a forked detection path.
Over the 16 MB Twilio limit: reply asking for web upload, no silent failure.
"""
from __future__ import annotations

import httpx

from app.core.config import settings

_MAX_BYTES = 16 * 1024 * 1024


async def download(media_url: str) -> bytes:
    """Download Twilio media with Basic Auth, capped at 16 MB.

    Args:
        media_url: Twilio MediaUrl0 value.

    Returns:
        Raw media bytes.

    Raises:
        ValueError: URL missing, auth missing, over-size, transport failure.
    """
    if not media_url.startswith(("http://", "https://")):
        raise ValueError("Refusing to fetch non-http media URL (SSRF guard).")
    sid = settings.twilio_account_sid
    token = settings.twilio_auth_token
    if not sid or not token:
        raise ValueError("Twilio credentials are not configured.")
    try:
        async with httpx.AsyncClient(timeout=30, auth=(sid, token), follow_redirects=True) as client:
            async with client.stream("GET", media_url) as resp:
                    raise ValueError(f"Media download failed (HTTP {resp.status_code}).")
                length = resp.headers.get("content-length")
                if length and int(length) > _MAX_BYTES:
                    raise ValueError("Media is over 16 MB — use the web upload instead.")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes(65536):
                    total += len(chunk)
                    if total > _MAX_BYTES:
                        raise ValueError("Media is over 16 MB — use the web upload instead.")
                    chunks.append(chunk)
                return b"".join(chunks)
    except httpx.HTTPError as exc:
        raise ValueError(f"Media download failed: {type(exc).__name__}") from exc
