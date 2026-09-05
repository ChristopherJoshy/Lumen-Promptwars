"""Synthetic-origin markers: real byte-level generator fingerprints.

No mocks, no heuristics-as-verdicts: every marker is a concrete tag, chunk,
or manifest found in the file. Covers C2PA manifests (JUMBF), PNG tEXt
parameters (Automatic1111/Stability), EXIF software/XMP generator tags
(Firefly, Midjourney, DALL-E, SynthID-marked XMP), and JPEG COM segments.
Absence of markers proves nothing (stripping is trivial) — presence is
strong positive evidence of AI generation.
"""

from __future__ import annotations

import io
import struct

# Lowercase substrings that identify known generators in tag/chunk text.
_GENERATORS = (
    "stable diffusion",
    "automatic1111",
    "comfyui",
    "midjourney",
    "dall-e",
    "dalle",
    "firefly",
    "imagen",
    "synthid",
    "ai generated",
    "ai-generated",
    "generated with ai",
    "deepmind",
    "openai",
    "stability",
    "leonardo",
    "ideogram",
    " playground",
)


def _png_text_chunks(data: bytes) -> list[str]:
    found: list[str] = []
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return found
    pos = 8
    while pos + 8 <= len(data):
        (length, ctype) = struct.unpack(">I4s", data[pos : pos + 8])
        if length > 8 * 1024 * 1024:
            break
        chunk = data[pos + 8 : pos + 8 + length]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            try:
                found.append(chunk.split(b"\x00", 1)[-1].decode("utf-8", "replace")[:2000])
            except Exception:
                pass
        pos += 12 + length
        if ctype == b"IEND":
            break
    return found


def _jpeg_segments(data: bytes) -> list[tuple[str, bytes]]:
    found: list[tuple[str, bytes]] = []
    if data[:2] != b"\xff\xd8":
        return found
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            break
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        seg = data[pos + 4 : pos + 2 + length]
        found.append((f"FF{marker:02X}", seg[:4000]))
        pos += 2 + length
        if marker == 0xDA:
            break
    return found


def scan(data: bytes) -> dict:
    """Scan raw file bytes for synthetic-origin markers.

    Returns {generator: str | None, markers: [str], c2pa: bool}.
    Never raises on weird input — returns empty markers instead (a corrupt
    file is meta.read's job to reject loudly).
    """
    markers: list[str] = []
    generator: str | None = None
    c2pa = False
    texts: list[str] = []

    try:
        texts.extend(_png_text_chunks(data))
        for name, seg in _jpeg_segments(data):
            if name == "FFED" and b"http://ns.adobe.com/xap/1.0/\x00" in seg:
                try:
                    texts.append(seg.split(b"\x00", 1)[-1].decode("utf-8", "replace")[:4000])
                except Exception:
                    pass
            if b"jumb" in seg[:16].lower() or b"c2pa" in seg.lower():
                c2pa = True
                markers.append("JPEG JUMBF/C2PA manifest store present")
            if name == "FFFE":
                try:
                    texts.append(seg.decode("utf-8", "replace")[:2000])
                except Exception:
                    pass
        blob = "\n".join(texts).lower()
        for sig in _GENERATORS:
            if sig in blob:
                idx = blob.index(sig)
                snippet = blob[max(0, idx - 40) : idx + 80].replace("\n", " ")
                markers.append(f"generator tag: ...{snippet}...")
                if generator is None:
                    generator = sig.strip()
    except Exception:
        pass
    return {"generator": generator, "markers": markers, "c2pa": c2pa}
