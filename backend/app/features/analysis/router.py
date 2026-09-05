"""Analysis HTTP surface: submit, status, report. Fusion lives in service.py."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def status() -> dict[str, str]:
    return {"pipeline": "skeleton"}


@router.get("/report/{case_id}")
async def report(case_id: str) -> dict[str, str]:
    raise NotImplementedError("checkpoint 4+ fills the fusion pipeline")
