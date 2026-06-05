"""Tests for the HTML (visual triage) report writer."""

from __future__ import annotations

import numpy as np
import soundfile as sf

from flac_detective.reporting import HTMLReporter
from flac_detective.reporting.html_reporter import _compute_spectrum_curve


def _write(results, tmp_path, name="report.html"):
    out = tmp_path / name
    HTMLReporter().generate_report(results, out)
    return out.read_text(encoding="utf-8")


def _make_wav(path, sr=44100, seconds=2.0, cutoff_hz=None):
    """Write a synthetic WAV. With cutoff_hz, only tones below it are present."""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    tones = [1000, 4000, 8000, 15000, 20000]
    if cutoff_hz is not None:
        tones = [f for f in tones if f < cutoff_hz]
    sig = sum(np.sin(2 * np.pi * f * t) for f in tones) / max(len(tones), 1)
    sf.write(path, sig.astype(np.float32), sr)
    return path


def test_html_is_single_self_contained_document(tmp_path):
    """One HTML file, no external assets — styles and script are inlined."""
    html = _write([{"filename": "a.flac", "score": 0, "verdict": "AUTHENTIC"}], tmp_path)
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html
    assert "<style>" in html and "<script>" in html
    # No external stylesheet / script references.
    assert 'src="http' not in html and 'href="http' not in html


def test_triage_table_ranked_most_suspicious_first(tmp_path):
    results = [
        {"filename": "a.flac", "score": 10, "verdict": "AUTHENTIC"},
        {"filename": "b.flac", "score": 95, "verdict": "FAKE_CERTAIN"},
        {"filename": "c.flac", "score": 58, "verdict": "SUSPICIOUS"},
    ]
    html = _write(results, tmp_path)
    # The worst file's row must appear before the others in source order.
    assert html.index("b.flac") < html.index("c.flac") < html.index("a.flac")


def test_summary_counts_by_verdict(tmp_path):
    results = [
        {"filename": "a.flac", "score": 0, "verdict": "AUTHENTIC"},
        {"filename": "b.flac", "score": 0, "verdict": "AUTHENTIC"},
        {"filename": "c.flac", "score": 95, "verdict": "FAKE_CERTAIN"},
    ]
    html = _write(results, tmp_path)
    assert 'class="summary"' in html
    # Total card plus per-verdict cards.
    assert ">3<" in html  # total files
    assert "Authentic" in html and "Fake (certain)" in html


def test_flagged_files_get_detail_cards_authentic_do_not(tmp_path):
    flagged = _write([{"filename": "f.flac", "score": 95, "verdict": "FAKE_CERTAIN"}], tmp_path)
    assert 'class="detail' in flagged

    clean = _write([{"filename": "ok.flac", "score": 0, "verdict": "AUTHENTIC"}], tmp_path)
    # No detail card section content for a clean-only scan.
    assert "Flagged files</h2><p" in clean.replace("\n", "")


def test_html_escapes_reason_and_path(tmp_path):
    """User/content strings must be HTML-escaped (no raw injection)."""
    results = [
        {
            "filename": "x.flac",
            "filepath": "C:/m/<b>x</b>.flac",
            "score": 60,
            "verdict": "SUSPICIOUS",
            "reason": "cutoff <script>alert(1)</script> low",
        }
    ]
    html = _write(results, tmp_path)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_spectrum_svg_rendered_for_readable_flagged_file(tmp_path):
    wav = _make_wav(tmp_path / "fake.wav", cutoff_hz=8000)
    results = [
        {
            "filename": "fake.wav",
            "filepath": str(wav),
            "score": 60,
            "verdict": "SUSPICIOUS",
            "cutoff_freq": 8000.0,
        }
    ]
    html = _write(results, tmp_path)
    assert '<svg class="spectrum"' in html
    assert "<polyline" in html
    assert "cutoff" in html  # the cutoff marker label


def test_spectrum_placeholder_when_file_unreadable(tmp_path):
    results = [
        {
            "filename": "gone.flac",
            "filepath": str(tmp_path / "does_not_exist.flac"),
            "score": 60,
            "verdict": "SUSPICIOUS",
        }
    ]
    html = _write(results, tmp_path)
    assert "Spectrum unavailable" in html
    assert "<polyline" not in html


def test_compute_spectrum_curve_shape(tmp_path):
    wav = _make_wav(tmp_path / "tone.wav")
    curve = _compute_spectrum_curve(str(wav))
    assert curve is not None
    freqs, norm, nyquist = curve
    assert len(freqs) == len(norm) > 2
    assert nyquist == 44100 / 2
    assert all(0.0 <= v <= 1.0 for v in norm)  # peak-normalised
    assert max(norm) == 1.0


def test_compute_spectrum_curve_returns_none_on_bad_input(tmp_path):
    assert _compute_spectrum_curve("") is None
    assert _compute_spectrum_curve(str(tmp_path / "nope.wav")) is None


def test_handles_empty_results(tmp_path):
    html = _write([], tmp_path)
    assert "<!DOCTYPE html>" in html
    assert "No files analyzed." in html
