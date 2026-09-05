"""Voice forensics role: all 22 scheduled Indian languages via Sarvam."""
from __future__ import annotations

import base64

from app.features.analysis.agents import audio_tools, muse_client, prompt_pack

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


def _to_wav(audio_bytes: bytes) -> bytes:
    """Transcode to 16 kHz mono WAV: Zen audio input rejects Opus-in-ogg
    (live 400, 2026-09-05) the way it once rejected tiny JPEGs — normalize,
    never downgrade to a text-only verdict."""
    import subprocess
    import tempfile
    from pathlib import Path

    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError as exc:
        raise ValueError(
            "imageio-ffmpeg is not installed; see https://ffmpeg.org/download.html."
        ) from exc
    with tempfile.TemporaryDirectory(prefix="lumen-audio-") as tmpdir:
        src = Path(tmpdir) / "src"
        src.write_bytes(audio_bytes)
        out = Path(tmpdir) / "norm.wav"
        proc = subprocess.run(
            [get_ffmpeg_exe(), "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        if proc.returncode != 0:
            raise ValueError(f"Audio transcode failed: {proc.stderr.decode(errors='replace')[:200]}")
        return out.read_bytes()


async def analyze(audio_bytes: bytes, mime: str, sarvam_hint: dict | None = None) -> dict:
    """Analyze audio for synthesis/editing cues plus transcript hint.

    Args:
        audio_bytes: Raw audio bytes (caller enforces size/duration caps).
        mime: Original MIME type.
        sarvam_hint: optional sarvam.transcribe() output; the transcript is
            ground truth and detected_language overrides language_guess.

    Returns:
        Dict with observations, artifact_score, transcript_hint,
        language_guess, entities, audio_tools (examine_audio dict or None).

    Raises:
        muse_client.MuseError: Zen call failed or returned bad JSON.
    """
    if not audio_bytes:
        raise ValueError("audio.analyze received empty bytes.")
    if mime.lower() in ("audio/wav", "audio/x-wav"):
        listen_bytes, data_mime = audio_bytes, "audio/wav"
    else:
        listen_bytes, data_mime = _to_wav(audio_bytes), "audio/wav"
    # Local numeric forensics are advisory: undecodable bytes degrade to
    # audio_tools=None (today's wav path never validated, and the suite pins
    # b"audio" flowing to the model) while empty/transcode failures above
    # still raise loudly as before. examine_audio itself stays loud.
    try:
        tool_scores = audio_tools.examine_audio(listen_bytes)
    except ValueError:
        tool_scores = None
    b64 = base64.b64encode(listen_bytes).decode()
    user_text = "Analyze this audio. Return JSON only, no commentary."
    if sarvam_hint:
        user_text += (
            f" Ground-truth transcript ({sarvam_hint.get('detected_language', 'unknown')}): "
            f"{sarvam_hint.get('transcript', '')}"
            + (f" / English: {sarvam_hint.get('translated_en')}" if sarvam_hint.get("translated_en") else "")
            + " Do not re-transcribe; judge synthesis/editing cues only."
        )
    if tool_scores is not None:
        user_text += (
            f" Local numeric audio forensics: clip_ratio={tool_scores['clip_ratio']:.3f},"
            f" silence_gaps={tool_scores['silence_gaps']},"
            f" dynamic_range_db={tool_scores['dynamic_range_db']:.1f} dB."
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
        "audio_tools": tool_scores,
    }
