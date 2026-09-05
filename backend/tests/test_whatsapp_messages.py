"""Verdict-message design tests: structure a forwarder can act on."""
from app.features.whatsapp_bot.messages import DISCLAIMER, format_verdict


def test_first_line_carries_verdict_and_reason():
    text = format_verdict("likely_synthetic", "artifacts in the 2-4 kHz band.", "https://x/r/1")
    assert "Likely synthetic" in text.split("\n\n")[0]
    assert "https://x/r/1" in text


def test_unknown_verdict_falls_back_to_insufficient_evidence():
    assert "Insufficient evidence" in format_verdict("bogus", "", "https://x/r/1")


def test_empty_reason_omitted_disclaimer_kept():
    text = format_verdict("verified", "  ", "https://x/r/1")
    assert "Why:" not in text
    assert text.endswith(DISCLAIMER)
