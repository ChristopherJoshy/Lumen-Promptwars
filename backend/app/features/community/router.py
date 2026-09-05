"""Community annotations: agree/disagree + free text on reports (ckpt 15)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{case_id}")
async def list_notes(case_id: str) -> list[dict]:
    raise NotImplementedError("checkpoint 15")
