"""Auth: email + JWT first, OAuth only if time allows (checkpoint 15)."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def me() -> dict:
    raise NotImplementedError("checkpoint 15")
