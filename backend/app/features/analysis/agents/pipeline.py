"""Agentic multi-signal pipeline (agentic-v1): one path for every modality.

Step 0 probe verdicts (2026-09-05, muse-spark-1.3-contributor-free via Zen
Responses API): text-only 200; vision 200 with normalized JPEG (>= 64px,
detail low, input_image/image_url) — tiny 1x1 JPEGs 500 upstream, so every
image is Pillow-normalized before sending; audio 200 with
input_audio/audio_url (data:audio/wav;base64 sine-tone probe returned valid
JSON with empty transcript, as expected). No fallback caps engaged: visual
and audio agents send real bytes. Text-only needs max_output_tokens >= 800
because reasoning tokens consume the headroom.

WhatsApp parity: forwards ride this identical pipeline with
source="whatsapp"; links pasted in chat go through analyze_link with the
same source. Unresolved link extractions are capped (never verified) and
run searcher-only on title/description/URL.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import subprocess
import tempfile
import time
from pathlib import Path
from app.core.config import settings
from app.db import usage
from app.features.analysis.agents import judge, links, muse_client, near_dup, sarvam, searcher, temporal

_TRACKER_PARAMS = frozenset(
    {"fbclid", "gclid", "si", "spm", "ref", "ref_src", "igshid", "mc_cid", "mc_eid"}
)


def _canonical_link(url: str) -> str:
    """Strip tracking params + fragments so shares of one link share a key."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url.strip())
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if k.lower() not in _TRACKER_PARAMS and not k.lower().startswith("utm_")
    ]
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", urlencode(kept), ""))


def _near_hit(case_id: str | None) -> dict | None:
    """Return the original verdict marked near-duplicate, if still cached."""
    if not case_id:
        return None
    hit = _cache_get(case_id)
    if hit is None:
        return None
    hit = dict(hit)
    hit["cached"] = "near-duplicate"
    hit["duplicate_of"] = case_id
    return hit


async def _log_usage(result: dict, *, modality: str, source: str, case_id: str) -> None:
    """Best-effort usage row; failures stay inside usage.log_case."""
    await usage.log_case(
        case_id=case_id,
        modality=modality,
        verdict=str(result.get("verdict", "")),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        source=source,
        cached=result.get("cached", False),
    )

_SARVAM_EXT = {
    "audio/mpeg": "audio.mp3",
    "audio/wav": "audio.wav",
    "audio/x-m4a": "audio.m4a",
    "audio/ogg": "audio.ogg",
    "audio/mp4": "audio.mp4",
}


def _sarvam_filename(mime: str) -> str:
    return _SARVAM_EXT.get(mime.lower(), "audio.mp3")

PIPELINE_VERSION = "agentic-v1"

_WEB_IMAGE_MAX = 25 * 1024 * 1024
_WHATSAPP_MAX = 16 * 1024 * 1024
_VIDEO_MAX_S = 120

_IMAGE_MIMES = ("image/jpeg", "image/png", "image/webp")
_VIDEO_MIMES = ("video/mp4", "video/mov", "video/webm")
_AUDIO_MIMES = ("audio/mpeg", "audio/wav", "audio/x-m4a", "audio/ogg", "audio/mp4")


class AnalysisError(Exception):
    """Loud pipeline failure: surfaces as a visible job error, never a fake verdict."""


def _cache_dir() -> Path:
    d = Path("storage/agentic_cache")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_get(key: str) -> dict | None:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if payload.get("model") != settings.muse_model or payload.get("version") != PIPELINE_VERSION:
        return None
    if time.time() - float(payload.get("saved_at", 0)) > 7 * 24 * 3600:
        return None
    result = payload.get("result")
    if isinstance(result, dict):
        result = dict(result)
        result["cached"] = True
        return result
    return None


def _cache_put(key: str, result: dict) -> None:
    path = _cache_dir() / f"{key}.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "model": settings.muse_model,
                    "version": PIPELINE_VERSION,
                    "saved_at": time.time(),
                    "result": result,
                }
            )
        )
    except OSError:
        pass


def _guard_bytes(data: bytes, *, source: str, kind: str) -> None:
    if not data:
        raise AnalysisError("Empty file: nothing to analyze.")
    if kind == "audio":
        cap_mb = settings.agent_max_audio_mb
        if len(data) > cap_mb * 1024 * 1024:
            raise AnalysisError(
                f"Audio is {len(data) // (1024 * 1024)} MB, over the {cap_mb} MB cap."
            )
        return
    if source == "whatsapp" and len(data) > _WHATSAPP_MAX:
        raise AnalysisError("File is over 16 MB — use the web upload instead.")
    if len(data) > _WEB_IMAGE_MAX:
        raise AnalysisError("File is over the 25 MB web-upload cap.")


def _normalize_image(data: bytes) -> bytes:
    """RGB, thumbnail 1024px, JPEG q80 re-encode (also upscales tiny probes)."""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGB")
            if img.width < 64 or img.height < 64:
                img = img.resize((max(64, img.width * 4), max(64, img.height * 4)), Image.NEAREST)
            img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=80)
            return buf.getvalue()
    except Exception as exc:
        raise AnalysisError(f"Unreadable image: {exc}") from exc


