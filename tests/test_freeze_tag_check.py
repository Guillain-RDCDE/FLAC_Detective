"""A failure to check for tags must not read as a clean file.

``has_tags`` returned False — "no metadata" — whenever ffprobe was missing,
timed out, or exited non-zero. The freeze then continued and shipped a file that
nobody had actually inspected, and one surviving ``encoder`` tag hands the other
party the answer for that file.

Same species as the frame-count audit that logged without refusing, and as
Provir's timestamp client that printed into a console nobody watched: a check
whose failure mode is silence. An unverifiable file is not a clean one, and the
safe direction is the one that stops the freeze.

Also covered: the check reads STREAM tags as well as format tags. ffmpeg writes
an encoder string into either, and set B arrived carrying exactly that shape of
leak in its WAV headers — a LIST/INFO chunk naming the muxer, identical across
all 280 files and therefore harmless only by luck.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

import freeze_exchange_set as fez  # noqa: E402


class _Completed:
    def __init__(self, stdout=b"", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_a_clean_file_reads_clean(monkeypatch, tmp_path):
    """The control: ffprobe runs, finds nothing, and the file passes."""
    monkeypatch.setattr(fez.subprocess, "run", lambda *a, **k: _Completed(b"  \n"))
    assert fez.has_tags(tmp_path / "x.flac") is False


def test_a_tag_is_found(monkeypatch, tmp_path):
    monkeypatch.setattr(fez.subprocess, "run", lambda *a, **k: _Completed(b"encoder=LAME\n"))
    assert fez.has_tags(tmp_path / "x.flac") is True


def test_ffprobe_missing_is_not_a_clean_file(monkeypatch, tmp_path):
    """The defect: OSError used to mean False, and the file shipped unchecked."""

    def boom(*a, **k):
        raise OSError("ffprobe not found")

    monkeypatch.setattr(fez.subprocess, "run", boom)
    assert fez.has_tags(tmp_path / "x.flac") is True


def test_a_timeout_is_not_a_clean_file(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="ffprobe", timeout=60)

    monkeypatch.setattr(fez.subprocess, "run", boom)
    assert fez.has_tags(tmp_path / "x.flac") is True


def test_a_nonzero_exit_is_not_a_clean_file(monkeypatch, tmp_path):
    """A probe can fail while still returning empty stdout, which is not 'no tags'."""
    monkeypatch.setattr(fez.subprocess, "run", lambda *a, **k: _Completed(b"", returncode=1))
    assert fez.has_tags(tmp_path / "x.flac") is True


def test_stream_tags_are_read_too(monkeypatch, tmp_path):
    """An encoder string in a stream tag is the same leak as one in a format tag."""
    seen = {}

    def capture(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Completed(b"")

    monkeypatch.setattr(fez.subprocess, "run", capture)
    fez.has_tags(tmp_path / "x.flac")
    entries = seen["cmd"][seen["cmd"].index("-show_entries") + 1]
    assert "format_tags" in entries
    assert "stream_tags" in entries
