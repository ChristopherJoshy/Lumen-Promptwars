"""Hardening tests: security headers, upload sniffing, rate limits, signal rows.

No network: spoof/rate-limit paths reject before the pipeline runs, and
signal-row tests monkeypatch the disk-cache lookup.
"""
from __future__ import annotations

import time

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from app.features.analysis import service
from app.features.ingestion import router as ingestion
from app.main import _security_headers, create_app

client = TestClient(create_app())


@pytest.fixture(autouse=True)
def _clean_limits():
    ingestion._reset_rate_limits()
    yield
    ingestion._reset_rate_limits()


def test_security_headers_helper():
    resp = _security_headers(Response(content=b"ok"))
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"


def test_security_headers_on_routes():
    for path in ("/health", "/api/v1/analysis/status"):
        resp = client.get(path)
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["x-frame-options"] == "SAMEORIGIN"


@pytest.mark.parametrize(
    ("blob", "kind"),
    [
        (b"\xff\xd8\xff" + b"\x00" * 16, "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
        (b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 4, "image/webp"),
        (b"ID3\x04\x00\x00\x00\x00", "audio/mpeg"),
        (b"\xff\xfb\x90\x00" + b"\x00" * 16, "audio/mpeg"),
        (b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 4, "audio/wav"),
        (b"OggS\x00\x02\x00\x00", "audio/ogg"),
        (b"\x00\x00\x00\x18ftypisom" + b"\x00" * 4, "video/mp4"),
        (b"\x1a\x45\xdf\xa3" + b"\x00" * 16, "video/webm"),
        (b"hello world, not media", None),
    ],
)
def test_sniff_kind(blob, kind):
    assert ingestion._sniff_kind(blob) == kind


def test_spoofed_content_type_rejected():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    resp = client.post(
        "/api/v1/ingestion/upload", content=png, headers={"Content-Type": "audio/mpeg"}
    )
    assert resp.status_code == 415


def test_matching_family_passes_sniff_gate():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    # Sniff gate passes (same family); the pipeline then fails loudly on
    # junk bytes — either 422 (AnalysisError) or an upload-level error, but
    # never 415.
    resp = client.post(
        "/api/v1/ingestion/upload", content=png, headers={"Content-Type": "image/png"}
    )
    assert resp.status_code != 415


def test_rate_limit_trips_on_21st_call():
    ip = "198.51.100.7"
    for _ in range(20):
        assert ingestion._rate_limited(ip) is None
    retry = ingestion._rate_limited(ip)
    assert retry is not None and retry > 0


def test_rate_limit_window_slides(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    ip = "203.0.113.9"
    for _ in range(20):
        assert ingestion._rate_limited(ip) is None
    assert ingestion._rate_limited(ip) is not None
    now[0] += 61.0  # window slides past every recorded hit
    assert ingestion._rate_limited(ip) is None


def test_rate_limit_http_429_with_retry_after():
    ingestion._hits["testclient"] = [time.monotonic()] * 20
    resp = client.post("/api/v1/ingestion/link", json={"url": "https://example.com/x"})
    assert resp.status_code == 429
    assert "retry-after" in {k.lower() for k in resp.headers}


def _case(signals: dict) -> dict:
    return {"signals": signals}


def test_signal_rows_provenance_debate_audio_tools(monkeypatch):
    signals = {
        "perceptual": {
            "artifact_score": 0.1,
            "observations": ["flat prosody"],
            "audio_tools": {"clip": 0.2, "gaps": 1, "dr": 8.5},
        },
        "provenance": {"generator": "midjourney", "markers": ["m1", "m2"], "c2pa": False},
        "debate": {"agreed": False, "counter_reasons": ["old-but-real"]},
    }
    monkeypatch.setattr(service, "get_case", lambda _cid: _case(signals))
    rows = service.list_signals("x" * 64)
    assert rows is not None
    by_name = {r["name"]: r["finding"] for r in rows}
    assert "midjourney" in by_name["provenance"]
    assert "2 markers" in by_name["provenance"]
    assert "c2pa False" in by_name["provenance"]
    assert "clip 0.2" in by_name["audio_tools"]
    assert "gaps 1" in by_name["audio_tools"]
    assert "dr 8.5" in by_name["audio_tools"]
    assert "old-but-real" in by_name["debate"]
    for row in rows:
        assert set(row) == {"name", "finding"}


def test_signal_rows_absent_when_missing(monkeypatch):
    monkeypatch.setattr(service, "get_case", lambda _cid: _case({}))
    assert service.list_signals("x" * 64) == []


def test_signal_rows_debate_agreed_and_skipped(monkeypatch):
    monkeypatch.setattr(
        service, "get_case", lambda _cid: _case({"debate": {"agreed": True}})
    )
    rows = service.list_signals("x" * 64)
    assert rows is not None and "agreed" in rows[0]["finding"]
    monkeypatch.setattr(
        service,
        "get_case",
        lambda _cid: _case({"debate": {"agreed": None, "note": "debate skipped: boom"}}),
    )
    rows = service.list_signals("x" * 64)
    assert rows is not None and "skipped" in rows[0]["finding"]
