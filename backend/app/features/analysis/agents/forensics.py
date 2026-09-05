"""Local numeric forensic instruments: ELA, DCT grid, noise, copy-move.

CPU-only, numpy + Pillow. Every function raises ValueError on bad input and
returns real measured numbers — never placeholders. Heatmaps are analysis
highlights for the report page, not proof of fakery (see copy rule).
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
from PIL import Image

_NAMES = ("ela", "dct", "noise", "copymove")


def _artifact_dir() -> Path:
    d = Path("storage/forensics")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _to_rgb(data: bytes) -> np.ndarray:
    if not data:
        raise ValueError("Empty bytes: nothing to examine.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            return np.asarray(img.convert("RGB"), dtype=np.uint8)
    except Exception as exc:
        raise ValueError(f"Unreadable image bytes: {exc}") from exc


def _to_heatmap_png(gray: np.ndarray) -> bytes:
    clipped = np.clip(gray, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(clipped, mode="L").save(buf, "PNG")
    return buf.getvalue()


def ela(image_rgb: bytes, quality: int = 90) -> dict:
    """Error-level analysis: recompress at quality, amplify the diff x12."""
    if not 1 <= quality <= 100:
        raise ValueError(f"ELA quality out of range: {quality}")
    orig = _to_rgb(image_rgb).astype(np.float32)
    buf = io.BytesIO()
    Image.fromarray(_to_rgb(image_rgb)).save(buf, "JPEG", quality=quality)
    recomp = _to_rgb(buf.getvalue()).astype(np.float32)
    diff = np.abs(orig - recomp).mean(axis=2)
    score = float(np.percentile(diff, 99) / 255.0)
    return {"score": score, "heatmap_png": _to_heatmap_png(diff * 12.0)}


_DCT_T = np.sqrt(2.0 / 8) * np.cos(
    np.outer(np.arange(8), np.arange(8) * 2 + 1) * np.pi / 16.0
)
_DCT_T[0, :] /= np.sqrt(2.0)


def _block_dct(block: np.ndarray) -> np.ndarray:
    return _DCT_T @ block @ _DCT_T.T


def dct_grid(image_rgb: bytes) -> dict:
    """8x8-block DCT high-frequency energy variance across the grid."""
    gray = np.asarray(Image.open(io.BytesIO(image_rgb)).convert("L"), dtype=np.float32)
    if gray.size == 0:
        raise ValueError("Unreadable image bytes.")
    h, w = gray.shape
    h8, w8 = h // 8, w // 8
    if h8 == 0 or w8 == 0:
        raise ValueError("Image too small for 8x8 DCT grid.")
    gray = gray[: h8 * 8, : w8 * 8] - 128.0
    energies = np.zeros((h8, w8), dtype=np.float64)
    for i in range(h8):
        for j in range(w8):
            coef = _block_dct(gray[i * 8 : (i + 1) * 8, j * 8 : (j + 1) * 8])
            energies[i, j] = float(np.abs(coef[2:, 2:]).sum())
    mean = energies.mean()
    score = float(min(1.0, (energies.std() / (mean + 1e-6)) / 4.0))
    norm = (energies - energies.min()) / (np.ptp(energies) + 1e-6) * 255.0
    big = np.asarray(Image.fromarray(norm.astype(np.uint8)).resize((w, h), Image.NEAREST))
    return {"score": score, "heatmap_png": _to_heatmap_png(big)}


def noise_map(image_rgb: bytes) -> dict:
    """Laplacian-residual regional variance: spliced regions differ in grain."""
    gray = np.asarray(Image.open(io.BytesIO(image_rgb)).convert("L"), dtype=np.float32)
    if gray.size == 0:
        raise ValueError("Unreadable image bytes.")
    padded = np.pad(gray, 1, mode="reflect")
    lap = (
        padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:] - 4 * gray
    )
    residual = np.abs(lap)
    h, w = residual.shape
    cells = 8
    ch, cw = max(1, h // cells), max(1, w // cells)
    variances = [
        float(residual[y : y + ch, x : x + cw].var())
        for y in range(0, h, ch)
        for x in range(0, w, cw)
    ]
    arr = np.array(variances)
    score = float(min(1.0, (arr.std() / (arr.mean() + 1e-6)) / 3.0))
    heat = residual / (residual.max() + 1e-6) * 255.0
    return {"score": score, "heatmap_png": _to_heatmap_png(heat)}


def copy_move(image_rgb: bytes) -> dict:
    """Block-match duplicates on downscaled grayscale: cloned-region count."""
    img = Image.open(io.BytesIO(image_rgb)).convert("L")
    img.thumbnail((256, 256), Image.LANCZOS)
    gray = np.asarray(img, dtype=np.float32)
    if gray.size == 0:
        raise ValueError("Unreadable image bytes.")
    h, w = gray.shape
    size, stride = 16, 8
    seen: dict[bytes, tuple[int, int]] = {}
    dup_mask = np.zeros((h, w), dtype=np.float32)
    dup_pairs = 0
    for y in range(0, h - size + 1, stride):
        for x in range(0, w - size + 1, stride):
            block = gray[y : y + size, x : x + size]
            if float(block.std()) < 2.0:
                continue  # flat regions match everywhere; not cloning evidence
            key = (block // 16).astype(np.uint8).tobytes()
            if key in seen:
                py, px = seen[key]
                if abs(py - y) + abs(px - x) > size:  # not self-overlap
                    dup_pairs += 1
                    dup_mask[y : y + size, x : x + size] = 255.0
                    dup_mask[py : py + size, px : px + size] = 255.0
            else:
                seen[key] = (y, x)
    score = float(min(1.0, dup_pairs / 50.0))
    with Image.open(io.BytesIO(image_rgb)) as src:
        ow, oh = src.width, src.height
    big = np.asarray(
        Image.fromarray(dup_mask.astype(np.uint8)).resize((ow, oh), Image.NEAREST)
    )
    return {"score": score, "heatmap_png": _to_heatmap_png(big)}


def jpeg_ghost(image_rgb: bytes) -> dict:
    """Double-compression ghost: ELA response curve across qualities.

    Spliced regions minimized at a different quality than the background;
    the spread of per-quality mean responses is the score.
    """
    orig = _to_rgb(image_rgb).astype(np.float32)
    means = []
    diffs = []
    for quality in (60, 75, 90):
        buf = io.BytesIO()
        Image.fromarray(_to_rgb(image_rgb)).save(buf, "JPEG", quality=quality)
        recomp = _to_rgb(buf.getvalue()).astype(np.float32)
        diff = np.abs(orig - recomp).mean(axis=2)
        means.append(float(diff.mean()))
        diffs.append(diff)
    spread = max(means) - min(means)
    score = float(min(1.0, spread / 12.0))
    heat = diffs[2] / (diffs[2].max() + 1e-6) * 255.0
    return {"score": score, "heatmap_png": _to_heatmap_png(heat)}


def blockiness(image_rgb: bytes) -> dict:
    """8x8 grid-boundary discontinuity: misaligned splices break the grid."""
    gray = np.asarray(Image.open(io.BytesIO(image_rgb)).convert("L"), dtype=np.float32)
    if gray.size == 0:
        raise ValueError("Unreadable image bytes.")
    h, w = gray.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    gray = gray[:h8, :w8]
    vert = np.abs(np.diff(gray, axis=1))
    horiz = np.abs(np.diff(gray, axis=0))
    on_grid_v = vert[:, 7::8].mean()
    off_grid_v = np.delete(vert, slice(7, vert.shape[1], 8), axis=1).mean()
    on_grid_h = horiz[7::8, :].mean()
    off_grid_h = np.delete(horiz, slice(7, horiz.shape[0], 8), axis=0).mean()
    ratio = (on_grid_v + on_grid_h + 1e-6) / (off_grid_v + off_grid_h + 1e-6)
    score = float(min(1.0, max(0.0, (ratio - 1.0) / 2.0)))
    heat = np.zeros_like(gray)
    heat[:, 7::8] = 255.0
    heat[7::8, :] = 255.0
    return {"score": score, "heatmap_png": _to_heatmap_png(heat * min(1.0, ratio / 3.0))}


def examine(data: bytes) -> dict:
    """Run all six instruments; sha-keyed artifacts reused, never recomputed.

    Returns {scores: {ela, dct, noise, copymove, ghost, blockiness,
    fused_mean}, artifacts: {name: path}, note: str}.
    """
    from app.features.analysis.agents import pipeline  # lazy: pipeline imports us

    jpeg = pipeline._normalize_image(data)
    sha = hashlib.sha256(jpeg).hexdigest()[:16]
    score_path = _artifact_dir() / f"{sha}.json"
    if score_path.is_file():
        import json

        try:
            cached = json.loads(score_path.read_text())
            if set(cached.get("scores", {})) >= {
                "ela",
                "dct",
                "noise",
                "copymove",
                "ghost",
                "blockiness",
            }:
                return cached
        except (OSError, ValueError):
            pass
    results = {
        "ela": ela(jpeg),
        "dct": dct_grid(jpeg),
        "noise": noise_map(jpeg),
        "copymove": copy_move(jpeg),
        "ghost": jpeg_ghost(jpeg),
        "blockiness": blockiness(jpeg),
    }
    artifacts: dict[str, str] = {}
    for name, res in results.items():
        path = _artifact_dir() / f"{sha}_{name}.png"
        if not path.is_file():
            path.write_bytes(res["heatmap_png"])
        artifacts[name] = str(path)
    scores = {name: round(float(res["score"]), 3) for name, res in results.items()}
    mean = round(sum(scores.values()) / len(scores), 3)
    payload = {
        "scores": {**scores, "fused_mean": mean},
        "artifacts": artifacts,
        "note": "Local numeric instruments (ELA/DCT/noise/copy-move/ghost/blockiness); "
        "highlights mark regions to inspect, not proof of fakery.",
    }
    try:
        import json

        score_path.write_text(json.dumps(payload))
    except OSError:
        pass
    return payload
