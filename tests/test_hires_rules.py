"""Rules 17 and 2 above 48 kHz and on dark passages (v2.5.0).

Two defects found on a purchased 24/192 solo-piano album, all 26 tracks flagged:

* Rule 17 read its fs/128 subbands at 192 kHz, 1.5 kHz each, where the high band
  of a quiet recording is the leakage of the low notes, phase-locked across
  subbands. It now reads above 48 kHz at the decoder rates (44.1 and 48 kHz)
  and keeps the higher reading.
* The low-wall instrument took a 16 dB step at 2 kHz in one window of three for
  a codec wall. A codec's low-pass is in every window; when several windows are
  read, the wall must now be read in at least two.

See ml/exchange/HIRES_RULES_REGISTRATION_2026-10-13.md.
"""

from __future__ import annotations

from functools import cache

import numpy as np
import soundfile as sf
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt

from flac_detective.analysis.new_scoring.rules.sbr_replication import (
    COHERENCE_HARD,
    COHERENCE_REVIEW,
)
from flac_detective.analysis.new_scoring.sbr import _coherence_at, replication_coherence
from flac_detective.analysis.spectrum import (
    LOW_WALL_MIN_WINDOWS,
    analyze_spectrum,
    is_low_wall_reading,
)


def _noise(n: int, rate: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n, 1 / rate)
    x = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) / np.sqrt(np.maximum(f, 50) / 50), n)
    return x / np.abs(x).max()


@cache
def _replicated(rate: int, seconds: float = 10.0, shift_bands: int = 22) -> np.ndarray:
    """A decoder's output at ``rate``: low band kept, high band a copy shifted by whole subbands."""
    n = int(rate * seconds)
    t = np.arange(n) / rate
    mono = _noise(n, rate, 3) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.7 * t)))
    low = sosfiltfilt(butter(8, 9000, "lowpass", fs=rate, output="sos"), mono)
    source = sosfiltfilt(butter(8, [2500, 9000], "bandpass", fs=rate, output="sos"), mono)
    copy = np.real(hilbert(source) * np.exp(2j * np.pi * shift_bands * rate / 128 * t))
    return low + copy * (0.4 + 0.2 * np.sin(2 * np.pi * 1.3 * t))


@cache
def _quiet_piano(rate: int = 192000, seconds: float = 10.0) -> np.ndarray:
    """Low struck notes with fast decays over a converter floor 90 dB down, nothing else."""
    n = int(rate * seconds)
    t = np.arange(n) / rate
    out = np.zeros(n)
    rng = np.random.default_rng(5)
    for start in np.arange(0.0, seconds, 0.6):
        f0 = 55.0 * 2 ** (rng.integers(0, 30) / 12)
        tt = t - start
        env = np.where(tt >= 0, np.exp(-tt * 3.0), 0.0)
        for h in range(1, 6):
            out += env * np.sin(2 * np.pi * f0 * h * tt) / h**2
    out = out / np.abs(out).max() * 0.3
    return out + 10 ** (-90 / 20) * np.random.default_rng(6).standard_normal(n)


def _up(x: np.ndarray, rate: int, to: int) -> np.ndarray:
    from math import gcd

    g = gcd(rate, to)
    return resample_poly(x, to // g, rate // g)


class TestRule17AboveFortyEightKilohertz:
    def test_the_synthetic_piano_reproduces_the_defect_at_192k(self):
        # The old reading, at the file's own rate: the defect this guards against.
        coherence, _ = _coherence_at(_quiet_piano(), 192000)
        assert coherence >= COHERENCE_REVIEW

    def test_a_quiet_piano_at_192k_no_longer_reads_as_replication(self):
        # Brought down, the synthetic's band above 5.5 kHz holds nothing within
        # 50 dB of its strongest subband, so the reading abstains (NaN), which
        # scores nothing; a finite reading must sit under the review bar.
        coherence, _ = replication_coherence(_quiet_piano(), 192000)
        assert not coherence >= COHERENCE_REVIEW

    def test_rates_up_to_48k_are_read_as_before(self):
        for rate in (44100, 48000):
            x = _replicated(rate)
            assert replication_coherence(x, rate) == _coherence_at(x, rate)

    def test_a_44k1_decode_resampled_up_still_reads_as_replication(self):
        for to in (88200, 96000, 192000):
            coherence, shift = replication_coherence(_up(_replicated(44100), 44100, to), to)
            assert coherence >= COHERENCE_HARD, to
            assert shift == 22

    def test_a_48k_decode_resampled_up_still_reads_as_replication(self):
        for to in (96000, 192000):
            coherence, shift = replication_coherence(_up(_replicated(48000), 48000, to), to)
            assert coherence >= COHERENCE_HARD, to
            assert shift == 22


SR = 44100


def _shaped(seconds: float, gain_db, seed: int) -> np.ndarray:
    n = int(SR * seconds)
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 10 ** (np.array([gain_db(x) for x in f]) / 20.0)
    x = np.fft.irfft(spec, n)
    return x / np.abs(x).max() * 0.5


def _full(f: float) -> float:
    return -f / 2000.0


def _wall(f: float) -> float:
    return 0.0 if f < 5000 else -90.0


def _write(path, parts) -> object:
    audio = np.concatenate(parts).astype(np.float32)
    sf.write(path, np.stack([audio, audio], axis=1), SR, subtype="PCM_16")
    return path


class TestLowWallAcrossWindows:
    """120 s files: the engine reads three contiguous 30 s windows, 15-45, 45-75, 75-105 s."""

    def test_two_windows_are_required(self):
        assert LOW_WALL_MIN_WINDOWS == 2

    def test_a_wall_in_one_window_of_three_is_not_believed(self, tmp_path):
        path = _write(
            tmp_path / "one.flac",
            [_shaped(45, _full, 1), _shaped(30, _wall, 2), _shaped(45, _full, 3)],
        )
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert not is_low_wall_reading(cutoff)

    def test_a_wall_in_two_windows_of_three_is_believed(self, tmp_path):
        path = _write(tmp_path / "two.flac", [_shaped(75, _wall, 4), _shaped(45, _full, 5)])
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert is_low_wall_reading(cutoff)
        assert 4750.0 <= cutoff <= 5250.0

    def test_a_wall_in_every_window_is_believed(self, tmp_path):
        path = _write(tmp_path / "all.flac", [_shaped(120, _wall, 6)])
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert is_low_wall_reading(cutoff)

    def test_a_one_window_file_keeps_its_single_reading(self, tmp_path):
        path = _write(tmp_path / "short.flac", [_shaped(20, _wall, 7)])
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert is_low_wall_reading(cutoff)
