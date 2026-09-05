"""Video forensics entrypoint: Muse agentic pipeline (agentic-v1).

Supersedes the local-model checkpoint 13 plan for v1 (stretch): frames are
analyzed by the visual agent and aggregated in agents.pipeline.analyze_video.
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


async def detect(video_path: str) -> dict:
    """Run agentic video forensics over a local file.

    Args:
        video_path: Local path or object-storage key readable from disk.

    Returns:
        Dict with label, confidence, evidence_path, model_version.

    Raises:
        FileNotFoundError: Path does not exist.
        AnalysisError: Pipeline failure (surfaces loudly, never faked).
    """
    from app.features.analysis.agents.pipeline import analyze_video

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    suffix = path.suffix.lower()
    mime = {"mp4": "video/mp4", "mov": "video/mov", "webm": "video/webm"}.get(
        suffix.lstrip("."), "video/mp4"
    )
    data = await asyncio.to_thread(path.read_bytes)
    result = await analyze_video(data, mime=mime, source="upload")
    sha = result.get("evidence", {}).get("sha256", "unknown")
    evidence_path = Path("storage") / f"detector_video_{sha[:16]}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(evidence_path.write_text, json.dumps(result, default=str))
    return {
        "label": _map_label(result["verdict"]),
        "confidence": result["confidence"],
        "evidence_path": str(evidence_path),
        "model_version": result["model_version"],
    }
