"""Rule 1's gate D: a slope is not a wall (v1.13.15, issue #8 fourth round).

Two rips of the same track, from two compilations, both rolling off gently
from 12 to 19 kHz, read a "192 kbps signature" at 17,250 Hz and were then
convicted or cleared on the container window alone. The position of an edge
cannot tell a mastering slope from a codec wall; the size of the step across
it can. These tests pin the instrument (``spectrum.edge_step_db``), the gate
(``apply_rule_1_mp3_bitrate``) and the hoisted mirror
(``rule1_may_consult_container``). Every test that pins the repaired
behaviour was run against the 1.13.14 tree first and fails there.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import WALL_GATE_MAX_HZ, WALL_MIN_STEP_DB
from flac_detective.analysis.new_scoring.rules.spectral import (
    apply_rule_1_mp3_bitrate,
    edge_is_a_slope,
    rule1_may_consult_container,
)
from flac_detective.analysis.spectrum import (
    analyze_spectrum,
    cell_profile_db,
    edge_step_db,
)

SR = 44100
N = 2**17  # bins of ~0.34 Hz: every 250 Hz cell holds hundreds of bins


def _spectrum(level_db):
    """A magnitude spectrum in dB with the given level as a function of Hz."""
    freq = np.fft.rfftfreq(N, 1 / SR)
    return freq, np.array([level_db(f) for f in freq], dtype=float)


def _wall(at_hz: float, depth_db: float = 40.0):
    return _spectrum(lambda f: 0.0 if f < at_hz else -depth_db)


def _slope(from_hz: float = 12000.0, db_per_khz: float = 6.0):
    return _spectrum(lambda f: 0.0 if f < from_hz else -(f - from_hz) / 1000.0 * db_per_khz)


class TestInstrument:
    def test_a_codec_wall_reads_its_full_depth(self):
        freq, mag = _wall(17250.0)
        assert edge_step_db(freq, mag, 17250.0, SR) == pytest.approx(40.0, abs=0.5)

    def test_a_six_db_per_khz_slope_reads_the_step_of_two_cells(self):
        """The reporter's file: ~6 dB/kHz, so two 250 Hz cells fall ~3 dB."""
        freq, mag = _slope()
        step = edge_step_db(freq, mag, 17250.0, SR)
        assert step == pytest.approx(3.0, abs=0.5)
        assert step < WALL_MIN_STEP_DB

    def test_no_edge_is_nan_not_zero(self):
        freq, mag = _spectrum(lambda f: 0.0)
        assert math.isnan(edge_step_db(freq, mag, 22050.0, SR))

    def test_a_wall_one_cell_off_the_reported_edge_is_still_seen(self):
        """detect_cutoff reports the start of the drop; the step may sit a cell away."""
        freq, mag = _wall(17500.0)
        assert edge_step_db(freq, mag, 17250.0, SR) > WALL_MIN_STEP_DB

    def test_cells_are_relative_to_the_reference_band(self):
        freq, mag = _wall(17250.0, depth_db=30.0)
        first, cells = cell_profile_db(freq, mag, SR)
        assert first == 14000.0
        assert cells[0] == pytest.approx(0.0, abs=0.1)
        assert cells[(17250 - 14000) // 250] == pytest.approx(-30.0, abs=0.1)

    def test_bar_is_between_the_two_populations(self):
        """LAME walls read 18-45 dB on full tracks; the reporter's slope 4-6 dB."""
        assert 6.0 < WALL_MIN_STEP_DB < 18.0


class TestGateD:
    @staticmethod
    def _r1(**kw):
        defaults = {
            "cutoff_freq": 17250.0,
            "container_bitrate": 735.0,  # the reporter's convicted rip
            "cutoff_std": 117.9,
            "sample_rate": SR,
            "energy_ratio": 1e-7,
            "residual_floor_db": float("nan"),
        }
        defaults.update(kw)
        (score, reasons), est = apply_rule_1_mp3_bitrate(**defaults)
        return score, est, reasons

    def test_the_reporters_file_no_longer_scores(self):
        score, est, reasons = self._r1(edge_step_db=5.2)
        assert score == 0 and est is None
        assert any("not a codec wall" in r for r in reasons)

    def test_a_wall_still_scores(self):
        score, est, _ = self._r1(edge_step_db=34.0)
        assert score == 50 and est == 192

    def test_unknown_step_is_not_a_slope(self):
        """An unknown step passes, like an unknown wander at gate A: legacy kept."""
        score, est, _ = self._r1(edge_step_db=float("nan"))
        assert score == 50 and est == 192

    def test_a_measured_zero_is_the_flattest_slope(self):
        assert edge_is_a_slope(0.0, 17250.0)
        assert not edge_is_a_slope(float("nan"), 17250.0)
        assert not edge_is_a_slope(WALL_MIN_STEP_DB, 17250.0)

    def test_the_gate_abstains_from_the_320_cell_up(self):
        """Up there a V0 low-pass and a genuine anti-alias roll-off are both soft.

        The step separates nothing; the residual-floor gate reads depth instead.
        """
        assert WALL_GATE_MAX_HZ == 19500.0
        assert not edge_is_a_slope(5.0, WALL_GATE_MAX_HZ)
        assert edge_is_a_slope(5.0, WALL_GATE_MAX_HZ - 250.0)
        # A soft step in the 320 cell with a deep floor still scores (the 320
        # branch decides on depth, exactly as in 1.13.14).
        (score, _), est = apply_rule_1_mp3_bitrate(
            20250.0, 900.0, 0.0, SR, 1e-5, residual_floor_db=-60.0, edge_step_db=5.0
        )
        assert score == 50 and est == 320

    def test_gate_d_reads_the_same_bar_as_the_rule(self):
        just_under = WALL_MIN_STEP_DB - 0.1
        score, _, _ = self._r1(edge_step_db=just_under)
        assert score == 0
        score, _, _ = self._r1(edge_step_db=WALL_MIN_STEP_DB)
        assert score == 50


class TestMirror:
    """The hoisted gate must refuse exactly what the rule refuses."""

    def test_mirror_refuses_the_slope(self):
        assert not rule1_may_consult_container(17250.0, SR, 117.9, 5.2)

    def test_mirror_admits_the_wall_and_the_unknown(self):
        assert rule1_may_consult_container(17250.0, SR, 117.9, 34.0)
        assert rule1_may_consult_container(17250.0, SR, 117.9, float("nan"))

    @pytest.mark.parametrize(
        "step", [0.0, 5.2, WALL_MIN_STEP_DB - 0.1, WALL_MIN_STEP_DB, 34.0, float("nan")]
    )
    def test_mirror_and_rule_agree(self, step):
        (score, _), _ = apply_rule_1_mp3_bitrate(
            17250.0, 735.0, 117.9, SR, 1e-7, residual_floor_db=float("nan"), edge_step_db=step
        )
        assert rule1_may_consult_container(17250.0, SR, 117.9, step) == (score == 50)


def _shaped_noise(path, gain_db, seconds: int = 20, seed: int = 7):
    """White noise whose spectrum follows ``gain_db(f)``, written as 44.1/16 FLAC."""
    import soundfile as sf

    rng = np.random.default_rng(seed)
    n = SR * seconds
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 10 ** (np.array([gain_db(x) for x in f]) / 20.0)
    audio = np.fft.irfft(spec, n)
    audio = (audio / np.abs(audio).max() * 0.5).astype(np.float32)
    sf.write(path, np.stack([audio, audio], axis=1), SR, subtype="PCM_16")
    return path


class TestAnalyzeSpectrumCarriesTheStep:
    def test_five_values_and_the_step_of_a_synthetic_slope(self, tmp_path):
        """The reporter's shape: flat to 12 kHz, then -6 dB/kHz, no wall anywhere."""
        path = _shaped_noise(
            tmp_path / "slope.flac",
            lambda f: 0.0 if f < 12000 else -(f - 12000) / 1000.0 * 6.0,
        )
        cutoff, energy, std, floor, step = analyze_spectrum(path, 30.0)
        assert 16000.0 <= cutoff <= 18000.0  # 30 dB down is reached near 17 kHz
        assert not math.isnan(step)
        assert step < WALL_MIN_STEP_DB

    def test_the_step_of_a_synthetic_wall(self, tmp_path):
        path = _shaped_noise(tmp_path / "wall.flac", lambda f: 0.0 if f < 16000 else -60.0)
        cutoff, energy, std, floor, step = analyze_spectrum(path, 30.0)
        assert 15500.0 <= cutoff <= 16500.0
        assert step >= WALL_MIN_STEP_DB
