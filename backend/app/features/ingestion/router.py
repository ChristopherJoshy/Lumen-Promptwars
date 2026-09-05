"""Ingestion HTTP surface: upload + link submit (checkpoint 3)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def status() -> dict[str, str]:
    return {"ingestion": "skeleton"}
