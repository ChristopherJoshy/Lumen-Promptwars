"""Provenance wiring: synthid.scan markers + run_fusion signals['provenance']."""

from __future__ import annotations

import asyncio
import io
import struct

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.features.analysis.agents import synthid
from app.features.analysis.agents import pipeline as agentic


def _run(coro):
    return asyncio.run(coro)


def _png_with_generator_text() -> bytes:
    img = Image.new("RGB", (64, 64), (10, 200, 90))
    info = PngInfo()
    info.add_text("parameters", "prompt here Steps: 30, Stable Diffusion v1.5")
    buf = io.BytesIO()
    img.save(buf, "PNG", pnginfo=info)
    return buf.getvalue()


def _jpeg_with_software_tag() -> bytes:
    img = Image.new("RGB", (64, 64), (200, 40, 40))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    raw = buf.getvalue()
    # JPEG COM segment carrying the file's software tag.
    comment = b"Software: Midjourney v6 test fixture"
    seg = b"\xff\xfe" + struct.pack(">H", len(comment) + 2) + comment
    assert raw[:2] == b"\xff\xd8"
    return raw[:2] + seg + raw[2:]


def test_scan_finds_png_text_generator_marker():
    out = synthid.scan(_png_with_generator_text())
    assert out["generator"] == "stable diffusion"
    assert any("stable diffusion" in m for m in out["markers"])


def test_scan_finds_jpeg_software_tag():
    out = synthid.scan(_jpeg_with_software_tag())
    assert out["generator"] == "midjourney"
    assert any("midjourney" in m for m in out["markers"])


def _fusion_kwargs(**overrides):
    kwargs = {
        "modality": "image",
        "perceptual": {"artifact_score": 0.1},
        "meta_info": {"sha256": "abc"},
        "search_result": {"exa_hits": [], "ddg_hits": [], "india_hits": []},
        "claimed_date": None,
        "source": "upload",
        "caption": "lamp",
    }
    kwargs.update(overrides)
    return kwargs


def _mock_fuse_and_critic(monkeypatch, seen: dict):
    from app.features.analysis.agents import critic

    async def fake_fuse(signals, source):
        seen.update(signals)
        return {"verdict": "verified", "confidence": 0.9, "explanation": "e", "reasons": ["r"]}

    async def fake_review(proposal, signals, source):
        return {"agree": True, "counter_reasons": [], "suggested_verdict": proposal["verdict"]}

    monkeypatch.setattr(agentic.judge, "fuse", fake_fuse)
    monkeypatch.setattr(critic, "review", fake_review)


def test_run_fusion_includes_provenance_signal(monkeypatch):
    seen: dict = {}
    _mock_fuse_and_critic(monkeypatch, seen)
    prov = {"generator": "midjourney", "markers": ["generator tag: ...midjourney..."], "c2pa": False}
    out = _run(agentic.run_fusion(**_fusion_kwargs(provenance_result=prov)))
    assert out["signals"]["provenance"] == prov
    assert seen["provenance"] == prov


def test_run_fusion_omits_provenance_when_absent(monkeypatch):
    seen: dict = {}
    _mock_fuse_and_critic(monkeypatch, seen)
    out = _run(agentic.run_fusion(**_fusion_kwargs()))
    assert "provenance" not in out["signals"]
    assert "provenance" not in seen
