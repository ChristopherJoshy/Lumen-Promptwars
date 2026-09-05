"""Ingestion HTTP surface: upload + link submit, verdicts inline.

No queue yet (Taskiq/Redis land later): submissions run the agentic
pipeline inline and return the verdict envelope. Typical image ~30s;
Render free-tier caps requests at 60s — large videos may exceed it and
should use smaller clips until background jobs land.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile

from app.features.analysis.agents import pipeline
from app.features.analysis.agents.pipeline import AnalysisError
from app.features.ingestion.schemas import LinkSubmit

router = APIRouter()

_UPLOAD_CAP = 25 * 1024 * 1024


async def _read_capped_upload(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > _UPLOAD_CAP:
            raise HTTPException(status_code=413, detail="File is over the 25 MB web-upload cap.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=422, detail="Empty file: nothing to analyze.")
    return data


def _envelope(result: dict) -> dict:
    return {
        "job_id": result.get("case_id", ""),
        "case_id": result.get("case_id", ""),
        "verdict": result.get("verdict", ""),
        "confidence": result.get("confidence", 0.0),
    }


@router.get("/status")
async def status() -> dict[str, str]:
    return {"ingestion": "live"}


@router.post("/upload")
async def upload(file: UploadFile) -> dict:
    """Analyze an uploaded file; returns the verdict envelope inline."""
    mime = (file.content_type or "").lower()
    data = await _read_capped_upload(file)
    try:
        if mime.startswith("image/"):
            result = await pipeline.analyze_image(data, mime=mime, source="upload")
        elif mime.startswith("video/"):
            result = await pipeline.analyze_video(data, mime=mime, source="upload")
        elif mime.startswith("audio/"):
            result = await pipeline.analyze_audio(data, mime=mime, source="upload")
        else:
            raise HTTPException(status_code=415, detail=f"Unsupported media type: {mime or 'unknown'}")
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _envelope(result)


@router.post("/link")
async def submit_link(body: LinkSubmit) -> dict:
    """Analyze a media link; returns the verdict envelope inline."""
    try:
        result = await pipeline.analyze_link(body.url, source="upload")
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _envelope(result)
