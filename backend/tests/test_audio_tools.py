"""Audio forensics: local numeric instruments + analyze wiring. No network."""
from __future__ import annotations

import asyncio
import io
import wave

import numpy as np
import pytest

from app.features.analysis.agents import audio as audio_agent
from app.features.analysis.agents import audio_tools


def _wav(samples: np.ndarray, sr: int = 16000) -> bytes:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _sine(sr=16000, dur=1.0, freq=440.0, amp=0.5, gap=None) -> np.ndarray:
    t = np.arange(int(sr * dur)) / sr
    s = amp * np.sin(2 * np.pi * freq * t)
    if gap:
        s[int(gap[0] * sr) : int(gap[1] * sr)] = 0.0
    return s


def test_clipped_sine_scores_above_clean():
    clean = audio_tools.examine_audio(_wav(_sine(amp=0.5)))
    clipped = audio_tools.examine_audio(_wav(_sine(amp=0.5) * 4.0))
    assert clipped["clip_ratio"] > clean["clip_ratio"]
    assert clean["clip_ratio"] == 0.0
    assert clipped["score"] > clean["score"]


def test_silence_gaps_counted_on_gapped_fixture():
    clean = audio_tools.examine_audio(_wav(_sine()))
    gapped = audio_tools.examine_audio(_wav(_sine(gap=(0.3, 0.6))))
    assert clean["silence_gaps"] == 0
    assert gapped["silence_gaps"] == 1


def test_rejects_empty_and_non_wav():
    with pytest.raises(ValueError):
        audio_tools.examine_audio(b"")
    with pytest.raises(ValueError):
        audio_tools.examine_audio(b"not-a-wav-file")


def test_analyze_returns_audio_tools_and_prompts_numbers(monkeypatch):
    seen: dict = {}

    async def fake_respond(system, parts, **kwargs):
        seen["text"] = parts[0]["text"]
        return {
            "observations": ["o"],
            "artifact_score": 0.2,
            "transcript_hint": "model guess",
            "language_guess": "hindi",
            "entities": [],
        }

    monkeypatch.setattr(audio_agent.muse_client, "respond", fake_respond)
    out = asyncio.run(audio_agent.analyze(_wav(_sine(gap=(0.2, 0.5))), "audio/wav"))
    assert out["audio_tools"]["silence_gaps"] == 1
    assert "clip_ratio=" in seen["text"] and "silence_gaps=" in seen["text"]


def test_analyze_degrades_to_none_on_undecodable_wav(monkeypatch):
    async def fake_respond(system, parts, **kwargs):
        return {
            "observations": ["o"],
            "artifact_score": 0.2,
            "transcript_hint": "t",
            "language_guess": "hindi",
            "entities": [],
        }

    monkeypatch.setattr(audio_agent.muse_client, "respond", fake_respond)
    out = asyncio.run(audio_agent.analyze(b"audio", "audio/wav"))
    assert out["audio_tools"] is None
