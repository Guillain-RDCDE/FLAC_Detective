"""A "Scan with FLAC Detective" entry in the Windows Explorer right-click menu.

Opening the GUI, then finding the folder again in a file dialog, is two steps
too many for "is this download genuine?". With the entry installed, a right
click on a folder (or on the empty space inside an open folder) opens the GUI
on that folder and starts the scan at once.

* Per user, under ``HKEY_CURRENT_USER\\Software\\Classes``: no administrator
  rights, nothing written for other accounts, and removed by
  ``--uninstall-context-menu`` the same way.
* The command is the interpreter this copy runs in, so a pipx or venv install
  points at itself and an upgrade in place keeps the entry working. Installing
  from another environment replaces the entry, never adds a second one.
* With the GUI extra (PySide6) the entry opens the GUI; without it, a console
  window runs the command-line scan and stays open on the summary.

On Windows 11 the entry is under "Show more options" (or Shift + right click):
the compact top-level menu only takes entries from signed packaged apps.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MENU_LABEL = "Scan with FLAC Detective"
_KEY_NAME = "FlacDetective"
# A folder, and the background of an open folder. %V is the folder in both cases
# (%1 is empty on a background click).
_PARENTS = (r"Software\Classes\Directory\shell", r"Software\Classes\Directory\Background\shell")
_ICON = Path(__file__).parent / "gui" / "resources" / "app_icon.ico"


def clean_shell_path(raw: str) -> str:
    """Undo Explorer's quoting of a drive root.

    ``"%V"`` on ``D:\\`` gives ``"D:\\"``, whose backslash escapes the closing
    quote when the command line is split, so the program receives ``D:"``. A
    path cannot end in a quote on Windows, so dropping one is always safe there.
    """
    return raw.rstrip('"') if sys.platform == "win32" else raw


def has_gui() -> bool:
    """Whether the GUI extra is installed in this interpreter."""
    return importlib.util.find_spec("PySide6") is not None


def build_command(python: Path, gui: bool) -> str:
    """The command line Explorer runs, ``%V`` standing for the folder."""
    if gui:
        # pythonw: no console window flashing up behind the GUI.
        pythonw = python.with_name("pythonw.exe")
        exe = pythonw if pythonw.exists() else python
        return f'"{exe}" -m flac_detective.gui.app "%V"'
    # cmd /k keeps the window open on the summary once the scan is done.
    return f'cmd.exe /k ""{python}" -m flac_detective.main "%V""'


def install(python: Path | None = None, gui: bool | None = None) -> str:
    """Write the menu entry for the current user; return the command it runs."""
    # Also how mypy, checking on Linux, knows winreg is only reached on Windows.
    if sys.platform != "win32":
        raise OSError("the right-click entry is for the Windows Explorer only")
    import winreg

    command = build_command(Path(python or sys.executable), has_gui() if gui is None else gui)
    for parent in _PARENTS:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{parent}\{_KEY_NAME}") as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, MENU_LABEL)
            if _ICON.exists():
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(_ICON))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{parent}\{_KEY_NAME}\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    return command


def uninstall() -> bool:
    """Remove the menu entry; return whether there was one."""
    if sys.platform != "win32":
        raise OSError("the right-click entry is for the Windows Explorer only")
    import winreg

    found = False
    for parent in _PARENTS:
        for sub in (rf"{parent}\{_KEY_NAME}\command", rf"{parent}\{_KEY_NAME}"):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
                found = True
            except FileNotFoundError:
                pass
    return found


def run_menu_command(action: str) -> int:
    """``--install-context-menu`` / ``--uninstall-context-menu``: do it and say so."""
    if sys.platform != "win32":
        print(
            "The right-click entry is for the Windows Explorer only. On another system, "
            "open the GUI (flac-detective-gui) and drop the folder on its window."
        )
        return 1
    if action == "install":
        command = install()
        print(f'Added "{MENU_LABEL}" to the right-click menu of folders.')
        print(f"  It runs: {command}")
        print('  On Windows 11 it is under "Show more options" (or Shift + right click).')
        if not has_gui():
            print(
                "  The GUI extra is not installed, so it opens a console scan. For the "
                'GUI: pip install "flac-detective[gui]", then run this command again.'
            )
        return 0
    if uninstall():
        print(f'Removed "{MENU_LABEL}" from the right-click menu.')
    else:
        print("There was no FLAC Detective entry in the right-click menu.")
    return 0
