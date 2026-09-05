"""Sarvam voice tool: ground-truth transcripts in all 22 scheduled Indian languages.

Saaras v3/v4 auto-detects the spoken language when language_code is
"unknown" (docs.sarvam.ai, verified 2026-09-05 — earlier plan draft said to
omit the field; the docs say send "unknown", with omit-and-retry as the
400 fallback). Raw httpx, no vendor SDK — same rule as muse_client.
"""

from __future__ import annotations

import httpx

from app.core.config import settings

_TRANSLATE_MODES = ("transcribe", "translate")


class SarvamError(Exception):
    """Loud Sarvam failure: pipeline degrades to Muse-only with a warning."""


async def _call(
    audio_bytes: bytes,
    *,
    mode: str,
    language_code: str | None,
    filename: str,
    client: httpx.AsyncClient,
) -> dict:
    data: dict[str, str] = {"model": settings.sarvam_model, "mode": mode}
    if language_code is not None:
        data["language_code"] = language_code
    resp = await client.post(
        f"{settings.sarvam_base_url}/speech-to-text",
        headers={"api-subscription-key": settings.sarvam_api_key},
        files={"file": (filename, audio_bytes)},
        data=data,
    )
    if resp.status_code == 400 and language_code is not None:
        # Field-shape rejection: retry once without language_code, then give up.
        data.pop("language_code", None)
        resp = await client.post(
            f"{settings.sarvam_base_url}/speech-to-text",
            headers={"api-subscription-key": settings.sarvam_api_key},
            files={"file": (filename, audio_bytes)},
            data=data,
        )
    if resp.status_code >= 400:
        raise SarvamError(f"Sarvam {mode} failed: HTTP {resp.status_code}.")
    try:
        return resp.json()
    except ValueError as exc:
        raise SarvamError(f"Sarvam {mode} returned non-JSON.") from exc


async def transcribe(
    audio_bytes: bytes,
    *,
    language_code: str | None = None,
    filename: str = "audio.mp3",
) -> dict:
    """Transcribe any Indian-language audio; auto-detect when code unknown.

    Returns exactly {transcript, detected_language, translated_en}.
    translated_en comes from a second mode="translate" call, skipped when
    the detected language is English or the transcript is empty.
    """
    if not audio_bytes:
        raise SarvamError("transcribe received empty bytes.")
    if not settings.sarvam_api_key:
        raise SarvamError("sarvam_api_key is not configured; Sarvam skipped.")
    async with httpx.AsyncClient(timeout=settings.agent_timeout_s) as client:
        first = await _call(
            audio_bytes,
            mode="transcribe",
            language_code=language_code or "unknown",
            filename=filename,
            client=client,
        )
        transcript = str(first.get("transcript") or "")
        detected = str(first.get("language_code") or "unknown")
        translated_en = ""
        if transcript and not detected.lower().startswith("en"):
            second = await _call(
                audio_bytes,
                mode="translate",
                language_code=detected if detected != "unknown" else None,
                filename=filename,
                client=client,
            )
            translated_en = str(second.get("transcript") or "")
        return {
            "transcript": transcript,
            "detected_language": detected,
            "translated_en": translated_en,
        }
