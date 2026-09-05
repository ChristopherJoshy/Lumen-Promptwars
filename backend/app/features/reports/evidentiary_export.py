"""Takedown-ready signed PDF/JSON export (checkpoint 12).

The generated document must state it is a documentation aid for a takedown
request, not a legal certification — not just the report page disclaimer.
"""
from __future__ import annotations


async def export(case_id: str) -> bytes:
    raise NotImplementedError("checkpoint 12")
