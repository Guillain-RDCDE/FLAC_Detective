"""Coverage for the CLI file-discovery / routing layer (previously untested).

This locks in the v0.15 behaviour that matters most: WAV and FLAC are routed to
the analyser, while lossy formats (mp3/m4a/…) are routed to the "replace with a
real FLAC" reject list — and the helpers that parse user-supplied paths.
"""

from __future__ import annotations

from pathlib import Path

from flac_detective.main import (
    _clean_path_string,
    _create_non_flac_result,
    _parse_multiple_paths,
    _validate_paths,
    scan_files,
)
from flac_detective.utils import find_flac_files, find_non_flac_audio_files


# --- path-string helpers ---------------------------------------------------
def test_parse_multiple_paths_separators():
    assert _parse_multiple_paths("a; b ; c") == ["a", "b", "c"]
    assert _parse_multiple_paths("a, b") == ["a", "b"]
    assert _parse_multiple_paths("single") == ["single"]


def test_clean_path_string_strips_quotes():
    assert _clean_path_string('"/music/x"') == "/music/x"
    assert _clean_path_string("'/music/x'") == "/music/x"
    assert _clean_path_string("/music/x") == "/music/x"


def test_validate_paths_keeps_only_existing(tmp_path):
    real = tmp_path / "real.flac"
    real.write_bytes(b"x")
    valid = _validate_paths([str(real), str(tmp_path / "ghost.flac")])
    assert valid == [real]


# --- discovery / routing ---------------------------------------------------
def _touch(p: Path):
    p.write_bytes(b"\x00")


def test_scan_files_routes_lossless_vs_lossy(tmp_path):
    """FLAC + WAV go to the analyse list; lossy go to the non-FLAC reject list."""
    _touch(tmp_path / "a.flac")
    _touch(tmp_path / "b.wav")
    _touch(tmp_path / "c.mp3")
    _touch(tmp_path / "d.m4a")
    analyse, reject = scan_files([tmp_path])
    names = {p.name for p in analyse}
    rej = {p.name for p in reject}
    assert names == {"a.flac", "b.wav"}  # WAV analysed on its own merits (v0.15)
    assert {"c.mp3", "d.m4a"} <= rej


def test_scan_files_direct_wav_file(tmp_path):
    """A .wav passed directly (not a folder) is accepted for analysis."""
    wav = tmp_path / "x.wav"
    _touch(wav)
    analyse, reject = scan_files([wav])
    assert analyse == [wav]
    assert reject == []


def test_find_flac_files_recurses(tmp_path):
    _touch(tmp_path / "top.flac")
    sub = tmp_path / "cd1"
    sub.mkdir()
    _touch(sub / "deep.flac")
    _touch(tmp_path / "skip.mp3")
    found = {p.name for p in find_flac_files(tmp_path)}
    assert found == {"top.flac", "deep.flac"}


def test_find_non_flac_audio_files(tmp_path):
    _touch(tmp_path / "a.mp3")
    _touch(tmp_path / "b.opus")
    _touch(tmp_path / "keep.flac")
    found = {p.name for p in find_non_flac_audio_files(tmp_path)}
    assert "a.mp3" in found and "b.opus" in found
    assert "keep.flac" not in found


# --- non-FLAC result --------------------------------------------------------
def test_create_non_flac_result_is_max_fake():
    res = _create_non_flac_result(Path("/music/song.mp3"))
    assert res["verdict"] == "NON_FLAC"
    assert res["score"] == 100
    assert "MP3" in res["reason"]
