"""Voice forensics role: Indic-first (Malayalam/Hindi/Tamil/Telugu)."""
from __future__ import annotations

import base64

from app.features.analysis.agents import muse_client

_SYSTEM = (
    "You are a voice-forensics analyst for Lumen. The input is a voice note "
    "or audio clip, very likely in Malayalam, Hindi, Tamil, or Telugu — "
    "treat those four as first-class expected inputs, not edge cases. "
    "Listen for signs of AI generation or editing: robotic/flat prosody, "
    "unnatural pauses, splicing clicks, background-noise discontinuities, "
    "reverberation mismatch, claimed language vs heard language. Transcribe "
    "a short fragment verbatim as transcript_hint, guess the language "
    "(malayalam | hindi | tamil | telugu | english | other | unknown), and "
    "name entities claimed in the audio (people, places, schemes, events). "
    "Return JSON ONLY with exactly these keys: "
    '{"observations": [str], "artifact_score": float 0..1, '
    '"transcript_hint": str, "language_guess": str, "entities": [str]}. '
    "artifact_score is suspicion of AI generation/editing "
    "(0 = natural human speech, 1 = certainly synthetic)."
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
