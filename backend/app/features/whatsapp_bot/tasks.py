"""WhatsApp Taskiq job: download -> analyze -> reply (checkpoint 6).

Inbound matrix (every forward rides the same agentic pipeline as upload):
image/* -> analyze_image, video/* -> analyze_video, audio/* (voice notes
included, no special-casing) -> analyze_audio, Body starting with
http(s):// -> analyze_link, anything else -> help text. All with
source="whatsapp". Total pipeline failure answers format_failure(), which
never resembles a verdict.
"""
from __future__ import annotations


def valid_twilio_signature(url: str, params: dict[str, str], signature: str, token: str) -> bool:
    """Twilio HMAC-SHA1 webhook check (stdlib only, no SDK).

    base64(HMAC-SHA1(token, public_url + sorted key+value pairs)).
    """
    import base64
    import hashlib
    import hmac

    if not url or not token or not signature:
        return False
    base = url + "".join(key + params[key] for key in sorted(params))
    digest = hmac.new(token.encode(), base.encode(), hashlib.sha1).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


HELP_TEXT = (
    "Send a photo, video, voice note, or paste a link and Lumen will check it. "
    "For files over 16 MB, use the web upload instead. "
    "After a verdict, just reply with questions about it."
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
_LAST_CASE: dict[str, str] = {}
_RECENT: dict[str, float] = {}


async def handle_inbound(payload: dict) -> str:
    """Route one inbound Twilio webhook payload through the pipeline.

    Args:
        payload: Twilio form fields (From, Body, NumMedia, MediaUrl0,
            MediaContentType0).

    Media and links run the full agentic pipeline and are remembered per
    sender, so follow-up questions chat about the last case. RETRY replays
    the last cached verdict. Anything else gets help text.

    Returns:
        The reply text that was (or would be) sent.
    """
    from app.core.config import settings
    from app.features.analysis import service as analysis_service
    from app.features.analysis.agents import pipeline as agentic
    from app.features.whatsapp_bot import client as wa_client
    from app.features.whatsapp_bot import media as wa_media
    from app.features.whatsapp_bot.messages import DISCLAIMER, format_failure, format_verdict

    sender = str(payload.get("From", ""))
    body = str(payload.get("Body", "") or "").strip()
    content_type = _pick_content_type(payload)
    media_url = str(payload.get("MediaUrl0", "") or "")

    import time as _time

    fingerprint = ""
    if content_type or body.startswith(("http://", "https://")):
        fingerprint = f"{sender}|{content_type}|{media_url}|{body[:200]}"
        last = _RECENT.get(fingerprint, 0.0)
        if _time.monotonic() - last < 60.0:
            return "(duplicate submission ignored)"
        _RECENT[fingerprint] = _time.monotonic()

    import logging

    log = logging.getLogger("lumen.whatsapp")

    async def reply(text: str, report_url: str = "") -> str:
        if sender:
            try:
                await wa_client.send_verdict(sender, text, report_url)
            except Exception as exc:
                log.warning("WhatsApp send to %s failed: %s", sender, exc)
        return text

    def _report_url(case_id: str) -> str:
        return f"{settings.frontend_url}/report/{case_id}"

    async def _answer_case(result: dict) -> str:
        import asyncio

        case_id = str(result.get("case_id", ""))
        if sender and case_id:
            _LAST_CASE[sender] = case_id
        url = _report_url(case_id)
        # Sandbox allows ~1 message per 3 s; the ack already used one slot.
        await asyncio.sleep(4)
        return await reply(
            format_verdict(result["verdict"], _first_sentence(result.get("explanation", "")), url),
            url,
        )

    if content_type.startswith("image/"):
        await reply("Photo received — running 7 forensic checks, origin scan, and web context. About 40 seconds…")
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_image(data, mime=content_type, source="whatsapp")
        except Exception as exc:
            return await reply(format_failure(str(exc)))
        return await _answer_case(result)
    if content_type.startswith("video/"):
        await reply("Video received — extracting frames and scanning each one. About a minute…")
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_video(data, mime=content_type, source="whatsapp")
        except Exception as exc:
            return await reply(format_failure(str(exc)))
        return await _answer_case(result)
    if content_type.startswith("audio/"):
        await reply("Voice note received — transcribing and checking for edits. About 40 seconds…")
        try:
            data = await wa_media.download(media_url)
            result = await agentic.analyze_audio(data, mime=content_type, source="whatsapp")
        except Exception as exc:
            return await reply(format_failure(str(exc)))
        return await _answer_case(result)
    if body.startswith(("http://", "https://")):
        await reply("Link received — fetching the media and scanning it. About a minute…")
        try:
            result = await agentic.analyze_link(body, source="whatsapp")
        except Exception as exc:
            return await reply(format_failure(str(exc)))
        return await _answer_case(result)
    if body.strip().upper() == "RETRY" and sender in _LAST_CASE:
        case = analysis_service.get_case(_LAST_CASE[sender])
        if case is not None:
            url = _report_url(_LAST_CASE[sender])
            return await reply(
                format_verdict(
                    str(case.get("verdict", "insufficient_evidence")),
                    _first_sentence(str(case.get("explanation", ""))),
                    url,
                ),
                url,
            )
        return await reply(
            "That case expired from the cache — please resend the photo, video, voice note, or link."
        )
    if body and sender in _LAST_CASE:
        try:
            answer = await analysis_service.answer_question(_LAST_CASE[sender], body)
        except Exception as exc:
            return await reply(format_failure(str(exc)))
        return await reply(f"{answer}\n\n{DISCLAIMER}")
    return await reply(HELP_TEXT)
