"""Several folders selected, one right click: one window scans them all.

Explorer starts one copy of the GUI per selected folder. The copies started
together must meet in one window (gui/gather.py) instead of opening on top of
one another, each with one folder.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

# A copy of the GUI whose scan only reports what it was given, then quits.
_COPY = textwrap.dedent(
    """
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from flac_detective.gui import app, main_window
    from PySide6.QtWidgets import QApplication

    def scan_now(self, paths):
        print("SCAN " + "|".join(sorted(p.name for p in paths)), flush=True)
        QApplication.quit()

    main_window.MainWindow.scan_now = scan_now
    raise SystemExit(app.main())
    """
)


def _right_click(tmp_path, folders):
    script = tmp_path / "fd_gui_copy.py"
    script.write_text(_COPY, encoding="utf-8")
    env = {**os.environ, "USER": f"t{os.getpid()}", "USERNAME": f"t{os.getpid()}"}
    copies = [
        subprocess.Popen(
            [sys.executable, str(script), str(f)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
        )
        for f in folders
    ]
    outputs = [c.communicate(timeout=120)[0] for c in copies]
    assert all(c.returncode == 0 for c in copies)
    return [line for out in outputs for line in out.splitlines() if line.startswith("SCAN ")]


def test_four_folders_one_window(tmp_path):
    folders = []
    for name in ("a", "b", "c", "d"):
        (tmp_path / name).mkdir()
        folders.append(tmp_path / name)
    assert _right_click(tmp_path, folders) == ["SCAN a|b|c|d"]


def test_one_folder_still_scans(tmp_path):
    (tmp_path / "a").mkdir()
    assert _right_click(tmp_path, [tmp_path / "a"]) == ["SCAN a"]
