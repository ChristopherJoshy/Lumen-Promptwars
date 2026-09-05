"""Pure-code metadata reader: Pillow for images, ffmpeg for durations."""
from __future__ import annotations

import hashlib
import io
import re
import subprocess

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")


def _ffmpeg_exe() -> str:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError as exc:
        raise ValueError(
            "imageio-ffmpeg is not installed; pip install imageio-ffmpeg "
            "or see https://ffmpeg.org/download.html for a local ffmpeg."
        ) from exc
    return get_ffmpeg_exe()


def _probe_duration(data: bytes) -> float | None:
    exe = _ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-i", "pipe:0"],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    stderr = proc.stderr.decode(errors="replace")
    match = _DURATION_RE.search(stderr)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read(data: bytes, mime: str) -> dict:
    """Read structural metadata without any LLM call.

    Args:
        data: Raw file bytes.
        mime: Declared MIME type.

    Returns:
        Dict with width, height, format, duration_s, exif, sha256.

    Raises:
        ValueError: Empty or corrupt input, with the underlying message.
    """
    if not data:
        raise ValueError("meta.read received empty bytes.")
    sha256 = hashlib.sha256(data).hexdigest()
    kind = mime.split("/")[0] if "/" in mime else ""
    if kind == "image":
        try:
            from PIL import Image
        except ImportError as exc:
            raise ValueError("pillow is not installed; pip install pillow.") from exc
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                fmt = (img.format or "").lower()
                exif: dict[str, str] = {}
                try:
                    raw = img.getexif()
                    for tag_id, value in raw.items():
                        exif[str(tag_id)] = str(value)[:500]
                except Exception:
                    exif = {}
        except Exception as exc:
            raise ValueError(f"corrupt image: {exc}") from exc
        return {
            "width": width,
            "height": height,
            "format": fmt,
            "duration_s": None,
            "exif": exif,
            "sha256": sha256,
        }
    if kind in ("audio", "video"):
        try:
            duration_s = _probe_duration(data)
        except Exception as exc:
            raise ValueError(f"corrupt media: {exc}") from exc
        width: int | None = None
        height: int | None = None
        if kind == "video":
            # Light dimension probe via Pillow is image-only; keep None
            # rather than a second ffmpeg parse pass.
            pass
        return {
            "width": width,
            "height": height,
            "format": mime.split("/")[-1].lower(),
            "duration_s": duration_s,
            "exif": {},
            "sha256": sha256,
        }
    raise ValueError(f"unsupported MIME for meta.read: {mime}")
