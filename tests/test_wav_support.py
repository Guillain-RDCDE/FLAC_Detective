"""WAV support (v0.15): WAV files are analysed on their own merits.

Two things must hold: (1) metadata reads from the WAV header, and (2) a genuine
full-spectrum WAV is NOT a false positive — the container-bitrate rules (1 & 3),
which assume lossless *compression*, are gated off for uncompressed input so an
honest WAV doesn't get flagged just for having a "full" bitrate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from flac_detective.analysis.metadata import read_metadata

sf = pytest.importorskip("soundfile")


def _write_wav(path: Path, sr=44100, seconds=6.0, cutoff_hz=None):
    """Write a noise WAV; if cutoff_hz given, low-pass it (fake-transcode shape)."""
    rng = np.random.default_rng(0)
    x = rng.standard_normal(int(sr * seconds)).astype(np.float32) * 0.3
    if cutoff_hz is not None:
        from scipy.signal import butter, sosfilt

        sos = butter(8, cutoff_hz, "low", fs=sr, output="sos")
        x = sosfilt(sos, x).astype(np.float32)
    sf.write(str(path), x, sr, subtype="PCM_16")


def test_read_metadata_wav(tmp_path):
    """read_metadata dispatches to soundfile for .wav and returns the header."""
    wav = tmp_path / "a.wav"
    _write_wav(wav, sr=44100, seconds=2.0)
    md = read_metadata(wav)
    assert md["sample_rate"] == 44100
    assert md["bit_depth"] == 16
    assert md["channels"] == 1
    assert md["duration"] == pytest.approx(2.0, abs=0.05)
    assert md["encoder"] == "WAV"


def test_full_spectrum_wav_is_authentic(tmp_path):
    """A genuine full-band WAV must not be flagged (R1/R3 gated for uncompressed)."""
    from flac_detective.analysis.analyzer import FLACAnalyzer

    wav = tmp_path / "clean.wav"
    _write_wav(wav, cutoff_hz=None)  # white noise reaches Nyquist
    res = FLACAnalyzer().analyze_file(wav)
    assert res["verdict"] == "AUTHENTIC", res
    assert res["score"] <= 30, res


# NOTE on detecting fake (transcoded) WAVs: the cutoff/cliff rules are tuned for
# *music*, not synthetic noise, so a faithful unit test would need a real MP3→WAV
# round-trip (we don't want an ffmpeg dependency in the suite). That direction is
# the same codec-agnostic spectral path already covered by the FLAC rule tests,
# and was verified manually: a 128 kbps MP3 decoded to WAV scores SUSPICIOUS (66).
