"""yt-dlp link extractor (checkpoint 3).

Retention: extracted third-party media is TRANSIENT — kept only for analysis
plus a short cache TTL, never re-served. We use yt-dlp, not Meta oEmbed: the
oEmbed terms restrict usage to front-end embedding display, which rules it
out for analysis metadata.
"""
from __future__ import annotations


async def extract(url: str) -> dict:
    raise NotImplementedError("checkpoint 3")
