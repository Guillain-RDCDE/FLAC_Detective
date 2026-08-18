"""Tests for the work-directory resolution (progress.json / report / log location).

Regression (GitHub issue: read-only audio directory in a container): the CLI
always wrote ``progress.json`` and the auto-named report next to the audio, so a
scan of a ``:ro`` mount failed on every progress save and could blow up at the
very end when writing the report — after all the analysis work was done. The old
code comment promised a fallback to the current directory that never existed.

Now: ``--work-dir DIR`` picks the location explicitly; without it, the scan
directory is used when writable, else the current directory, else the temp dir.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

from flac_detective import main as m

# ---------------------------------------------------------------------------
# _is_writable_dir — the probe
# ---------------------------------------------------------------------------


def test_is_writable_dir_true_for_tmp(tmp_path):
    assert m._is_writable_dir(tmp_path) is True
    # The probe must not leave anything behind.
    assert list(tmp_path.iterdir()) == []


def test_is_writable_dir_false_for_missing_dir(tmp_path):
    assert m._is_writable_dir(tmp_path / "nope") is False


def test_is_writable_dir_false_for_a_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    assert m._is_writable_dir(f) is False


@pytest.mark.skipif(sys.platform == "win32", reason="chmod is not enforced on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores directory permissions"
)
def test_is_writable_dir_false_for_chmod_555(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        assert m._is_writable_dir(ro) is False
    finally:
        ro.chmod(0o755)


# ---------------------------------------------------------------------------
# resolve_work_dir — the policy
# ---------------------------------------------------------------------------


def test_explicit_work_dir_is_created_and_returned(tmp_path):
    wd = tmp_path / "state" / "nested"
    wd_out, notes = m.resolve_work_dir([tmp_path], wd)
    assert wd_out == wd
    assert notes == []
    assert wd.is_dir()


def test_explicit_work_dir_unwritable_exits_early(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(m, "_is_writable_dir", lambda p: False)
    with pytest.raises(SystemExit) as exc:
        m.resolve_work_dir([tmp_path], tmp_path / "wd")
    assert exc.value.code == 2
    assert "not writable" in capsys.readouterr().err


def test_default_uses_scan_directory(tmp_path):
    scan = tmp_path / "music"
    scan.mkdir()
    assert m.resolve_work_dir([scan]) == (scan, [])


def test_default_uses_parent_when_first_path_is_a_file(tmp_path):
    scan = tmp_path / "music"
    scan.mkdir()
    f = scan / "a.flac"
    f.write_bytes(b"")
    assert m.resolve_work_dir([f]) == (scan, [])


def test_readonly_scan_dir_falls_back_to_cwd(tmp_path, monkeypatch):
    scan = tmp_path / "music_ro"
    scan.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    real = m._is_writable_dir
    monkeypatch.setattr(m, "_is_writable_dir", lambda p: False if p == scan else real(p))
    out, notes = m.resolve_work_dir([scan])
    assert out == cwd
    # The user is told what happened and how to resume / override.
    assert any("read-only" in n for n in notes)
    assert any("--work-dir" in n for n in notes)


def test_nothing_writable_falls_back_to_tempdir(tmp_path, monkeypatch):
    scan = tmp_path / "music_ro"
    scan.mkdir()
    monkeypatch.chdir(tmp_path)
    tmp = Path(tempfile.gettempdir())
    monkeypatch.setattr(m, "_is_writable_dir", lambda p: p == tmp)
    out, notes = m.resolve_work_dir([scan])
    assert out == tmp
    assert any("temp" in n for n in notes)


@pytest.mark.skipif(sys.platform == "win32", reason="chmod is not enforced on Windows")
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores directory permissions"
)
def test_readonly_scan_dir_real_chmod_falls_back_to_cwd(tmp_path, monkeypatch):
    """The container scenario for real: audio dir chmod 555, CWD writable."""
    scan = tmp_path / "audio"
    scan.mkdir()
    (scan / "x.flac").write_bytes(b"")
    scan.chmod(0o555)
    cwd = tmp_path / "work"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    try:
        out, notes = m.resolve_work_dir([scan])
        assert out == cwd
        assert notes
    finally:
        scan.chmod(0o755)


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_parses_work_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["flac-detective", str(tmp_path), "--work-dir", "/tmp/fd"])
    args = m.parse_arguments()
    assert args.work_dir == Path("/tmp/fd")


def test_cli_work_dir_defaults_to_none(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["flac-detective", str(tmp_path)])
    args = m.parse_arguments()
    assert args.work_dir is None
