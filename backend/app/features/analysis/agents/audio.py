"""Voice forensics role: all 22 scheduled Indian languages via Sarvam."""
from __future__ import annotations

import base64

from app.features.analysis.agents import muse_client, prompt_pack

_SYSTEM = (
    "You are a voice-forensics analyst for Lumen. The input is a voice note "
    "or audio clip in ANY Indian language — Hindi, Bengali, Marathi, Telugu, "
    "Tamil, Gujarati, Kannada, Malayalam, Odia, Punjabi, Urdu, Assamese, and "
    "the rest of the 22 scheduled languages, plus Indian English — all are "
    "first-class expected inputs. Code-mixing (Hinglish, Tanglish) is normal "
    "speech, never a synthetic tell. When a ground-truth transcript is "
    "provided, do NOT re-transcribe: judge synthesis/editing cues only "
    "(robotic/flat prosody, unnatural pauses, splicing clicks, "
    "background-noise discontinuities, reverberation mismatch, claimed "
    "language vs heard language). language_guess is a free-form lowercase "
    "language name (e.g. malayalam, hindi, tamil, bengali, en-IN). Name "
    "entities claimed in the audio (people, places, schemes, events). "
    "Return JSON ONLY with exactly these keys: "
    '{"observations": [str], "artifact_score": float 0..1, '
    '"transcript_hint": str, "language_guess": str, "entities": [str]}. '
    "artifact_score is suspicion of AI generation/editing "
    "(0 = natural human speech, 1 = certainly synthetic).\n"
    + prompt_pack.load("forward_tells")
)

_MIME_TO_DATA = {
    "audio/mpeg": "audio/mp3",
    "audio/mp3": "audio/mp3",
    "audio/wav": "audio/wav",
    "audio/x-wav": "audio/wav",
    "audio/ogg": "audio/ogg",
    "audio/mp4": "audio/mp4",
    "audio/x-m4a": "audio/mp4",
}


async def analyze(audio_bytes: bytes, mime: str, sarvam_hint: dict | None = None) -> dict:
    """Analyze audio for synthesis/editing cues plus transcript hint.

    Args:
        audio_bytes: Raw audio bytes (caller enforces size/duration caps).
        mime: Original MIME type.
        sarvam_hint: optional sarvam.transcribe() output; the transcript is
            ground truth and detected_language overrides language_guess.

    Returns:
        Dict with observations, artifact_score, transcript_hint,
        language_guess, entities.

    Raises:
        muse_client.MuseError: Zen call failed or returned bad JSON.
    """
    if not audio_bytes:
        raise ValueError("audio.analyze received empty bytes.")
    data_mime = _MIME_TO_DATA.get(mime.lower(), "audio/mp3")
    b64 = base64.b64encode(audio_bytes).decode()
    user_text = "Analyze this audio. Return JSON only, no commentary."
    if sarvam_hint:
        user_text += (
            f" Ground-truth transcript ({sarvam_hint.get('detected_language', 'unknown')}): "
            f"{sarvam_hint.get('transcript', '')}"
            + (f" / English: {sarvam_hint.get('translated_en')}" if sarvam_hint.get("translated_en") else "")
            + " Do not re-transcribe; judge synthesis/editing cues only."
        )
    parts = [
        {
            "type": "input_text",
            "text": user_text,
        },
        {"type": "input_audio", "audio_url": f"data:{data_mime};base64,{b64}"},
    ]
    result = await muse_client.respond(_SYSTEM, parts)
    for key in ("observations", "artifact_score", "transcript_hint", "language_guess", "entities"):
        if key not in result:
            raise muse_client.MuseError(f"Audio agent omitted key: {key}")
    try:
        result["artifact_score"] = float(result["artifact_score"])
    except (TypeError, ValueError) as exc:
        raise muse_client.MuseError("Audio agent artifact_score is not a number.") from exc
    if not 0.0 <= result["artifact_score"] <= 1.0:
        raise muse_client.MuseError("Audio agent artifact_score outside 0..1.")
    language_guess = str(result["language_guess"])
    transcript_hint = str(result["transcript_hint"])
    if sarvam_hint and sarvam_hint.get("detected_language"):
        language_guess = str(sarvam_hint["detected_language"])  # instrument wins
        transcript_hint = str(sarvam_hint.get("transcript") or transcript_hint)
    return {
        "observations": list(result["observations"]),
        "artifact_score": result["artifact_score"],
        "transcript_hint": transcript_hint,
        "language_guess": language_guess,
        "entities": list(result["entities"]),
    }
