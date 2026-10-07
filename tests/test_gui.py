"""Smoke tests for the PySide6 GUI (skipped where PySide6 isn't installed).

Runs headless via the offscreen Qt platform. Covers the table-population and
summary logic and a numeric-sort helper — not a full UI drive, but enough to
catch import/layout regressions and the result→row mapping.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# No update-check thread inside test windows (and no request to PyPI from a test).
os.environ.setdefault("FLAC_DETECTIVE_NO_UPDATE_CHECK", "1")

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


def test_update_notice_reaches_the_header(app, monkeypatch):
    """A newer release on PyPI (simulated) ends as a link in the header.

    The check runs on a QThread; the test lets it finish, pumps the event loop
    so the queued signal lands, and closes the window the way a user would, so
    the close-time wait is exercised too. Without a newer release the label
    stays hidden (the other tests, with the check switched off, never see it).
    """
    from flac_detective import update_check as uc

    monkeypatch.delenv("FLAC_DETECTIVE_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(uc, "latest_version", lambda: "9.9.9")
    win = MainWindow()
    assert win._update_worker is not None
    assert win._update_worker.wait(5000)
    for _ in range(20):
        app.processEvents()
    assert not win._update_label.isHidden()
    assert "9.9.9" in win._update_label.text()
    assert "pypi.org/project/flac-detective" in win._update_label.text()
    win.close()


def test_install_button_appears_and_runs_the_installer(app, monkeypatch):
    """The header button installs through updater.upgrade, off the UI thread.

    The confirmation dialog and the real installer are replaced: the dialog by
    a method that says yes, the installer by a stub that reports success.
    """
    from flac_detective import update_check as uc
    from flac_detective import updater as up
    from flac_detective.gui import main_window as mw

    monkeypatch.delenv("FLAC_DETECTIVE_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(uc, "latest_version", lambda: "9.9.9")
    monkeypatch.setattr(
        up,
        "upgrade",
        lambda on_line=None, **kw: (
            on_line and on_line("Successfully installed flac-detective-9.9.9"),
            up.UpgradeResult(
                ok=True,
                method="pip",
                command=["x"],
                installed_version="9.9.9",
                message="Installed 9.9.9. Restart.",
            ),
        )[1],
    )
    monkeypatch.setattr(mw.QMessageBox, "information", lambda *a, **k: None)
    win = MainWindow()
    assert win._update_worker.wait(5000)
    for _ in range(20):
        app.processEvents()
    assert not win._update_button.isHidden()
    assert win._update_button.text() == "Install v9.9.9"

    monkeypatch.setattr(win, "_confirm_install", lambda: True)
    win._start_install()
    assert win._install_worker is not None
    assert win._install_worker.wait(10000)
    for _ in range(20):
        app.processEvents()
    assert "Restart" in win._summary_label.text()
    assert not win._update_button.isEnabled()
    win.close()


def test_a_deferred_install_offers_to_close_the_app(app, monkeypatch):
    """Windows path: the result says 'after exit'; the app asks to close and does."""
    from flac_detective import update_check as uc
    from flac_detective import updater as up
    from flac_detective.gui import main_window as mw

    monkeypatch.delenv("FLAC_DETECTIVE_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(uc, "latest_version", lambda: "9.9.9")
    monkeypatch.setattr(
        up,
        "upgrade",
        lambda on_line=None, **kw: up.UpgradeResult(
            ok=False, method="pip", command=["x"], deferred=True, message="will install on exit"
        ),
    )
    asked = []

    def question(*a, **k):
        asked.append(a[1])
        return mw.QMessageBox.StandardButton.Yes

    monkeypatch.setattr(mw.QMessageBox, "question", question)
    win = MainWindow()
    assert win._update_worker.wait(5000)
    for _ in range(20):
        app.processEvents()
    monkeypatch.setattr(win, "_confirm_install", lambda: True)
    closed = []
    monkeypatch.setattr(win, "close", lambda: closed.append(True) or True)
    win._start_install()
    assert win._install_worker.wait(10000)
    for _ in range(20):
        app.processEvents()
    assert asked == ["Close to install"]
    assert closed == [True]
    assert "will install on exit" in win._summary_label.text()


def test_no_update_check_thread_when_opted_out(app, monkeypatch):
    monkeypatch.setenv("FLAC_DETECTIVE_NO_UPDATE_CHECK", "1")
    win = MainWindow()
    assert win._update_worker is None
    assert win._update_label.isHidden()


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
