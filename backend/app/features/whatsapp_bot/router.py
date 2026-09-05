"""Twilio webhook: validate signature, run the real pipeline, return TwiML.

No Taskiq yet, so analysis runs inline: the verdict is delivered through
the Twilio Messages API by handle_inbound, and the webhook answers an empty
TwiML Response. Slow cases may outrun Twilio's ~15 s webhook timeout, but
the verdict still arrives as a WhatsApp message.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from xml.sax.saxutils import escape

from app.core.config import settings
from app.features.whatsapp_bot.tasks import handle_inbound, valid_twilio_signature

router = APIRouter()


@router.post("/webhook")
async def webhook(request: Request) -> Response:
    """Accept one inbound Twilio message; 403 on missing/bad signature."""
    token = settings.twilio_auth_token
    if not token:
        raise HTTPException(status_code=403, detail="WhatsApp webhook is not configured.")
    public_url = settings.twilio_webhook_url
    if not public_url:
        raise HTTPException(status_code=403, detail="twilio_webhook_url is not configured.")
    signature = request.headers.get("X-Twilio-Signature", "")
    try:
        form = await request.form()
    except AssertionError as exc:
        raise HTTPException(status_code=500, detail=f"Form parsing unavailable: {exc}") from exc
    params = {str(k): str(v) for k, v in form.multi_items()}
    if not valid_twilio_signature(public_url, params, signature, token):
        raise HTTPException(status_code=403, detail="Bad webhook signature.")
    reply = await handle_inbound(params)
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(reply)}</Message></Response>"
    )
    return Response(content=twiml, media_type="text/xml")
