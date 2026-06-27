"""Tests for the text report's easy vs advanced modes."""

from __future__ import annotations

from flac_detective.reporting.text_reporter import TextReporter

_FAKE = {
    "filename": "track.flac",
    "filepath": "/music/track.flac",
    "score": 95,
    "verdict": "FAKE_CERTAIN",
    "cutoff_freq": 16000,
    "estimated_mp3_bitrate": 128,
    "reason": "R2: cutoff low | R9: artefacts",
}
_AUTH = {"filename": "ok.flac", "score": 0, "verdict": "AUTHENTIC"}


def test_easy_mode_plain_language(tmp_path):
    """Easy mode: plain verdict + action, and none of the plumbing."""
    out = tmp_path / "easy.txt"
    TextReporter(advanced=False).generate_report([_FAKE, _AUTH], out)
    text = out.read_text(encoding="utf-8")
    assert "Replace it" in text  # the recommended action
    assert "128 kbps" in text  # plain explanation
    # Plumbing must be absent.
    assert "R2" not in text and "R9" not in text
    assert "Cutoff" not in text and "Bitrate" not in text
    assert "/100" not in text and "/150" not in text


def test_easy_mode_all_clear(tmp_path):
    """With nothing flagged, easy mode says so plainly."""
    out = tmp_path / "clear.txt"
    TextReporter(advanced=False).generate_report([_AUTH], out)
    text = out.read_text(encoding="utf-8")
    assert "All clear" in text


def test_advanced_mode_keeps_technical_table(tmp_path):
    """Advanced mode (default) still shows the technical suspicious table."""
    out = tmp_path / "adv.txt"
    TextReporter(advanced=True).generate_report([_FAKE, _AUTH], out)
    text = out.read_text(encoding="utf-8")
    assert "SUSPICIOUS FILES" in text
    assert "Cutoff" in text  # the technical column header
    assert "Score" in text


def test_default_is_advanced(tmp_path):
    """Constructing TextReporter() with no args preserves the historical (advanced) report."""
    out = tmp_path / "def.txt"
    TextReporter().generate_report([_FAKE], out)
    assert "SUSPICIOUS FILES" in out.read_text(encoding="utf-8")
