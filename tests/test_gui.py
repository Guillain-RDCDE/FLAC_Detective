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
    # The stashed result round-trips on the first cell.
    stashed = win._table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    assert stashed["filename"] in {"a.flac", "b.flac"}


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
