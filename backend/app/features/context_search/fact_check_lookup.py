"""Google Fact Check Tools API lookup, India-source-weighted (checkpoint 10).

Primary source, not a fallback: hits from Indian IFCN signatories (Alt News,
BOOM, Factly) and PIB Fact Check are labeled distinctly — "already debunked
by PIB Fact Check" outranks an unranked generic web match. Generic reverse
search is secondary.
"""
from __future__ import annotations

INDIA_SOURCES = ("alt news", "boom", "factly", "pib fact check")


async def lookup(query: str) -> list[dict]:
    raise NotImplementedError("checkpoint 10")
