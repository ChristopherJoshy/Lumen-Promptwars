"""Twilio webhook: validate signature, enqueue Taskiq job, return TwiML fast.

No media download or analysis inline — Twilio expects a fast response.
Full build in checkpoint 6 against the WhatsApp sandbox number.
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/webhook")
async def webhook() -> str:
    raise NotImplementedError("checkpoint 6")
