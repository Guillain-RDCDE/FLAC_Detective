"""Rule 1's depth gate: the floor above the edge (v1.13.16).

Two Beatport AIFFs of a track whose CD and vinyl editions run to 20.5-21 kHz
read a soft edge at 16 kHz (7.7 and 8.8 dB over 500 Hz) and nothing above it
(-63 and -65 dB), and 1.13.15 cleared both: gate D read the edge as a slope,
and on an uncompressed container gate C-prime had no depth reading to accept
the PCM-level bitrate. The step across an edge cannot tell a gentle codec
filter from a mastering roll-off; what is left above the edge can. These
tests pin the instrument (``spectrum.floor_above_edge_db``), the two gates it
feeds in ``apply_rule_1_mp3_bitrate`` and the hoisted mirror
(``rule1_may_consult_container``). Every test that pins the repaired
behaviour fails on the 1.13.15 tree.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import (
    DEEP_FLOOR_DB,
    WALL_GATE_MAX_HZ,
    WALL_MIN_STEP_DB,
)
from flac_detective.analysis.new_scoring.rules.spectral import (
    apply_rule_1_mp3_bitrate,
    edge_is_a_slope,
    floor_is_digital_silence,
    rule1_may_consult_container,
)
from flac_detective.analysis.spectrum import (
    FLOOR_MIN_CELLS,
    analyze_spectrum,
    edge_step_db,
    floor_above_edge_db,
)

SR = 44100
N = 2**17  # bins of ~0.34 Hz: every 250 Hz cell holds hundreds of bins
PCM = 1411.2  # what a 44.1/16/2 WAV or AIFF reads as container bitrate


def _spectrum(level_db):
    freq = np.fft.rfftfreq(N, 1 / SR)
    return freq, np.array([level_db(f) for f in freq], dtype=float)


def _beatport(at_hz: float = 16000.0, floor_db: float = -70.0):
    """The Beatport shape: a gentle 12 dB/kHz filter, then silence.

    ``at_hz`` is where detect_cutoff reports the edge — the point 30 dB under
    the reference — so the filter starts 2.5 kHz below it. Measured on the two
    files: 7.7-8.8 dB over 500 Hz at the edge, 25 dB over the next 2 kHz,
    -63 to -65 dB above.
    """
    start = at_hz - 2500.0

    def level(f):
        if f < start:
            return 0.0
        return max(-(f - start) / 1000.0 * 12.0, floor_db)

    return _spectrum(level)


def _rolloff(from_hz: float = 12000.0, db_per_khz: float = 6.0, floor_db: float = -44.0):
    """Issue #8's shape: -6 dB/kHz from 12 kHz, into an analogue floor."""
    return _spectrum(
        lambda f: 0.0 if f < from_hz else max(-(f - from_hz) / 1000.0 * db_per_khz, floor_db)
    )


def _wall(at_hz: float, depth_db: float = 40.0):
    return _spectrum(lambda f: 0.0 if f < at_hz else -depth_db)


