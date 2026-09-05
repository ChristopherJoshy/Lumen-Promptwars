"""Image forensics entrypoint: Muse agentic pipeline (agentic-v1).

Supersedes the local-model checkpoint 7 plan for v1: no local weights are
shipped (repo stays under 10 MB), so this delegates to
agents.pipeline.analyze_image. See docs/skills/detector-module.md.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path


def _map_label(verdict: str) -> str:
    """Map pipeline verdicts onto the detector-module contract."""
    if verdict == "verified":
        return "authentic"
    if verdict == "likely_synthetic":
        return "synthetic"
    return "uncertain"


async def detect(image_path: str) -> dict:
    """Run agentic image forensics over a local file.

    Args:
        image_path: Local path or object-storage key readable from disk.

    Returns:
        Dict with label, confidence, evidence_path, model_version.

    Raises:
        FileNotFoundError: Path does not exist.
        AnalysisError: Pipeline failure (surfaces loudly, never faked).
    """
    from app.features.analysis.agents.pipeline import analyze_image

    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    suffix = path.suffix.lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        suffix.lstrip("."), "image/jpeg"
    )
    data = await asyncio.to_thread(path.read_bytes)
    result = await analyze_image(data, mime=mime, source="upload")
    sha = result.get("evidence", {}).get("sha256", "unknown")
    evidence_path = Path("storage") / f"detector_image_{sha[:16]}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(evidence_path.write_text, json.dumps(result, default=str))
    return {
        "label": _map_label(result["verdict"]),
        "confidence": result["confidence"],
        "evidence_path": str(evidence_path),
        "model_version": result["model_version"],
    }
