"""Taskiq worker entrypoint. Real jobs land per-checkpoint; this boots empty."""
from __future__ import annotations


async def run_worker() -> None:
    raise NotImplementedError("wired in checkpoint 4 (Taskiq + Redis)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_worker())
