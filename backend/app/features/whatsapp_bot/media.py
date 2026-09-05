"""Authenticated Twilio media download (Basic Auth on MediaUrl0).

Same analysis pipeline as direct upload — never a forked detection path.
Over the 16 MB Twilio limit: reply asking for web upload, no silent failure.
"""
from __future__ import annotations


async def download(media_url: str) -> bytes:
    raise NotImplementedError("checkpoint 6")
