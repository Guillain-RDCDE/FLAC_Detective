"""Tests for audio_formats: codec probing, lossless classification, ffmpeg decode.

The structural foundation for ALAC/APE support. Fixtures are generated with
ffmpeg; the whole module is skipped if ffmpeg/ffprobe aren't available.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from flac_detective.analysis import audio_formats as af

sf = pytest.importorskip("soundfile")

if not af.ffmpeg_available():
    pytest.skip("ffmpeg/ffprobe not on PATH", allow_module_level=True)


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    """A short WAV, plus ALAC, AAC and FLAC re-encodes of it."""
    d = tmp_path_factory.mktemp("fmt")
    wav = d / "src.wav"
    sr = 44100
    x = (np.random.default_rng(0).standard_normal(sr * 2) * 0.2).astype(np.float32)
    sf.write(str(wav), x, sr, subtype="PCM_16")

    def enc(name, args):
        out = d / name
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-vn", *args, str(out)],
            check=True,
            capture_output=True,
        )
        return out

    return {
        "wav": wav,
        "alac": enc("a.m4a", ["-c:a", "alac"]),
        "aac": enc("b.m4a", ["-c:a", "aac", "-b:a", "192k"]),
        "flac": enc("c.flac", ["-c:a", "flac"]),
    }


def test_probe_codec(sources):
    assert af.probe_codec(sources["alac"]) == "alac"
    assert af.probe_codec(sources["aac"]) == "aac"
    assert af.probe_codec(sources["flac"]) == "flac"


def test_probe_codec_strips_trailing_comma_and_cr(monkeypatch):
    r"""Regression: ffprobe can emit 'alac,\r' on real ALAC files with cover art.

    Field validation on a real library found ~10 ALAC tracks whose csv codec_name
    came back as 'alac,' (trailing empty field + Windows CR), which made
    is_analysable_lossless reject them as if lossy. probe_codec must normalise it.
    """

    class _R:
        stdout = "alac,\r\n"

    monkeypatch.setattr(af.subprocess, "run", lambda *a, **k: _R())
    codec = af.probe_codec(Path("whatever.m4a"))
    assert codec == "alac"
    # And the file must therefore route to analysis, not the reject list.
    monkeypatch.setattr(af, "probe_codec", lambda _p: "alac")
    assert af.is_analysable_lossless(Path("whatever.m4a")) is True


def test_lossless_classification(sources):
    assert af.is_analysable_lossless(sources["flac"]) is True
    assert af.is_analysable_lossless(sources["wav"]) is True
    assert af.is_analysable_lossless(sources["alac"]) is True
    # An AAC .m4a is lossy — must NOT be treated as analysable lossless.
    assert af.is_analysable_lossless(sources["aac"]) is False


def test_needs_ffmpeg_decode(sources):
    assert af.needs_ffmpeg_decode(sources["flac"]) is False
    assert af.needs_ffmpeg_decode(sources["wav"]) is False
    assert af.needs_ffmpeg_decode(sources["alac"]) is True


def test_decode_alac_to_wav(sources):
    wav = af.decode_to_wav(sources["alac"])
    try:
        assert wav is not None and wav.exists()
        info = sf.info(str(wav))  # readable by libsndfile
        assert info.samplerate == 44100
        assert info.duration == pytest.approx(2.0, abs=0.1)
    finally:
        if wav:
            wav.unlink(missing_ok=True)
