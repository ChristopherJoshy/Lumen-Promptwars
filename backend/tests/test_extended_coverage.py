"""Extended coverage: forensics, packs, Sarvam, graph memory, routes, near-dup."""

from __future__ import annotations

import asyncio
import io

import numpy as np
import pytest
from PIL import Image

def _run(coro):
    return asyncio.run(coro)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

from app.features.analysis import service as analysis_service
from app.features.analysis.agents import audio as audio_agent
from app.features.analysis.agents import forensics, near_dup, prompt_pack, sarvam
from app.features.analysis.agents import pipeline as agentic
from app.features.analysis.agents import visual as visual_agent
from app.features.analysis.agents.graph import run_case


def _png(color=(30, 120, 200), size=(128, 128)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _noisy_png(seed: int = 7, size=(160, 160)) -> bytes:
    buf = io.BytesIO()
    Image.effect_noise(size, 64).convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def test_ela_clean_image_scores_low():
    out = forensics.ela(_png())
    assert out["score"] < 0.2
    assert out["heatmap_png"][:8] == b"\x89PNG\r\n\x1a\n"


def test_copy_move_clone_scores_above_plain():
    from PIL import Image as PILImage

    base = PILImage.effect_noise((160, 160), 64).convert("RGB")
    clone = base.copy()
    region = base.crop((16, 16, 80, 80))
    clone.paste(region, (80, 80))
    plain_buf, clone_buf = io.BytesIO(), io.BytesIO()
    base.save(plain_buf, "PNG")
    clone.save(clone_buf, "PNG")
    plain = forensics.copy_move(plain_buf.getvalue())["score"]
    duped = forensics.copy_move(clone_buf.getvalue())["score"]
    assert duped > plain


def test_prompt_pack_budget_and_missing():
    text = prompt_pack.load("ai_image_tells", budget_chars=200)
    assert len(text) <= 230  # budget + truncation marker
    with pytest.raises(FileNotFoundError):
        prompt_pack.load("no_such_pack")


class _QueueClient:
    responses: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        payload = _QueueClient.responses.pop(0)
        return _FakeResponse(200, payload)


def test_sarvam_transcribe_and_translate(monkeypatch):
    _QueueClient.responses = [
        {"transcript": "namaste", "language_code": "hi-IN"},
        {"transcript": "hello", "language_code": "en-IN"},
    ]
    monkeypatch.setattr(sarvam.httpx, "AsyncClient", _QueueClient)
    monkeypatch.setattr(sarvam.settings, "sarvam_api_key", "k")
    out = _run(sarvam.transcribe(b"audio", filename="a.mp3"))
    assert out == {"transcript": "namaste", "detected_language": "hi-IN", "translated_en": "hello"}


def test_examine_fresh_run_six_scores(monkeypatch, tmp_path):
    monkeypatch.setattr(forensics, "_artifact_dir", lambda: tmp_path)
    out = forensics.examine(_png())
    assert set(out["scores"]) == {"ela", "dct", "noise", "copymove", "ghost", "blockiness", "spectrum", "fused_mean"}
    assert set(out["artifacts"]) == {"ela", "dct", "noise", "copymove", "ghost", "blockiness", "spectrum"}
    out2 = forensics.examine(_png())
    assert out2["scores"] == out["scores"]

def test_spectrum_flags_peaky_synthetic():
    from PIL import Image as PILImage

    grid = (np.indices((128, 128)).sum(axis=0) % 2 * 255).astype("uint8")
    grid = np.stack([grid] * 3, axis=2)
    grid_buf = io.BytesIO()
    PILImage.fromarray(grid).save(grid_buf, "PNG")
    assert forensics.spectrum(grid_buf.getvalue())["score"] > 0.5
    assert forensics.spectrum(_png())["score"] < 0.5

def test_visual_injects_instrument_readings(monkeypatch):
    seen: dict = {}

    async def fake_respond(system, parts, **kwargs):
        seen["text"] = parts[0]["text"]
        return {
            "observations": ["o"],
            "artifact_score": 0.1,
            "caption": "c",
            "entities": [],
            "ocr_text": "",
        }

    monkeypatch.setattr(visual_agent.muse_client, "respond", fake_respond)
    out = _run(visual_agent.analyze(_png(), tool_data={"scores": {"ela": 0.9, "fused_mean": 0.8}}))
    assert "ela=0.9" in seen["text"]
    assert out["artifact_score"] == 0.1


def test_audio_coerces_sarvam_language(monkeypatch):
    async def fake_respond(system, parts, **kwargs):
        return {
            "observations": ["o"],
            "artifact_score": 0.2,
            "transcript_hint": "model guess",
            "language_guess": "hindi",
            "entities": [],
        }

    monkeypatch.setattr(audio_agent.muse_client, "respond", fake_respond)
    hint = {"transcript": "vanakkam", "detected_language": "ta-IN", "translated_en": ""}
    out = _run(audio_agent.analyze(b"audio", "audio/wav", sarvam_hint=hint))
    assert out["language_guess"] == "ta-IN"
    assert out["transcript_hint"] == "vanakkam"


def _mock_graph(monkeypatch):
    async def fake_visual(jpeg, tool_data=None, provenance=None):
        return {
            "observations": ["clean"],
            "artifact_score": 0.1,
            "caption": "a lamp",
            "entities": ["lamp"],
            "ocr_text": "",
        }

    async def fake_search(*, caption, entities, ocr_text):
        return {"exa_hits": [], "ddg_hits": [], "india_hits": [], "warnings": []}

    async def fake_fusion(**kwargs):
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Clean.",
            "reasons": ["r"],
            "signals": kwargs,
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "abc", "caption": "a lamp"},
            "cached": False,
        }

    monkeypatch.setattr(forensics, "examine", lambda data: {"scores": {"fused_mean": 0.05}, "artifacts": {}, "note": "n"})
    monkeypatch.setattr(visual_agent, "analyze", fake_visual)
    monkeypatch.setattr(agentic, "run_search", fake_search)
    monkeypatch.setattr(agentic, "run_fusion", fake_fusion)