def _extract_frames(data: bytes, max_frames: int) -> list[bytes]:
    """Evenly spaced JPEG frames at ~1fps via the imageio-ffmpeg binary."""
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError as exc:
        raise AnalysisError(
            "imageio-ffmpeg is not installed; see https://ffmpeg.org/download.html."
        ) from exc
    with tempfile.TemporaryDirectory(prefix="lumen-frames-") as tmpdir:
        src = Path(tmpdir) / "src.mp4"
        src.write_bytes(data)
        out = str(Path(tmpdir) / "f%03d.jpg")
        proc = subprocess.run(
            [
                get_ffmpeg_exe(),
                "-y",
                "-i",
                str(src),
                "-vf",
                "fps=1",
                "-frames:v",
                str(max_frames),
                "-q:v",
                "3",
                out,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        if proc.returncode != 0:
            raise AnalysisError(f"Frame extraction failed: {proc.stderr.decode(errors='replace')[:300]}")
        frames: list[bytes] = []
        for path in sorted(Path(tmpdir).glob("f*.jpg"))[:max_frames]:
            try:
                frames.append(_normalize_image(path.read_bytes()))
            except AnalysisError:
                continue
        if not frames:
            raise AnalysisError("No frames could be extracted from this video.")
        return frames


def _apply_temporal_override(fused: dict, temporal_result: dict) -> dict:
    if temporal_result.get("flag") and fused.get("verdict") == "verified":
        fused = dict(fused)
        fused["verdict"] = "contradiction_detected"
        reasons = list(fused.get("reasons", []))
        reasons.append(f"Temporal check: {temporal_result.get('note', '')}")
        fused["reasons"] = reasons
    return fused


def _shape_result(
    *,
    verdict: str,
    confidence: float,
    explanation: str,
    reasons: list[str],
    signals: dict,
    sha256: str,
    caption: str,
    cached: bool = False,
) -> dict:
    return {
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "reasons": reasons,
        "signals": signals,
        "model_version": f"{settings.muse_model}@{PIPELINE_VERSION}",
        "evidence": {"sha256": sha256, "caption": caption},
        "cached": cached,
    }


async def run_search(*, caption: str, entities: list[str], ocr_text: str) -> dict:
    """Context-retrieval stage: Exa + DDG evidence for the tail."""
    try:
        return await searcher.search(caption, entities, ocr_text)
    except Exception as exc:
        raise AnalysisError(f"Search failed: {exc}") from exc


async def run_fusion(
    *,
    modality: str,
    perceptual: dict,
    meta_info: dict,
    search_result: dict,
    claimed_date: str | None,
    source: str,
    forensics_result: dict | None = None,
    sarvam_entry: dict | None = None,
    meta_dates: dict | None = None,
    unresolved_platform: str | None = None,
    sha256: str = "",
    caption: str = "",
) -> dict:
    """Fusion stage: temporal check + judge + overrides, shaped for callers."""
    if meta_dates is None:
        meta_dates = {
            "exif_date": (meta_info.get("exif") or {}).get("306"),
            "upload_date": meta_info.get("upload_date"),
        }
    temporal_result = temporal.check(
        meta_dates, search_result.get("exa_hits", []) + search_result.get("ddg_hits", []), claimed_date
    )
    signals = {
        "modality": modality,
        "perceptual": perceptual,
        "meta": meta_info,
        "search": search_result,
        "temporal": temporal_result,
    }
    if forensics_result is not None:
        signals["forensics"] = forensics_result
    if sarvam_entry is not None:
        signals["sarvam"] = sarvam_entry
    try:
        fused = await judge.fuse(signals, source)
    except muse_client.MuseError as exc:
        raise AnalysisError(f"Fusion failed: {exc}") from exc
    if unresolved_platform and fused.get("verdict") == "verified":
        fused = dict(fused)
        fused["verdict"] = "insufficient_evidence"
        fused["reasons"] = list(fused.get("reasons", [])) + [
            f"Unresolved extraction ({unresolved_platform}): "
            "no bytes to inspect, so verification is impossible."
        ]
    fused = _apply_temporal_override(fused, temporal_result)
    return _shape_result(
        verdict=fused["verdict"],
        confidence=fused["confidence"],
        explanation=fused["explanation"],
        reasons=fused["reasons"],
        signals=signals,
        sha256=sha256 or str(meta_info.get("sha256", "")),
        caption=caption,
    )


async def analyze_image(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Image verdicts via the case graph; signature frozen for callers."""
    if mime not in _IMAGE_MIMES:
        raise AnalysisError(f"Unsupported image MIME: {mime}")
    _guard_bytes(data, source=source, kind="image")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:img:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    if near := _near_hit(await asyncio.to_thread(near_dup.lookup_image, data)):
        return near
    from app.features.analysis.agents import graph  # lazy: graph imports pipeline

    result = await graph.run_case(
        modality="image",
        data=data,
        mime=mime,
        source=source,
        claimed_date=claimed_date,
        thread_id=cache_key,
    )
    result["case_id"] = cache_key
    _cache_put(cache_key, result)
    near_dup.remember_image(data, cache_key, "image")
    await _log_usage(result, modality="image", source=source, case_id=cache_key)
    return result


async def analyze_video(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Video verdicts via the case graph; signature frozen for callers."""
    if mime not in _VIDEO_MIMES:
        raise AnalysisError(f"Unsupported video MIME: {mime}")
    _guard_bytes(data, source=source, kind="video")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:vid:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    # Local frame extract for the instant path; the graph re-extracts on a
    # miss (~1s ffmpeg) — documented cost of keeping bytes out of state.
    probe_frames = await asyncio.to_thread(_extract_frames, data, settings.agent_max_frames)
    for frame in probe_frames:
        if near := _near_hit(await asyncio.to_thread(near_dup.lookup_image, frame)):
            return near
    from app.features.analysis.agents import graph  # lazy: graph imports pipeline

    result = await graph.run_case(
        modality="video",
        data=data,
        mime=mime,
        source=source,
        claimed_date=claimed_date,
        thread_id=cache_key,
    )
    result["case_id"] = cache_key
    _cache_put(cache_key, result)
    for frame in probe_frames:
        near_dup.remember_image(frame, cache_key, "video")
    await _log_usage(result, modality="video", source=source, case_id=cache_key)
    return result


async def analyze_audio(
    data: bytes, *, mime: str, source: str, claimed_date: str | None = None
) -> dict:
    """Audio verdicts via the case graph; signature frozen for callers."""
    if mime not in _AUDIO_MIMES:
        raise AnalysisError(f"Unsupported audio MIME: {mime}")
    _guard_bytes(data, source=source, kind="audio")
    cache_key = hashlib.sha256(f"{settings.muse_model}@{PIPELINE_VERSION}:aud:".encode() + data).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    from app.features.analysis.agents import graph  # lazy: graph imports pipeline

    # One STT call up front: a repeated viral voice note matches on its
    # transcript and skips the judge/search entirely. Misses reuse the
    # transcript inside the graph (no double STT).
    pre_sarvam = None
    if settings.sarvam_api_key:
        try:
            pre_sarvam = await sarvam.transcribe(data, filename=_sarvam_filename(mime))
            if near := _near_hit(
                await asyncio.to_thread(near_dup.lookup_transcript, pre_sarvam.get("transcript", ""))
            ):
                return near
        except sarvam.SarvamError:
            pre_sarvam = None
    result = await graph.run_case(
        modality="audio",
        data=data,
        mime=mime,
        source=source,
        claimed_date=claimed_date,
        thread_id=cache_key,
        pre_sarvam=pre_sarvam,
    )
    result["case_id"] = cache_key
    _cache_put(cache_key, result)
    transcript = ((result.get("signals", {}).get("sarvam") or {}).get("result") or {}).get("transcript", "")
    await asyncio.to_thread(near_dup.remember_transcript, transcript, cache_key)
    await _log_usage(result, modality="audio", source=source, case_id=cache_key)
    return result

async def analyze_link(url: str, *, source: str) -> dict:
    """Resolve a link, then dispatch on kind; unresolved stays searcher-only."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise AnalysisError("Link must start with http(s)://")
    cache_key = hashlib.sha256(
        f"{settings.muse_model}@{PIPELINE_VERSION}:link:{_canonical_link(url)}".encode()
    ).hexdigest()
    if hit := _cache_get(cache_key):
        return hit
    resolved = await links.resolve(url)
    kind = resolved.get("kind")
    metadata = resolved.get("metadata", {})
    if kind == "unresolved" or not resolved.get("data"):
        title = str(metadata.get("title") or "")
        desc = str(metadata.get("description") or "")
        caption_seed = " ".join([title, desc, url])[:2000]
        search_result = await run_search(
            caption=caption_seed, entities=[], ocr_text=caption_seed
        )
        result = await run_fusion(
            modality="link",
            perceptual={"note": resolved.get("note", "")},
            meta_info={"url": url, **metadata},
            search_result=search_result,
            claimed_date=metadata.get("upload_date"),
            source=source,
            meta_dates={"upload_date": metadata.get("upload_date")},
            unresolved_platform=str(metadata.get("platform", "unknown")),
            sha256=hashlib.sha256(url.encode()).hexdigest(),
            caption=caption_seed[:500],
        )
        result["case_id"] = cache_key
        _cache_put(cache_key, result)
        await _log_usage(result, modality="link", source=source, case_id=cache_key)
        return result
    data = resolved["data"]
    mime = resolved.get("mime") or "video/mp4"
    claimed = metadata.get("upload_date")
    if kind == "image":
        return await analyze_image(data, mime=mime, source=source, claimed_date=claimed)
    if kind == "audio":
        return await analyze_audio(data, mime=mime, source=source, claimed_date=claimed)
    return await analyze_video(data, mime=mime, source=source, claimed_date=claimed)
