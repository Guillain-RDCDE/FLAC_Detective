"""Entry point for the FLAC Detective desktop GUI (``flac-detective-gui``).

Keeps the PySide6 import lazy and inside :func:`main` so a missing optional
dependency yields a friendly hint (``pip install "flac-detective[gui]"``) instead
of a raw ImportError traceback.
"""

from __future__ import annotations

import sys
from pathlib import Path

_RESOURCES = Path(__file__).parent / "resources"


def _make_splash(QtCore, QtGui, QtWidgets):
    """An instant, branded loading screen shown while the heavy imports run.

    The first launch spends several seconds importing matplotlib and the
    analysis stack; without a splash that gap looks like "nothing happened".
    """
    icon_file = _RESOURCES / "app_icon.png"
    pad, icon_sz = 28, 88
    width, height = 360, 200

    canvas = QtGui.QPixmap(width, height)
    canvas.fill(QtGui.QColor("#ffffff"))
    painter = QtGui.QPainter(canvas)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    if icon_file.exists():
        icon = QtGui.QPixmap(str(icon_file)).scaled(
            icon_sz,
            icon_sz,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap((width - icon_sz) // 2, pad, icon)

    painter.setPen(QtGui.QColor("#1d1d1f"))
    title_font = QtGui.QFont("Segoe UI Variable Display", 15)
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.drawText(
        QtCore.QRect(0, pad + icon_sz + 6, width, 30),
        QtCore.Qt.AlignmentFlag.AlignHCenter,
        "FLAC Detective",
    )
    painter.setPen(QtGui.QColor("#6e6e73"))
    painter.setFont(QtGui.QFont("Segoe UI Variable Text", 9))
    painter.drawText(
        QtCore.QRect(0, pad + icon_sz + 36, width, 24),
        QtCore.Qt.AlignmentFlag.AlignHCenter,
        "Loading…",
    )
    painter.end()

    splash = QtWidgets.QSplashScreen(canvas)
    splash.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
    return splash


def main() -> int:
    """Launch the GUI; return a process exit code."""
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
    except ImportError:
        sys.stderr.write(
            "The GUI needs PySide6 (and matplotlib). Install the optional extra:\n"
            '    pip install "flac-detective[gui]"\n'
        )
        return 1

    app = QtWidgets.QApplication.instance()
    if not isinstance(app, QtWidgets.QApplication):
        # instance() also returns a bare QCoreApplication, which has no
        # setFont/setWindowIcon/setStyleSheet — accepting one would raise below.
        app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("FLAC Detective")

    icon_file = _RESOURCES / "app_icon.png"
    if icon_file.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_file)))

    # A modern, legible base font; the stylesheet refines sizes per role.
    app.setFont(QtGui.QFont("Segoe UI Variable Text", 10))

    # Show the splash before the expensive imports so feedback is instant.
    splash = _make_splash(QtCore, QtGui, QtWidgets)
    splash.show()
    app.processEvents()

    # Heavy imports happen here (matplotlib, analysis stack) — behind the splash.
    from . import style
    from .main_window import MainWindow

    app.setStyleSheet(style.APP_STYLE)
    window = MainWindow()

    # Size to FIT the primary screen, then centre on it. Without this the window
    # can open off-view: too tall for a scaled display (its title bar lands
    # above the top edge) or pushed onto a 2nd monitor — both look like the
    # launch did "nothing". Clamp to the available work area so it stays whole
    # and visible on any DPI / multi-monitor layout.
    primary = QtGui.QGuiApplication.primaryScreen()
    if primary is not None:
        area = primary.availableGeometry()
        w = min(1180, int(area.width() * 0.92))
        h = min(760, int(area.height() * 0.92))
        window.resize(w, h)
        x = area.x() + max(0, (area.width() - w) // 2)
        y = area.y() + max(0, (area.height() - h) // 2)
        window.move(x, y)

    window.show()
    window.setWindowState(
        (window.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
    )
    window.raise_()
    window.activateWindow()
    splash.finish(window)
    # int(...) — QApplication.exec() is typed Any in the PySide6 stubs and the
    # project's mypy config has warn_return_any.
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