class TestInstrument:
    def test_the_beatport_shape_is_soft_and_deep(self):
        freq, mag = _beatport()
        step = edge_step_db(freq, mag, 16000.0, SR)
        floor = floor_above_edge_db(freq, mag, 16000.0, SR)
        assert step < WALL_MIN_STEP_DB  # gate D alone would clear it
        assert floor <= DEEP_FLOOR_DB  # the depth gate does not

    def test_the_reporters_rolloff_is_soft_and_shallow(self):
        freq, mag = _rolloff()
        step = edge_step_db(freq, mag, 17250.0, SR)
        floor = floor_above_edge_db(freq, mag, 17250.0, SR)
        assert step < WALL_MIN_STEP_DB
        assert floor > DEEP_FLOOR_DB
        assert floor == pytest.approx(-44.0, abs=1.0)

    def test_a_codec_wall_reads_its_floor(self):
        freq, mag = _wall(16000.0, depth_db=70.0)
        assert floor_above_edge_db(freq, mag, 16000.0, SR) == pytest.approx(-70.0, abs=0.5)

    def test_the_band_starts_one_khz_above_the_edge(self):
        """The gap keeps the edge's own transition out of the reading."""
        freq, mag = _spectrum(lambda f: 0.0 if f < 16000 else (-20.0 if f < 16900 else -70.0))
        assert floor_above_edge_db(freq, mag, 16000.0, SR) == pytest.approx(-70.0, abs=0.5)

    def test_near_nyquist_is_nan_the_other_instrument_rules_there(self):
        """From ~19.9 kHz up fewer than FLOOR_MIN_CELLS cells fit: abstain."""
        freq, mag = _wall(20250.0, depth_db=70.0)
        assert math.isnan(floor_above_edge_db(freq, mag, 20250.0, SR))
        assert FLOOR_MIN_CELLS == 4

    def test_no_edge_is_nan_not_zero(self):
        freq, mag = _spectrum(lambda f: 0.0)
        assert math.isnan(floor_above_edge_db(freq, mag, 22050.0, SR))

    def test_bar_is_between_the_two_populations(self):
        """Deepest genuine edge below 19.5 kHz: -55.2; shallower Beatport file: -62.8."""
        assert -62.8 < DEEP_FLOOR_DB < -55.2


class TestTheStepYieldsToDepth:
    @staticmethod
    def _r1(**kw):
        defaults = {
            "cutoff_freq": 16000.0,
            "container_bitrate": 600.0,  # a FLAC of a 160 kbps source, inside its window
            "cutoff_std": float("nan"),
            "sample_rate": SR,
            "energy_ratio": 1e-7,
            "residual_floor_db": float("nan"),
            "edge_step_db": 7.7,
        }
        defaults.update(kw)
        (score, reasons), est = apply_rule_1_mp3_bitrate(**defaults)
        return score, est, reasons

    def test_a_soft_edge_over_silence_scores(self):
        score, est, reasons = self._r1(floor_above_db=-62.8)
        assert score == 50 and est == 160
        assert any("digital silence" in r for r in reasons)

    def test_a_soft_edge_over_an_analogue_floor_still_does_not(self):
        """Issue #8's files: step 4.5-6.2, floor -41 to -44. Unchanged."""
        score, est, reasons = self._r1(edge_step_db=6.2, floor_above_db=-44.4)
        assert score == 0 and est is None
        assert any("not a codec wall" in r for r in reasons)

    def test_an_unknown_floor_leaves_gate_d_alone(self):
        score, est, _ = self._r1(floor_above_db=float("nan"))
        assert score == 0 and est is None

    def test_the_predicate(self):
        assert floor_is_digital_silence(DEEP_FLOOR_DB)
        assert not floor_is_digital_silence(DEEP_FLOOR_DB + 0.1)
        assert not floor_is_digital_silence(float("nan"))
        assert not edge_is_a_slope(5.0, 16000.0, DEEP_FLOOR_DB)
        assert edge_is_a_slope(5.0, 16000.0, DEEP_FLOOR_DB + 0.1)
        assert edge_is_a_slope(5.0, 16000.0)  # default: unknown floor, 1.13.15 behaviour

    def test_the_gate_still_abstains_from_the_320_cell_up(self):
        assert not edge_is_a_slope(5.0, WALL_GATE_MAX_HZ, -70.0)
        assert not edge_is_a_slope(5.0, WALL_GATE_MAX_HZ, float("nan"))

    def test_depth_reads_the_zone_the_bar_was_derived_on(self):
        """From the 320 cell up the depth gate abstains, whatever the floor.

        The second after-pass moved two transcodes at exactly 19,500 Hz; the bar
        was derived on edges below that line and the genuine population above
        it was never measured against it. The near-Nyquist residual floor is
        the instrument up there.
        """
        assert floor_is_digital_silence(-70.0, WALL_GATE_MAX_HZ - 250.0)
        assert not floor_is_digital_silence(-70.0, WALL_GATE_MAX_HZ)
        assert not floor_is_digital_silence(-70.0, 20250.0)
        # In the 320 cell, a deep floor above the edge does not open the window.
        (score, _), est = apply_rule_1_mp3_bitrate(
            19500.0, 1200.0, float("nan"), SR, 1e-7, edge_step_db=30.0, floor_above_db=-70.0
        )
        assert score == 0 and est is None
        # One cell lower it does.
        (score, _), est = apply_rule_1_mp3_bitrate(
            19250.0, 1200.0, float("nan"), SR, 1e-7, edge_step_db=30.0, floor_above_db=-70.0
        )
        assert score == 50 and est is not None


