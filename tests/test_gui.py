"""Smoke tests for the PySide6 GUI (skipped where PySide6 isn't installed).

Runs headless via the offscreen Qt platform. Covers the table-population and
summary logic and a numeric-sort helper — not a full UI drive, but enough to
catch import/layout regressions and the result→row mapping.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from flac_detective.gui.main_window import MainWindow, _num_item  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """A single QApplication for the module."""
    return QApplication.instance() or QApplication([])


def test_num_item_sorts_numerically(app):
    """The score/cutoff items must compare as numbers, not strings (9 < 86)."""
    assert _num_item(9) < _num_item(86)
    assert not (_num_item(100) < _num_item(20))


def test_append_row_and_summary(app):
    """Feeding results populates the table and the summary tallies verdicts."""
    win = MainWindow()
    results = [
        {
            "filename": "a.flac",
            "score": 92,
            "verdict": "FAKE_CERTAIN",
            "cutoff_freq": 16000,
            "sample_rate": 44100,
            "bit_depth": 16,
            "reason": "R2",
            "hires_verdict": "NOT_HIRES",
        },
        {
            "filename": "b.flac",
            "score": 3,
            "verdict": "AUTHENTIC",
            "cutoff_freq": 22050,
            "sample_rate": 96000,
            "bit_depth": 24,
            "reason": "ok",
            "hires_verdict": "UPSAMPLED",
            "hires_reason": "cliff",
        },
    ]
    for r in results:
        win._results.append(r)
        win._append_row(r)
    assert win._table.rowCount() == 2
    win._update_summary(cancelled=False)
    text = win._summary_label.text()
    assert "1 fake" in text and "1 fake hi-res" in text
    # The stashed result round-trips on the File cell (where _append_row puts it).
    from flac_detective.gui.main_window import _COL_FILE

    stashed = win._table.item(0, _COL_FILE).data(Qt.ItemDataRole.UserRole)
    assert stashed["filename"] in {"a.flac", "b.flac"}


def test_easy_advanced_toggle(app):
    """The Advanced toggle shows/hides the Score column and re-renders the detail."""
    from flac_detective.gui.main_window import _COL_SCORE

    win = MainWindow()
    r = {
        "filename": "x.flac",
        "filepath": "",
        "score": 92,
        "verdict": "FAKE_CERTAIN",
        "cutoff_freq": 16000,
        "estimated_mp3_bitrate": 128,
        "reason": "R2: cutoff low | R9: artefacts",
        "hires_verdict": "NOT_HIRES",
    }
    win._results.append(r)
    win._append_row(r)

    # Default = easy: Score column hidden, reasons are plain (no rule codes).
    assert win._table.isColumnHidden(_COL_SCORE)
    win._populate_detail(r)
    assert "R2" not in win._reasons.toHtml()
    assert "128 kbps" in win._reasons.toPlainText()

    # Flip to advanced: Score column shown, per-rule bullets return.
    win._advanced_check.setChecked(True)
    assert not win._table.isColumnHidden(_COL_SCORE)
    assert "R2" in win._reasons.toHtml()


def test_advanced_detail_says_which_rule_decided(app):
    """In advanced mode the detail panel leads with the deciding rule and the witness count.

    Issue #8's reporter looked at a `Fake 63` in this panel and could not see
    that the whole case was one spectral reading. The text report had carried
    the line since 1.13.11; the GUI had not. Same function, same line.
    """
    win = MainWindow()
    r = {
        "filename": "y.flac",
        "filepath": "",
        "score": 58,
        "verdict": "SUSPICIOUS",
        "cutoff_freq": 18250,
        "estimated_mp3_bitrate": 224,
        "reason": "Constant MP3 bitrate detected (Spectral): 224 kbps | R2: Cutoff 18250 Hz",
        "score_breakdown": {"Rule1MP3Bitrate": 50, "Rule2Cutoff": 8},
        "evidence_families": ["spectral"],
        "hires_verdict": "NOT_HIRES",
    }
    win._results.append(r)
    win._append_row(r)

    # Easy mode: no rule attribution, plain language only.
    win._populate_detail(r)
    assert "evidence family" not in win._reasons.toPlainText()

    win._advanced_check.setChecked(True)
    text = win._reasons.toPlainText()
    assert "MP3 bitrate signature +50" in text
    assert "1 evidence family: spectral" in text
    # The line precedes the per-rule bullets.
    assert text.index("evidence family") < text.index("R2:")


def test_collect_files_dedup(app, tmp_path):
    """Folder expansion de-duplicates and only picks up audio files."""
    (tmp_path / "x.flac").write_bytes(b"\x00")
    (tmp_path / "note.txt").write_text("nope")
    win = MainWindow()
    win._set_targets([tmp_path, tmp_path])  # same dir twice
    files = win._collect_files()
    names = {f.name for f in files}
    assert "x.flac" in names
    assert "note.txt" not in names
