"""WhatsApp webhook schemas (Twilio form fields)."""
from pydantic import BaseModel


class InboundMessage(BaseModel):
    From: str = ""
    Body: str = ""
    NumMedia: int = 0
    MediaUrl0: str = ""