class TestTheContainerWindowYieldsToDepth:
    """Below the 320 cell, a floor at or under the bar settles it without the window.

    The two Beatport files compress to 776 and 848 kbps (loud, dense masters)
    against a 160 kbps window of 450-650: the first after-pass of the registered
    repair left them AUTHENTIC on that alone. What is left above the edge is a
    fact about the audio, not about its loudness.
    """

    def test_the_beatport_files_score_at_their_real_flac_size(self):
        for container, step, floor in ((776.1, 7.7, -62.8), (848.4, 8.8, -65.1)):
            (score, reasons), est = apply_rule_1_mp3_bitrate(
                16000.0,
                container,
                float("nan"),
                SR,
                1e-7,
                residual_floor_db=float("nan"),
                edge_step_db=step,
                floor_above_db=floor,
            )
            assert score == 50 and est == 160, (container, step, floor)
            assert any("digital silence" in r for r in reasons)

    def test_outside_the_window_without_depth_is_unchanged(self):
        """A hard wall at 776 kbps, floor unknown or shallow: the window still decides."""
        for floor in (float("nan"), -50.0, DEEP_FLOOR_DB + 0.1):
            (score, _), est = apply_rule_1_mp3_bitrate(
                16000.0,
                776.1,
                float("nan"),
                SR,
                1e-7,
                residual_floor_db=float("nan"),
                edge_step_db=34.0,
                floor_above_db=floor,
            )
            assert score == 0 and est is None, floor

    def test_inside_the_window_is_unchanged_either_way(self):
        for floor in (float("nan"), -50.0, -70.0):
            (score, _), est = apply_rule_1_mp3_bitrate(
                16000.0,
                600.0,
                float("nan"),
                SR,
                1e-7,
                residual_floor_db=float("nan"),
                edge_step_db=34.0,
                floor_above_db=floor,
            )
            assert score == 50 and est == 160, floor

    def test_the_gate_never_removes_a_point(self):
        """Every combination the depth gate touches scores at least what 1.13.15 scored."""
        for container in (300.0, 600.0, 776.1, PCM):
            for step in (5.0, 34.0, float("nan")):
                (before, _), _ = apply_rule_1_mp3_bitrate(
                    16000.0,
                    container,
                    float("nan"),
                    SR,
                    1e-7,
                    residual_floor_db=float("nan"),
                    edge_step_db=step,
                )
                (after, _), _ = apply_rule_1_mp3_bitrate(
                    16000.0,
                    container,
                    float("nan"),
                    SR,
                    1e-7,
                    residual_floor_db=float("nan"),
                    edge_step_db=step,
                    floor_above_db=-70.0,
                )
                assert after >= before, (container, step)