def test_graph_persists_thread_state(monkeypatch, tmp_path):
    from app.features.analysis.agents import graph as graph_mod
    from app.features.analysis.agents import meta as meta_mod

    monkeypatch.setattr(graph_mod, "_memory_path", lambda: tmp_path / "g.sqlite")
    monkeypatch.setattr(meta_mod, "read", lambda data, mime: {"sha256": "abc"})
    _mock_graph(monkeypatch)
    thread = "test-thread-1"
    out = _run(
        run_case(modality="image", data=_png(), mime="image/png", source="upload", claimed_date=None, thread_id=thread)
    )
    assert out["verdict"] == "verified"

    async def _read_state():
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "g.sqlite")) as saver:
            tup = await saver.aget_tuple({"configurable": {"thread_id": thread}})
            assert tup is not None
            return tup.checkpoint["channel_values"]["shaped"]["verdict"]

    assert _run(_read_state()) == "verified"


def test_report_service_404s():
    assert analysis_service.get_case("0" * 64) is None
    assert analysis_service.get_case("not-hex") is None
    assert analysis_service.list_signals("0" * 64) is None
    assert analysis_service.forensics_path("0" * 64, "ela") is None
    assert analysis_service.forensics_path("0" * 64, "bogus") is None


def test_near_dup_roundtrip_and_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr(near_dup, "_db_path", lambda: tmp_path / "n.sqlite")
    assert near_dup.lookup_image(_png()) is None
    near_dup.remember_image(_png(), "case-1", "image")
    assert near_dup.lookup_image(_png()) == "case-1"
    assert near_dup.lookup_transcript("short") is None
    long_text = "this is a long repeated voice note transcript for testing"
    assert near_dup.lookup_transcript(long_text) is None
    near_dup.remember_transcript(long_text, "case-2")
    assert near_dup.lookup_transcript(long_text.upper()) == "case-2"


def test_canonical_link_strips_trackers():
    url = agentic._canonical_link("https://X.com/a?utm_source=x&u=1&fbclid=z#frag")
    assert url == "https://x.com/a?u=1"


