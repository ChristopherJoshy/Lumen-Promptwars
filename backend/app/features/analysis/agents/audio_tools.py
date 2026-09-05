"""Local numeric audio forensics: clipping, silence gaps, dynamic range.

Role: sole owner of waveform-level numeric evidence for voice notes.
Decodes WAV PCM via the stdlib ``wave`` module (+ numpy, no new deps) and
returns real measured numbers — never estimates or placeholders.

Loud-failure rule: empty bytes, non-WAV bytes, compressed WAV, unsupported
sample widths, and zero-frame files raise ``ValueError``. Callers that treat
these numbers as advisory (e.g. ``audio.analyze``) may degrade to
``audio_tools=None``; direct users get the exception.
"""
from __future__ import annotations

import io
import wave

import numpy as np

_CLIP_THRESH = 0.98  # fraction of full-scale above which a sample counts as clipped
_SILENCE_THRESH = 0.02  # below 2% full-scale counts as near-silent
_SILENCE_MIN_S = 0.15  # a near-silent span longer than this is one gap
_DR_WINDOW_S = 0.05  # RMS window for dynamic-range measurement


def _decode_mono(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV PCM bytes to mono float64 in [-1, 1] plus sample rate."""
    if not wav_bytes:
        raise ValueError("audio_tools.examine_audio received empty bytes.")
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as w:
            if w.getcomptype() != "NONE":
                raise ValueError(
                    f"audio_tools: compressed WAV unsupported (comptype={w.getcomptype()!r})."
                )
            nch, sw, sr, nframes = (
                w.getnchannels(),
                w.getsampwidth(),
                w.getframerate(),
                w.getnframes(),
            )
            raw = w.readframes(nframes)
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError(f"audio_tools: not valid WAV bytes: {exc}") from exc
    if nframes == 0:
        raise ValueError("audio_tools: WAV contains no audio frames.")
    if len(raw) < nframes * nch * sw:
        raise ValueError("audio_tools: WAV data truncated.")
    if sw == 1:  # 8-bit PCM is unsigned
        mono = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif sw == 2:
        mono = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sw == 3:  # 24-bit little-endian PCM: sign-extend manually
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = a[:, 0] + (a[:, 1] << 8) + (a[:, 2] << 16)
        v -= (v & 0x800000) << 1
        mono = v.astype(np.float64) / 8388608.0
    elif sw == 4:
        mono = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"audio_tools: unsupported WAV sample width: {sw} bytes.")
    mono = mono.reshape(nframes, nch).mean(axis=1)
    return mono, sr


def examine_audio(wav_bytes: bytes) -> dict:
    """Measure clipping, silence gaps, and dynamic range of WAV bytes.

    Returns:
        Dict with ``clip_ratio`` (fraction of samples beyond 0.98
        full-scale), ``silence_gaps`` (count of >150ms near-silent spans),
        ``dynamic_range_db`` (20*log10 of max/min 50ms-window RMS over
        non-silent windows; 0.0 when fewer than two speak windows exist),
        and ``score`` 0..1 fused as ``min(1, clip*3 + gaps*0.15 +
        (1-min(dr,60)/60)*0.3)`` (flat/compressed audio scores higher;
        natural speech-vs-pause contrast scores lower).

    Raises:
        ValueError: empty or non-WAV bytes, compressed/unsupported WAV.
    """
    mono, sr = _decode_mono(wav_bytes)
    clip_ratio = float(np.mean(np.abs(mono) > _CLIP_THRESH))

    silent = np.abs(mono) < _SILENCE_THRESH
    min_len = max(1, int(sr * _SILENCE_MIN_S))
    edges = np.diff(silent.astype(np.int8), prepend=0, append=0)
    starts = np.nonzero(edges == 1)[0]
    ends = np.nonzero(edges == -1)[0]
    silence_gaps = int(np.sum((ends - starts) > min_len))

    win = max(1, int(sr * _DR_WINDOW_S))
    nwin = len(mono) // win
    if nwin < 2:
        dynamic_range_db = 0.0
    else:
        rms = np.sqrt(
            (mono[: nwin * win].reshape(nwin, win).astype(np.float64) ** 2).mean(axis=1)
        )
        voiced = rms[rms >= _SILENCE_THRESH]
        if len(voiced) < 2:
            dynamic_range_db = 0.0
        else:
            dynamic_range_db = float(max(0.0, 20.0 * np.log10(voiced.max() / voiced.min())))

    score = min(
        1.0,
        clip_ratio * 3.0
        + silence_gaps * 0.15
        + (1.0 - min(dynamic_range_db, 60.0) / 60.0) * 0.3,
    )
    return {
        "clip_ratio": clip_ratio,
        "silence_gaps": silence_gaps,
        "dynamic_range_db": dynamic_range_db,
        "score": float(score),
    }