class TestUncompressedContainerAcceptedOnDepth:
    """A WAV/AIFF at PCM level (a caller passing an on-disk bitrate) is accepted on depth."""

    @staticmethod
    def _r1(**kw):
        defaults = {
            "cutoff_freq": 16000.0,
            "container_bitrate": PCM,
            "cutoff_std": float("nan"),
            "sample_rate": SR,
            "energy_ratio": 1e-7,
            "residual_floor_db": float("nan"),  # no near-Nyquist reading at 16 kHz
        }
        defaults.update(kw)
        (score, reasons), est = apply_rule_1_mp3_bitrate(**defaults)
        return score, est, reasons

    def test_the_beatport_aiff_scores(self):
        """Soft edge AND uncompressed container: both locks open on depth."""
        score, est, reasons = self._r1(edge_step_db=7.7, floor_above_db=-62.8)
        assert score == 50 and est == 160
        assert any("digital silence" in r for r in reasons)

    def test_a_hard_wall_on_a_wav_scores_when_deep(self):
        """The v1.12 G2 mechanism: a 16 kHz wall on PCM had no depth reading."""
        score, est, _ = self._r1(edge_step_db=34.0, floor_above_db=-66.0)
        assert score == 50 and est == 160

    def test_a_hard_wall_on_a_wav_without_a_reading_is_unchanged(self):
        """An unknown floor keeps 1.13.15 exactly: uninformative container, no proof, no score."""
        score, est, _ = self._r1(edge_step_db=34.0, floor_above_db=float("nan"))
        assert score == 0 and est is None

    def test_a_shallow_floor_on_a_wav_does_not_open_the_container(self):
        score, est, _ = self._r1(edge_step_db=34.0, floor_above_db=-50.0)
        assert score == 0 and est is None

    def test_the_near_nyquist_instrument_still_opens_it(self):
        """The existing acceptance path is untouched."""
        (score, _), est = apply_rule_1_mp3_bitrate(
            19250.0, PCM, float("nan"), SR, 1e-7, residual_floor_db=-60.0, edge_step_db=30.0
        )
        assert score == 50 and est is not None


class TestMirror:
    """The hoisted gate must admit exactly what the rule now scores."""

    @pytest.mark.parametrize(
        "step", [5.0, WALL_MIN_STEP_DB - 0.1, WALL_MIN_STEP_DB, 34.0, float("nan")]
    )
    @pytest.mark.parametrize(
        "floor", [-70.0, DEEP_FLOOR_DB, DEEP_FLOOR_DB + 0.1, -40.0, float("nan")]
    )
    def test_mirror_and_rule_agree_on_a_flac(self, step, floor):
        (score, _), _ = apply_rule_1_mp3_bitrate(
            16000.0,
            600.0,
            float("nan"),
            SR,
            1e-7,
            residual_floor_db=float("nan"),
            edge_step_db=step,
            floor_above_db=floor,
        )
        assert rule1_may_consult_container(16000.0, SR, float("nan"), step, floor) == (score == 50)

    def test_mirror_admits_the_beatport_case(self):
        assert rule1_may_consult_container(16000.0, SR, float("nan"), 7.7, -62.8)
        assert not rule1_may_consult_container(16000.0, SR, float("nan"), 7.7, -44.4)


def _shaped_noise(path, gain_db, seconds: int = 20, seed: int = 7):
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


class TestAnalyzeSpectrumCarriesTheFloor:
    def test_six_values_and_the_floor_of_a_beatport_shape(self, tmp_path):
        path = _shaped_noise(
            tmp_path / "beatport.flac",
            lambda f: 0.0 if f < 13500 else max(-(f - 13500) / 1000.0 * 12.0, -90.0),
        )
        cutoff, energy, std, resid, step, floor = analyze_spectrum(path, 30.0)
        assert 15500.0 <= cutoff <= 17000.0  # 30 dB down is reached at 16 kHz
        assert step < WALL_MIN_STEP_DB  # gate D alone would clear it
        assert not math.isnan(floor)
        assert floor <= DEEP_FLOOR_DB

    def test_the_floor_of_a_rolloff_into_noise(self, tmp_path):
        path = _shaped_noise(
            tmp_path / "rolloff.flac",
            lambda f: 0.0 if f < 12000 else max(-(f - 12000) / 1000.0 * 6.0, -44.0),
        )
        cutoff, energy, std, resid, step, floor = analyze_spectrum(path, 30.0)
        assert 16000.0 <= cutoff <= 18000.0
        assert floor > DEEP_FLOOR_DB
