"""The Explorer right-click entry (``--install-context-menu``)."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import pytest

from flac_detective import shell_menu
from flac_detective.cli.args import build_parser


def test_gui_command_uses_pythonw_and_the_folder(tmp_path):
    python = tmp_path / "python.exe"
    python.touch()
    (tmp_path / "pythonw.exe").touch()
    command = shell_menu.build_command(python, gui=True)
    assert command == f'"{tmp_path / "pythonw.exe"}" -m flac_detective.gui.app "%V"'


def test_gui_command_falls_back_to_python_without_pythonw(tmp_path):
    python = tmp_path / "python.exe"
    assert shell_menu.build_command(python, gui=True).startswith(f'"{python}" -m')


def test_console_command_stays_open_on_the_summary(tmp_path):
    python = tmp_path / "python.exe"
    command = shell_menu.build_command(python, gui=False)
    assert command == f'cmd.exe /k ""{python}" -m flac_detective.main "%V""'


@pytest.mark.skipif(sys.platform != "win32", reason="Explorer quoting is Windows-only")
def test_drive_root_quote_is_dropped():
    # "%V" on D:\ reaches the program as D:" (the backslash escapes the quote).
    assert shell_menu.clean_shell_path('D:"') == "D:"
    assert shell_menu.clean_shell_path(r"C:\Music\Album") == r"C:\Music\Album"


def test_menu_options_parse_and_exclude_each_other():
    parser = build_parser()
    assert parser.parse_args(["--install-context-menu"]).install_context_menu
    assert parser.parse_args(["--uninstall-context-menu"]).uninstall_context_menu
    with pytest.raises(SystemExit):
        parser.parse_args(["--install-context-menu", "--uninstall-context-menu"])


@pytest.mark.skipif(sys.platform != "win32", reason="registry is Windows-only")
def test_install_then_uninstall_round_trip(monkeypatch):
    import winreg

    # A scratch key, never the user's real Explorer menu.
    root = r"Software\FlacDetectiveTest"
    parents = (rf"{root}\Directory\shell", rf"{root}\Directory\Background\shell")
    monkeypatch.setattr(shell_menu, "_PARENTS", parents)
    try:
        command = shell_menu.install(python=Path(r"C:\py\python.exe"), gui=False)
        for parent in parents:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"{parent}\FlacDetective") as key:
                assert winreg.QueryValueEx(key, "MUIVerb")[0] == shell_menu.MENU_LABEL
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, rf"{parent}\FlacDetective\command"
            ) as key:
                assert winreg.QueryValueEx(key, "")[0] == command
        assert shell_menu.uninstall() is True
        assert shell_menu.uninstall() is False
    finally:
        for sub in (
            rf"{root}\Directory\Background\shell",
            rf"{root}\Directory\Background",
            rf"{root}\Directory\shell",
            rf"{root}\Directory",
            root,
        ):
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
