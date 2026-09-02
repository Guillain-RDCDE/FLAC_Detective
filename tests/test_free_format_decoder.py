"""A third-party decoder binary is hashed before it is executed, and its failures are loud.

Set C's MP3 ladder climbs past 320 kbps into free format, which ffmpeg cannot
read at all — measured on 2 September: it emits ``[mp3float] Header missing``
once per frame and produces no audio, while ``lame --decode`` reads the same file
without complaint. So the decoder that reads those files comes from the other
party, and a binary someone else built gets its digest checked every time before
it runs.

The failure mode being guarded here is the one this exchange keeps meeting: a
decode that produces nothing and reports success, so silence reaches a manifest
looking like data.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from free_format import DecoderRefused, decode_free_format, verify_decoder  # noqa: E402


class _Completed:
    def __init__(self, returncode=0, stderr=b""):
        self.returncode = returncode
        self.stderr = stderr


def _fake_lame(tmp_path: Path) -> Path:
    exe = tmp_path / "lame.exe"
    exe.write_bytes(b"not really lame, but it hashes")
    return exe


def test_a_missing_decoder_is_refused(tmp_path):
    with pytest.raises(DecoderRefused, match="no decoder"):
        verify_decoder(tmp_path / "absent.exe")


def test_the_digest_is_returned_when_none_is_expected(tmp_path):
    exe = _fake_lame(tmp_path)
    assert verify_decoder(exe) == hashlib.sha256(exe.read_bytes()).hexdigest()


def test_a_wrong_digest_stops_execution(tmp_path):
    exe = _fake_lame(tmp_path)
    with pytest.raises(DecoderRefused, match="does not match"):
        verify_decoder(exe, "0" * 64)


def test_the_right_digest_passes(tmp_path):
    exe = _fake_lame(tmp_path)
    good = hashlib.sha256(exe.read_bytes()).hexdigest()
    assert verify_decoder(exe, good.upper()) == good


def test_decoding_checks_the_binary_before_running_it(tmp_path, monkeypatch):
    """A bad digest must stop the decode, not merely be reported after it."""
    exe = _fake_lame(tmp_path)
    ran = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: ran.append(a) or _Completed())
    with pytest.raises(DecoderRefused):
        decode_free_format(tmp_path / "x.mp3", tmp_path / "out.wav", exe, "0" * 64)
    assert not ran, "the decoder was executed despite a failed hash check"


def test_a_decode_that_writes_nothing_is_a_failure(tmp_path, monkeypatch):
    """Exit 0 with no output is the silence this exchange keeps mistaking for data."""
    exe = _fake_lame(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed(returncode=0))
    with pytest.raises(DecoderRefused, match="failed"):
        decode_free_format(tmp_path / "x.mp3", tmp_path / "out.wav", exe)


def test_an_empty_output_file_is_a_failure(tmp_path, monkeypatch):
    exe = _fake_lame(tmp_path)
    out = tmp_path / "out.wav"

    def fake_run(*a, **k):
        out.write_bytes(b"")
        return _Completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(DecoderRefused, match="failed"):
        decode_free_format(tmp_path / "x.mp3", out, exe)


def test_a_real_decode_returns_the_output(tmp_path, monkeypatch):
    exe = _fake_lame(tmp_path)
    out = tmp_path / "out.wav"

    def fake_run(*a, **k):
        out.write_bytes(b"RIFF....WAVE" + b"\x00" * 100)
        return _Completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert decode_free_format(tmp_path / "x.mp3", out, exe) == out
