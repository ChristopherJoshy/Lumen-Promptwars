"""Link resolver: yt-dlp as a library, capped, never raising on blocks."""
from __future__ import annotations

import asyncio
import hashlib
import tempfile
from pathlib import Path

from app.features.ingestion.platform_detect import detect_platform

_MAX_FILESIZE = 25 * 1024 * 1024


def _guess_kind(mime: str | None, ext: str) -> str:
    ext = (ext or "").lower()
    if ext in ("jpg", "jpeg", "png", "webp") or (mime or "").startswith("image/"):
        return "image"
    if ext in ("mp3", "wav", "m4a", "ogg", "opus") or (mime or "").startswith("audio/"):
        return "audio"
    return "video"


def _extract(url: str) -> dict:
    import yt_dlp

    tmpdir = tempfile.mkdtemp(prefix="lumen-link-")
    outtmpl = str(Path(tmpdir) / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "noplaylist": True,
        "socket_timeout": 15,
        "outtmpl": outtmpl,
        "no_warnings": True,
        "max_filesize": _MAX_FILESIZE,
        "format": "best[filesize<?25M]/best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return {"info": info or {}, "tmpdir": tmpdir}


def _ssrf_blocked(url: str) -> str | None:
    """Return a reason when the URL targets non-public hosts, else None."""
    import ipaddress
    import socket
    from urllib.parse import urlsplit

    try:
        host = urlsplit(url).hostname or ""
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except Exception:
        return "host does not resolve to a public address"
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
        return "host is not a public address"
    return None


async def resolve(url: str) -> dict:
    """Resolve a public link to downloadable bytes plus metadata.

    Args:
        url: Public media/page URL.

    Returns:
        Dict with kind (image | video | audio | unresolved), data, mime,
        metadata (uploader, upload_date, title, description, platform),
        note. Platform blocks (Instagram/X datacenter rejects, some
        Telegram links) return unresolved with the platform named plus
        the direct-upload remedy — never an exception, never silence.
    """
    platform = detect_platform(url)
    blocked = _ssrf_blocked(url)
    if blocked:
        return {
            "kind": "unresolved",
            "data": None,
            "mime": None,
            "metadata": {
                "uploader": "",
                "upload_date": None,
                "title": "",
                "description": "",
                "platform": platform,
            },
            "note": f"Refused {blocked}; only public media links are fetched.",
        }
    try:
        result = await asyncio.to_thread(_extract, url)
    except Exception as exc:
        return {
            "kind": "unresolved",
            "data": None,
            "mime": None,
            "metadata": {
                "uploader": "",
                "upload_date": None,
                "title": "",
                "description": "",
                "platform": platform,
            },
            "note": (
                f"{platform} extraction failed ({type(exc).__name__}); "
                "upload the file directly instead."
            ),
        }
    info = result.get("info", {})
    tmpdir = result.get("tmpdir", "")
    files = sorted(Path(tmpdir).glob("*")) if tmpdir else []
    data: bytes | None = None
    mime: str | None = None
    ext = str(info.get("ext", ""))
    if files:
        biggest = max(files, key=lambda p: p.stat().st_size if p.is_file() else -1)
        if biggest.is_file() and biggest.stat().st_size <= _MAX_FILESIZE:
            data = biggest.read_bytes()
            suffix = biggest.suffix.lower().lstrip(".")
            if suffix in ("jpg", "jpeg"):
                mime = "image/jpeg"
            elif suffix == "png":
                mime = "image/png"
            elif suffix == "webp":
                mime = "image/webp"
            elif suffix in ("mp3",):
                mime = "audio/mpeg"
            elif suffix in ("wav",):
                mime = "audio/wav"
            elif suffix in ("m4a", "mp4") and _guess_kind("", suffix) == "audio":
                mime = "audio/mp4"
            elif suffix in ("ogg", "opus"):
                mime = "audio/ogg"
            elif suffix in ("mov",):
                mime = "video/mov"
            elif suffix in ("webm",):
                mime = "video/webm"
            else:
                mime = "video/mp4"
            ext = suffix
    metadata = {
        "uploader": str(info.get("uploader") or info.get("channel") or ""),
        "upload_date": info.get("upload_date"),
        "title": str(info.get("title") or ""),
        "description": str(info.get("description") or "")[:2000],
        "platform": platform,
    }
    if data is None:
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        _ = digest
        return {
            "kind": "unresolved",
            "data": None,
            "mime": None,
            "metadata": metadata,
            "note": (
                f"{platform} extraction returned no downloadable file; "
                "upload the file directly instead."
            ),
        }
    kind = _guess_kind(mime, ext)
    return {"kind": kind, "data": data, "mime": mime, "metadata": metadata, "note": ""}
