"""WhatsApp Taskiq job: download -> analyze -> reply (checkpoint 6).

Inbound matrix (every forward rides the same agentic pipeline as upload):
image/* -> analyze_image, video/* -> analyze_video, audio/* (voice notes
included, no special-casing) -> analyze_audio, Body starting with
http(s):// -> analyze_link, anything else -> help text. All with
source="whatsapp". Total pipeline failure answers format_failure(), which
never resembles a verdict.
"""
from __future__ import annotations


HELP_TEXT = (
    "Send a photo, video, voice note, or paste a link and Lumen will check it. "
    "For files over 16 MB, use the web upload instead."
)


def _pick_content_type(payload: dict) -> str:
    for key in ("MediaContentType0", "MediaContentType", "ContentType"):
        value = payload.get(key)
        if value:
            return str(value).split(";")[0].strip().lower()
    num = str(payload.get("NumMedia", "0"))
    if num not in ("0", "") and payload.get("MediaUrl0"):
        return "image/jpeg"
    return ""


def _first_sentence(text: str) -> str:
    text = " ".join(text.strip().split())
    for sep in (". ", "! ", "? "):
        if sep in text:
            return text.split(sep)[0].strip().rstrip(".!?") + "."
    return text[:280]


async def handle_inbound(payload: dict) -> str:
    """Route one inbound Twilio webhook payload through the pipeline.

    Args:
        payload: Twilio form fields (From, Body, NumMedia, MediaUrl0,
            MediaContentType0).

    Returns:
        The reply text that was (or would be) sent.
    """
    from app.core.config import settings
    from app.features.analysis.agents import pipeline as agentic
    from app.features.whatsapp_bot import client as wa_client
    from app.features.whatsapp_bot import media as wa_media
    from app.features.whatsapp_bot.messages import format_failure, format_verdict

    sender = str(payload.get("From", ""))
    body = str(payload.get("Body", "") or "").strip()
    content_type = _pick_content_type(payload)
    media_url = str(payload.get("MediaUrl0", "") or "")

    async def reply(text: str, report_url: str = "") -> str:
        if sender:
            try:
                await wa_client.send_verdict(sender, text, report_url)
            except Exception:
                pass
        return text

    if content_type.startswith("image/"):
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_image(data, mime="image/jpeg", source="whatsapp")
        except Exception:
            return await reply(format_failure())
        sha = result.get("evidence", {}).get("sha256", "")[:12]
        url = f"{settings.frontend_url}/report/{sha}"
        return await reply(format_verdict(result["verdict"], _first_sentence(result.get("explanation", "")), url), url)
    if content_type.startswith("video/"):
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_video(data, mime="video/mp4", source="whatsapp")
        except Exception:
            return await reply(format_failure())
        sha = result.get("evidence", {}).get("sha256", "")[:12]
        url = f"{settings.frontend_url}/report/{sha}"
        return await reply(format_verdict(result["verdict"], _first_sentence(result.get("explanation", "")), url), url)
    if content_type.startswith("audio/"):
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_audio(data, mime="audio/mpeg", source="whatsapp")
        except Exception:
            return await reply(format_failure())
        sha = result.get("evidence", {}).get("sha256", "")[:12]
        url = f"{settings.frontend_url}/report/{sha}"
        return await reply(format_verdict(result["verdict"], _first_sentence(result.get("explanation", "")), url), url)
    if body.startswith(("http://", "https://")):
        try:
            result = await agentic.analyze_link(body, source="whatsapp")
        except Exception:
            return await reply(format_failure())
        sha = result.get("evidence", {}).get("sha256", "")[:12]
        url = f"{settings.frontend_url}/report/{sha}"
        return await reply(format_verdict(result["verdict"], _first_sentence(result.get("explanation", "")), url), url)
    return await reply(HELP_TEXT)
