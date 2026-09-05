"""Ingestion HTTP surface: upload + link submit, verdicts inline.

No queue yet (Taskiq/Redis land later): submissions run the agentic
pipeline inline and return the verdict envelope. Typical image ~30s;
Render free-tier caps requests at 60s — large videos may exceed it and
should use smaller clips until background jobs land.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from app.features.analysis.agents import pipeline
from app.features.analysis.agents.pipeline import AnalysisError
from app.features.ingestion.schemas import LinkSubmit

router = APIRouter()

_UPLOAD_CAP = 25 * 1024 * 1024

_RATE_LIMIT = 20
_RATE_WINDOW = 60.0
_hits: dict[str, list[float]] = {}


def _sniff_kind(data: bytes) -> str | None:
    """Sniff the media kind from magic bytes; None when unrecognized.

    Returns a representative MIME type. Container formats shared by audio
    and video (MP4/MOV, WebM) report a video/* kind — the family check in
    _family_ok() treats both families as acceptable for those.
    """
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if len(data) >= 4 and data[:4] == b"OggS":
        return "audio/ogg"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "video/mp4"
    if len(data) >= 4 and data[:4] == b"\x1a\x45\xdf\xa3":
        return "video/webm"
    if len(data) >= 3 and data[:3] == b"ID3":
        return "audio/mpeg"
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return "audio/mpeg"
    return None


def _family_ok(sniffed: str, claimed: str) -> bool:
    """True when the claimed content-type family matches the sniffed kind.

    Dual-use containers (ftyp, WebM) accept either audio/* or video/*.
    """
    claimed_family = claimed.split("/", 1)[0] if "/" in claimed else ""
    if sniffed in ("video/mp4", "video/webm"):
        return claimed_family in ("video", "audio")
    sniffed_family = sniffed.split("/", 1)[0]
    return claimed_family == sniffed_family


def _check_upload_mime(data: bytes, mime: str) -> None:
    """Reject uploads whose sniffed kind family contradicts the claim (415).

    Unknown sniffs pass through — the pipeline fails loudly on its own.
    """
    sniffed = _sniff_kind(data)
    if sniffed is not None and not _family_ok(sniffed, mime):
        raise HTTPException(
            status_code=415,
            detail=f"Content-type {mime or 'unknown'} does not match file contents ({sniffed}).",
        )


def _rate_limited(ip: str) -> float | None:
    """Sliding-window check: 20 POSTs/minute per IP.

    Returns retry-after seconds when exceeded, else None. Prunes stale
    entries on every call so the dict cannot grow unboundedly.
    """
    now = time.monotonic()
    recent = [t for t in _hits.get(ip, []) if now - t < _RATE_WINDOW]
    if len(recent) >= _RATE_LIMIT:
        _hits[ip] = recent
        return _RATE_WINDOW - (now - recent[0])
    recent.append(now)
    _hits[ip] = recent
    return None


def _reset_rate_limits() -> None:
    """Clear all rate-limit counters (tests only)."""
    _hits.clear()


def _enforce_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    retry_after = _rate_limited(ip)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: 20 submissions per minute.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )


async def _read_capped_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
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
async def upload(request: Request) -> dict:
    """Analyze an uploaded file (raw body, Content-Type = media MIME)."""
    _enforce_rate_limit(request)
    mime = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    data = await _read_capped_body(request)
    _check_upload_mime(data, mime)
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
async def submit_link(body: LinkSubmit, request: Request) -> dict:
    """Analyze a media link; returns the verdict envelope inline."""
    _enforce_rate_limit(request)
    try:
        result = await pipeline.analyze_link(body.url, source="upload")
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _envelope(result)