def test_usage_ledger_disabled_and_safe(monkeypatch):
    from app.db import usage

    monkeypatch.setattr(usage.settings, "mongo_url", "")
    monkeypatch.setattr(usage, "_client", None)
    assert _run(usage.log_case(case_id="x", modality="m", verdict="v", confidence=0.5, source="s")) is None
    assert _run(usage.usage_stats()) == {}

    class _Boom:
        def __getattr__(self, _):
            raise RuntimeError("down")

    monkeypatch.setattr(usage, "get_client", lambda: _Boom())
    assert _run(usage.log_case(case_id="x", modality="m", verdict="v", confidence=0.5, source="s")) is None
    assert _run(usage.usage_stats()) == {}


def test_reasoning_effort_low_by_default(monkeypatch):
    seen: dict = {}

    class _CapClient(_QueueClient):
        async def post(self, *args, **kwargs):
            seen.update(kwargs.get("json", {}))
            return _FakeResponse(200, {"output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}]})

    from app.features.analysis.agents import muse_client

    monkeypatch.setattr(muse_client.httpx, "AsyncClient", _CapClient)
    monkeypatch.setattr(muse_client.settings, "opencode_zen_api_key", "k")
    _run(muse_client.respond("Return JSON ONLY with exactly this key: {\"ok\": true}.", [{"type": "input_text", "text": "Reply with the JSON object and no other text."}]))
    assert seen.get("reasoning") == {"effort": "low"}
    assert seen.get("temperature") == 0


def _fusion_kwargs():
    return {
        "modality": "image",
        "perceptual": {"artifact_score": 0.1},
        "meta_info": {"sha256": "abc"},
        "search_result": {"exa_hits": [], "ddg_hits": [], "india_hits": []},
        "claimed_date": None,
        "source": "upload",
        "caption": "lamp",
    }


def _verdict(v):
    return {"verdict": v, "confidence": 0.9, "explanation": "e", "reasons": ["r"]}


def test_debate_agree_keeps_proposal(monkeypatch):
    from app.features.analysis.agents import critic

    async def fake_fuse(signals, source):
        return _verdict("verified")

    async def fake_review(proposal, signals, source):
        return {"agree": True, "counter_reasons": [], "suggested_verdict": proposal["verdict"]}

    monkeypatch.setattr(agentic.judge, "fuse", fake_fuse)
    monkeypatch.setattr(critic, "review", fake_review)
    out = _run(agentic.run_fusion(**_fusion_kwargs()))
    assert out["verdict"] == "verified"
    assert out["signals"]["debate"] == {"agreed": True, "counter_reasons": []}


def test_debate_disagree_judge_has_last_word(monkeypatch):
    from app.features.analysis.agents import critic

    calls: list = []

    async def fake_fuse(signals, source):
        calls.append("challenge" in signals)
        return _verdict("verified" if "challenge" not in signals else "insufficient_evidence")

    async def fake_review(proposal, signals, source):
        return {"agree": False, "counter_reasons": ["no dated hit"], "suggested_verdict": "insufficient_evidence"}

    monkeypatch.setattr(agentic.judge, "fuse", fake_fuse)
    monkeypatch.setattr(critic, "review", fake_review)
    out = _run(agentic.run_fusion(**_fusion_kwargs()))
    assert calls == [False, True]
    assert out["verdict"] == "insufficient_evidence"
    assert out["signals"]["debate"]["agreed"] is False
    assert any("Debate" in r for r in out["reasons"])


def test_debate_critic_failure_keeps_proposal(monkeypatch):
    from app.features.analysis.agents import critic
    from app.features.analysis.agents import muse_client

    async def fake_fuse(signals, source):
        return _verdict("verified")

    async def boom(proposal, signals, source):
        raise muse_client.MuseError("critic down")

    monkeypatch.setattr(agentic.judge, "fuse", fake_fuse)
    monkeypatch.setattr(critic, "review", boom)
    out = _run(agentic.run_fusion(**_fusion_kwargs()))
    assert out["verdict"] == "verified"
    assert "skipped" in out["signals"]["debate"]["note"]


def test_examine_fresh_run_six_scores(monkeypatch, tmp_path):
    monkeypatch.setattr(forensics, "_artifact_dir", lambda: tmp_path)
    out = forensics.examine(_png())
    assert set(out["scores"]) == {"ela", "dct", "noise", "copymove", "ghost", "blockiness", "fused_mean"}
    assert set(out["artifacts"]) == {"ela", "dct", "noise", "copymove", "ghost", "blockiness"}
    out2 = forensics.examine(_png())
    assert out2["scores"] == out["scores"]
