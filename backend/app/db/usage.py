"""MongoDB usage ledger: per-case volume for dashboards and abuse watch.

Local-first: empty MONGO_URL disables everything (no-op). Best-effort:
every write is timeout-bounded and swallowed — usage tracking must never
break or slow a verdict. Only verdict pointers are stored (case_id,
modality, verdict, source) — never media bytes (retention rule).
"""

from __future__ import annotations

import asyncio
import time

from app.core.config import settings

_client = None


def get_client():
    """Singleton Motor client, or None when MONGO_URL is unset."""
    global _client
    if _client is None and settings.mongo_url:
        from motor.motor_asyncio import AsyncIOMotorClient

        _client = AsyncIOMotorClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
        )
    return _client


async def log_case(
    *,
    case_id: str,
    modality: str,
    verdict: str,
    confidence: float,
    source: str,
    cached: object = False,
) -> None:
    """Insert one usage row; no-op when unconfigured, silent on failure."""
    client = get_client()
    if client is None:
        return
    doc = {
        "case_id": case_id,
        "modality": modality,
        "verdict": verdict,
        "confidence": float(confidence or 0.0),
        "source": source,
        "cached": bool(cached),
        "ts": time.time(),
    }
    try:
        await asyncio.wait_for(client.lumen.usage.insert_one(doc), timeout=2.0)
    except Exception:
        pass  # usage ledger is advisory; verdicts never depend on it


async def usage_stats() -> dict:
    """Counts by verdict and modality for the dashboard; {} when disabled."""
    client = get_client()
    if client is None:
        return {}
    try:
        pipeline = [
            {"$group": {"_id": {"v": "$verdict", "m": "$modality"}, "n": {"$sum": 1}}},
        ]
        rows = await asyncio.wait_for(
            client.lumen.usage.aggregate(pipeline).to_list(length=100), timeout=3.0
        )
        return {"by_verdict_modality": rows}
    except Exception:
        return {}
