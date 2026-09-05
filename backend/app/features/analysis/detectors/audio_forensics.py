"""Audio forensics entrypoint: Muse agentic pipeline (agentic-v1).

Supersedes the local-model checkpoint 5 plan for v1: Indic-first priority
(Malayalam/Hindi/Tamil/Telugu) now lives in the audio agent's prompt rather
than in local-model tuning.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path


def _map_label(verdict: str) -> str:
    if verdict == "verified":
        return "authentic"
    if verdict == "likely_synthetic":
        return "synthetic"
    return "uncertain"


async def detect(audio_path: str) -> dict:
    """Run agentic audio forensics over a local file.

    Args:
        audio_path: Local path or object-storage key readable from disk.

    Returns:
        Dict with label, confidence, evidence_path, model_version.

    Raises:
        FileNotFoundError: Path does not exist.
        AnalysisError: Pipeline failure (surfaces loudly, never faked).
    """
    from app.features.analysis.agents.pipeline import analyze_audio

    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio not found: {audio_path}")
    suffix = path.suffix.lower().lstrip(".")
    mime = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "ogg": "audio/ogg",
        "opus": "audio/ogg",
    }.get(suffix, "audio/mpeg")
    data = await asyncio.to_thread(path.read_bytes)
    result = await analyze_audio(data, mime=mime, source="upload")
    sha = result.get("evidence", {}).get("sha256", "unknown")
    evidence_path = Path("storage") / f"detector_audio_{sha[:16]}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(evidence_path.write_text, json.dumps(result, default=str))
    return {
        "label": _map_label(result["verdict"]),
        "confidence": result["confidence"],
        "evidence_path": str(evidence_path),
        "model_version": result["model_version"],
    }
