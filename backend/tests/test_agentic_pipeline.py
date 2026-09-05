"""Agentic pipeline tests: no network, monkeypatched transport."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.features.analysis.agents import muse_client, searcher
from app.features.analysis.agents import pipeline as agentic
from app.features.analysis.agents import temporal
from app.features.ingestion.platform_detect import detect_platform
from app.features.whatsapp_bot.messages import DISCLAIMER, format_failure, format_verdict


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    response: _FakeResponse | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        assert _FakeClient.response is not None
        return _FakeClient.response


def _run(coro):
    return asyncio.run(coro)


def test_respond_parses_fenced_multi_item(monkeypatch):
    payload = {
        "output": [
            {"type": "reasoning", "status": "completed"},
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": '```json\n{"verdict": "ok", "n": 1}\n```'}
                ],
            },
        ]
    }
    _FakeClient.response = _FakeResponse(200, payload)
    monkeypatch.setattr(muse_client.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(muse_client.settings, "opencode_zen_api_key", "test-key")
    result = _run(muse_client.respond("sys", [{"type": "input_text", "text": "hi"}]))
    assert result == {"verdict": "ok", "n": 1}


def test_respond_raises_on_non_json(monkeypatch):
    payload = {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "not json at all"}],
            }
        ]
    }
    _FakeClient.response = _FakeResponse(200, payload)
    monkeypatch.setattr(muse_client.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(muse_client.settings, "opencode_zen_api_key", "test-key")
    with pytest.raises(muse_client.MuseError):
        _run(muse_client.respond("sys", [{"type": "input_text", "text": "hi"}]))


def test_india_hit_labeling(monkeypatch):
    async def fake_exa(query: str):
        return [
            {"title": "Alt News debunks viral clip", "url": "https://altnews.in/xyz", "snippet": "s"},
            {"title": "Random blog", "url": "https://example.com/a", "snippet": "s"},
        ]

    def fake_ddg(query: str):
        return [{"title": "BOOM fact check", "href": "https://boomlive.in/fact", "body": "b"}]

    monkeypatch.setattr(searcher, "_exa_search", fake_exa)
    monkeypatch.setattr(searcher, "_ddg_text", fake_ddg)
    result = _run(searcher.search("viral clip", ["clip"], ""))
    urls = {h["url"] for h in result["india_hits"]}
    assert "https://altnews.in/xyz" in urls
    assert "https://boomlive.in/fact" in urls
    assert "https://example.com/a" not in urls


def test_temporal_override_turns_verified_into_contradiction():
    fused = {"verdict": "verified", "confidence": 0.9, "explanation": "e", "reasons": ["r"]}
    out = agentic._apply_temporal_override(fused, {"flag": True, "note": "seen earlier"})
    assert out["verdict"] == "contradiction_detected"
    assert any("Temporal" in r for r in out["reasons"])


def test_format_verdict_consumes_pipeline_shaped_dict():
    shaped = {
        "verdict": "likely_synthetic",
        "confidence": 0.82,
        "explanation": "Hands blur into extra fingers. Lighting mismatches the background.",
        "reasons": ["extra fingers", "lighting mismatch"],
        "signals": {},
        "model_version": "m@agentic-v1",
        "evidence": {"sha256": "abc", "caption": "c"},
        "cached": False,
    }
    reason = shaped["explanation"].split(". ")[0] + "."
    text = format_verdict(shaped["verdict"], reason, "https://x/r/1")
    assert "Likely synthetic" in text.split("\n\n")[0]
    assert "https://x/r/1" in text
    assert text.endswith(DISCLAIMER)


def test_format_failure_contains_no_verdict_label():
    text = format_failure()
    for label in ("Verified —", "Likely synthetic —", "Contradiction detected —"):
        assert label not in text
    assert "RETRY" in text


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://youtu.be/abc123", "youtube"),
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://www.instagram.com/p/xyz/", "instagram"),
        ("https://vm.tiktok.com/abc/", "tiktok"),
        ("https://x.com/user/status/1", "x"),
        ("https://twitter.com/user/status/1", "x"),
        ("https://www.facebook.com/watch/?v=1", "facebook"),
        ("https://t.me/channel/123", "telegram"),
        ("https://example.com/page", "generic"),
    ],
)
def test_platform_matrix(url, expected):
    assert detect_platform(url) == expected


def test_link_unresolved_cap_never_verified(monkeypatch):
    async def fake_resolve(url: str):
        return {
            "kind": "unresolved",
            "data": None,
            "mime": None,
            "metadata": {
                "uploader": "",
                "upload_date": None,
                "title": "viral clip",
                "description": "forward",
                "platform": "instagram",
            },
            "note": "instagram extraction failed; upload the file directly instead.",
        }

    async def fake_search(caption, entities, ocr_text):
        return {"exa_hits": [], "ddg_hits": [], "india_hits": [], "warnings": []}

    async def fake_fuse(signals, source):
        return {
            "verdict": "verified",
            "confidence": 0.99,
            "explanation": "Looks fine.",
            "reasons": ["looks fine"],
        }

    async def fake_review(proposal, signals, source):
        return {"agree": True, "counter_reasons": [], "suggested_verdict": proposal["verdict"]}

    monkeypatch.setattr(agentic.links, "resolve", fake_resolve)
    monkeypatch.setattr(agentic.searcher, "search", fake_search)
    monkeypatch.setattr(agentic.judge, "fuse", fake_fuse)
    monkeypatch.setattr("app.features.analysis.agents.critic.review", fake_review)
    result = _run(agentic.analyze_link("https://www.instagram.com/p/xyz/", source="upload"))
    assert result["verdict"] != "verified"
    assert result["verdict"] == "insufficient_evidence"


def test_whatsapp_routing_matrix(monkeypatch):
    from app.features.whatsapp_bot import tasks as wa_tasks

    calls: list[str] = []

    async def fake_download(url: str):
        return b"bytes"

    async def fake_image(data, *, mime, source):
        calls.append(f"image:{source}")
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Clean pixels here.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
        }

    async def fake_video(data, *, mime, source):
        calls.append(f"video:{source}")
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Clean frames here.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
        }

    async def fake_audio(data, *, mime, source):
        calls.append(f"audio:{source}")
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Natural speech here.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
        }

    async def fake_link(url, *, source):
        calls.append(f"link:{source}")
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Matches source here.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
        }

    async def fake_send(to, text, report_url):
        calls.append("send")

    monkeypatch.setattr("app.features.whatsapp_bot.media.download", fake_download)
    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_image", fake_image)
    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_video", fake_video)
    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_audio", fake_audio)
    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_link", fake_link)
    monkeypatch.setattr("app.features.whatsapp_bot.client.send_verdict", fake_send)

    base = {"From": "whatsapp:+911234567890", "NumMedia": "1", "MediaUrl0": "https://x/f"}
    _run(wa_tasks.handle_inbound({**base, "MediaContentType0": "image/jpeg", "Body": ""}))
    _run(wa_tasks.handle_inbound({**base, "MediaContentType0": "video/mp4", "Body": ""}))
    _run(wa_tasks.handle_inbound({**base, "MediaContentType0": "audio/ogg", "Body": ""}))
    _run(
        wa_tasks.handle_inbound(
            {"From": "whatsapp:+911234567890", "Body": "https://youtu.be/abc", "NumMedia": "0"}
        )
    )
    text = _run(
        wa_tasks.handle_inbound(
            {"From": "whatsapp:+911234567890", "Body": "hello", "NumMedia": "0"}
        )
    )
    assert "image:whatsapp" in calls
    assert "video:whatsapp" in calls
    assert "audio:whatsapp" in calls
    assert "link:whatsapp" in calls
    assert "Send a photo" in text


def test_temporal_check_no_dates():
    out = temporal.check({}, [], None)
    assert out["flag"] is False
    assert out["earliest_seen"] is None


def test_whatsapp_conversation_remembers_and_answers(monkeypatch):
    from app.features.whatsapp_bot import tasks as wa_tasks

    async def fake_link(url, *, source):
        return {
            "verdict": "verified",
            "confidence": 0.9,
            "explanation": "Clean pixels here.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
            "case_id": "c" * 64,
        }

    async def fake_answer(case_id, question):
        assert case_id == "c" * 64
        return f"answered: {question}"

    async def fake_send(to, text, report_url):
        assert f"/report/{'c' * 64}" in text or "answered" in text

    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_link", fake_link)
    monkeypatch.setattr("app.features.analysis.service.answer_question", fake_answer)
    monkeypatch.setattr("app.features.whatsapp_bot.client.send_verdict", fake_send)
    wa_tasks._LAST_CASE.clear()
    sender = {"From": "whatsapp:+911234567890", "Body": "https://youtu.be/abc", "NumMedia": "0"}
    _run(wa_tasks.handle_inbound(sender))
    assert wa_tasks._LAST_CASE.get("whatsapp:+911234567890") == "c" * 64
    follow = _run(
        wa_tasks.handle_inbound(
            {"From": "whatsapp:+911234567890", "Body": "why?", "NumMedia": "0"}
        )
    )
    assert follow.startswith("answered: why?")
    retry = _run(
        wa_tasks.handle_inbound(
            {"From": "whatsapp:+911234567890", "Body": "RETRY", "NumMedia": "0"}
        )
    )
    assert "expired" in retry
    import json as _json
    from pathlib import Path as _Path

    cache_file = _Path("storage/agentic_cache") / ("c" * 64 + ".json")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        _json.dumps({"result": {"verdict": "verified", "explanation": "Clean.", "reasons": []}})
    )
    try:
        replay = _run(
            wa_tasks.handle_inbound(
                {"From": "whatsapp:+911234567890", "Body": "RETRY", "NumMedia": "0"}
            )
        )
    finally:
        cache_file.unlink(missing_ok=True)
    assert "Verified" in replay


def test_whatsapp_image_flow_ack_then_summary_link(monkeypatch):
    from app.features.whatsapp_bot import tasks as wa_tasks

    sent: list[str] = []

    async def fake_download(url):
        return b"bytes"

    async def fake_image(data, *, mime, source, claimed_date=None):
        return {
            "verdict": "likely_synthetic",
            "confidence": 0.8,
            "explanation": "AI texture here. Second sentence.",
            "reasons": ["r"],
            "signals": {},
            "model_version": "m@agentic-v1",
            "evidence": {"sha256": "aabbccddeeff0011", "caption": "c"},
            "cached": False,
            "case_id": "d" * 64,
        }

    async def fake_send(to, text, report_url):
        sent.append(text)

    monkeypatch.setattr("app.features.whatsapp_bot.media.download", fake_download)
    monkeypatch.setattr("app.features.analysis.agents.pipeline.analyze_image", fake_image)
    monkeypatch.setattr("app.features.whatsapp_bot.client.send_verdict", fake_send)
    wa_tasks._LAST_CASE.clear()
    out = _run(
        wa_tasks.handle_inbound(
            {
                "From": "whatsapp:+911234567890",
                "NumMedia": "1",
                "MediaUrl0": "https://x/f",
                "MediaContentType0": "image/jpeg",
                "Body": "",
            }
        )
    )
    assert len(sent) == 2
    assert "40 seconds" in sent[0]
    assert "Likely synthetic" in sent[1]
    assert f"/report/{'d' * 64}" in sent[1]
    assert out == sent[1]
