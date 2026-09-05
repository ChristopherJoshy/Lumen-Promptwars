"""Near-duplicate instant cache: dHash for pixels, transcripts for voice.

No neural embeddings — CLIP-style weights would break the <10 MB,
no-local-weights constraint. A 64-bit dHash (PIL + numpy, zero new deps)
catches WhatsApp re-encodes/resizes that defeat exact-sha caching; audio
re-encodes defeat byte hashes too, so voice notes match on the normalized
Sarvam transcript instead. Only hashes and verdict pointers are stored —
never bytes (retention rule).
"""

from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image

HAMMING_CUTOFF = 8


def _db_path() -> Path:
    path = Path("storage/memory/near_dup.sqlite")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    # dHash is hex text: a 64-bit digest can exceed SQLite's signed INTEGER.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS image_hashes "
        "(dhash TEXT PRIMARY KEY, case_id TEXT NOT NULL, kind TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS transcripts "
        "(text TEXT PRIMARY KEY, case_id TEXT NOT NULL)"
    )
    return conn


def dhash(image_bytes: bytes) -> int:
    """64-bit difference hash: 9x8 grayscale, bit = left pixel brighter."""
    if not image_bytes:
        raise ValueError("dhash received empty bytes.")
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            gray = np.asarray(img.convert("L").resize((9, 8), Image.LANCZOS), dtype=np.int16)
    except Exception as exc:
        raise ValueError(f"dhash unreadable image: {exc}") from exc
    bits = gray[:, :-1] > gray[:, 1:]
    out = 0
    for bit in bits.flatten():
        out = (out << 1) | int(bit)
    return out


def hamming(a: int, b: int) -> int:
    """Hamming distance between two dHashes (xor popcount)."""
    return bin(a ^ b).count("1")


def _hex(digest: int) -> str:
    return f"{digest:016x}"


def lookup_image(image_bytes: bytes) -> str | None:
    """Return the case_id of a near-duplicate analysis, if any."""
    try:
        digest = dhash(image_bytes)
    except ValueError:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT case_id FROM image_hashes WHERE dhash = ?", (_hex(digest),)
        ).fetchone()
        if row:
            return str(row[0])
        best: str | None = None
        best_dist = HAMMING_CUTOFF + 1
        for (stored, case_id) in conn.execute("SELECT dhash, case_id FROM image_hashes"):
            dist = hamming(digest, int(stored, 16))
            if dist < best_dist:
                best, best_dist = str(case_id), dist
        return best if best_dist <= HAMMING_CUTOFF else None


def remember_image(image_bytes: bytes, case_id: str, kind: str) -> None:
    """Store a dHash pointer after a full analysis (best-effort, never loud)."""
    try:
        digest = dhash(image_bytes)
    except ValueError:
        return
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO image_hashes (dhash, case_id, kind) VALUES (?, ?, ?)",
                (_hex(digest), case_id, kind),
            )
            conn.commit()
    except OSError:
        pass


def _normalize_transcript(text: str) -> str:
    return " ".join(text.lower().split())


def lookup_transcript(transcript: str) -> str | None:
    """Return the case_id of a voice note with the same normalized transcript."""
    norm = _normalize_transcript(transcript)
    if len(norm) < 20:
        return None  # too short to be identifying; never match on fragments
    with _connect() as conn:
        row = conn.execute(
            "SELECT case_id FROM transcripts WHERE text = ?", (norm,)
        ).fetchone()
    return str(row[0]) if row else None


def remember_transcript(transcript: str, case_id: str) -> None:
    """Store a transcript pointer after a full audio analysis (best-effort)."""
    norm = _normalize_transcript(transcript)
    if len(norm) < 20:
        return
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO transcripts (text, case_id) VALUES (?, ?)",
                (norm, case_id),
            )
            conn.commit()
    except OSError:
        pass
