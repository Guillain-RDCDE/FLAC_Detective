"""Entry point for the FLAC Detective desktop GUI (``flac-detective-gui``).

Keeps the PySide6 import lazy and inside :func:`main` so a missing optional
dependency yields a friendly hint (``pip install "flac-detective[gui]"``) instead
of a raw ImportError traceback.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Launch the GUI; return a process exit code."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "The GUI needs PySide6 (and matplotlib). Install the optional extra:\n"
            '    pip install "flac-detective[gui]"\n'
        )
        return 1

    # Imported here (not at module top) so the import-hint above fires first.
    from .main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("FLAC Detective")
    window = MainWindow()
    window.show()
    # int(...) — QApplication.exec() is typed Any in the PySide6 stubs and the
    # project's mypy config has warn_return_any.
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
