"""The low wall: a codec wall under the 10-14 kHz reference band (v1.17.0).

Under ~64 kbps an encoder's low-pass sits at 3-11 kHz. detect_cutoff measures
against the 10-14 kHz reference and scans from 14 kHz, so on those files it
compares the codec's floor with itself, finds nothing, and reports the top of
the band; Rule 8 then granted -50 to a file whose music stops at 4 kHz. These
tests pin the instrument (``spectrum.low_wall_hz``), the invariant that makes a
cutoff under 14 kHz unambiguous (``is_low_wall_reading``), what Rules 2 and 8
do with it, and the path through ``analyze_spectrum``. Every test that pins the
repaired behaviour fails on the 1.16.0 tree (``low_wall_hz`` does not exist
there, and ``analyze_spectrum`` reports the top of the band).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import SCORE_WARNING
from flac_detective.analysis.new_scoring.rules.spectral import (
    apply_rule_1_mp3_bitrate,
    apply_rule_2_cutoff,
    apply_rule_8_nyquist_exception,
    rule1_may_consult_container,
)
from flac_detective.analysis.spectrum import (
    LOW_WALL_DEPTH_DB,
    LOW_WALL_STEP_DB,
    analyze_spectrum,
    detect_cutoff,
    is_low_wall_reading,
    low_wall_hz,
)

SR = 44100
N = 2**17


def _spectrum(level_db, sr: int = SR):
    freq = np.fft.rfftfreq(N, 1 / sr)
    return freq, np.array([level_db(f) for f in freq], dtype=float)


def _codec(at_hz: float, depth_db: float = 60.0):
    return _spectrum(lambda f: 0.0 if f < at_hz else -depth_db)


class TestInstrument:
    @pytest.mark.parametrize("at_hz", [3000.0, 5000.0, 7500.0, 11000.0, 13500.0])
    def test_a_codec_wall_is_found_where_it_is(self, at_hz):
        freq, mag = _codec(at_hz)
        assert low_wall_hz(freq, mag, SR) == at_hz

    def test_a_dark_recording_declines_and_is_not_a_wall(self):
        # The 1920s 78 rpm transfer's shape: ~10 dB/kHz from 3 kHz into its floor.
        freq, mag = _spectrum(lambda f: 0.0 if f < 3000 else max(-(f - 3000) / 100.0, -60.0))
        assert math.isnan(low_wall_hz(freq, mag, SR))

    def test_a_full_band_spectrum_has_no_low_wall(self):
        freq, mag = _spectrum(lambda f: -f / 2000.0)
        assert math.isnan(low_wall_hz(freq, mag, SR))

    def test_a_dip_that_comes_back_is_not_a_wall(self):
        # A sharp 40 dB dip at 3-4 kHz, then the music returns: step yes, depth no.
        freq, mag = _spectrum(lambda f: -40.0 if 3000 <= f < 4000 else 0.0)
        assert math.isnan(low_wall_hz(freq, mag, SR))

    def test_a_shallow_wall_is_not_enough(self):
        freq, mag = _codec(6000.0, depth_db=LOW_WALL_DEPTH_DB - 5)
        assert math.isnan(low_wall_hz(freq, mag, SR))

    def test_a_soft_edge_is_not_enough(self):
        # Deep, but it takes 3 kHz to get there: under the step bar everywhere.
        freq, mag = _spectrum(lambda f: 0.0 if f < 5000 else max(-(f - 5000) / 1000.0 * 20, -60.0))
        per_500 = 20 * 0.5
        assert per_500 < LOW_WALL_STEP_DB
        assert math.isnan(low_wall_hz(freq, mag, SR))

    def test_the_depth_stops_at_16_khz_whatever_the_rate(self):
        # A 96 kHz field recording: a tonal dip at 3.5 kHz, music on to 6 kHz,
        # then a gentle 18 dB/kHz decline into the floor, and nothing above.
        # Read to Nyquist, the empty band puts the 90th percentile of "above"
        # deep in the decline and the dip reads as a wall; read to 16 kHz the
        # music after the dip is still in the top tenth and it is a dip.
        sr = 96000

        def level(f):
            if 3500 <= f < 4000:
                return -45.0
            if f < 6000:
                return -20.0 - (f - 4000) / 1000.0 * 2
            return max(-24.0 - (f - 6000) / 1000.0 * 18, -120.0)

        freq, mag = _spectrum(level, sr)
        assert math.isnan(low_wall_hz(freq, mag, sr))


class TestTheReadingIsUnambiguous:
    @pytest.mark.parametrize("at_hz", [3000.0, 6000.0, 9000.0, 12000.0, 13750.0])
    def test_detect_cutoff_never_answers_under_14_khz(self, at_hz):
        freq, mag = _codec(at_hz)
        assert detect_cutoff(freq, mag, SR) >= 14000.0

    @pytest.mark.parametrize(
        "cutoff, expected",
        [
            (0.0, False),
            (1999.0, False),
            (2000.0, True),
            (13999.0, True),
            (14000.0, False),
            (16000.0, False),
            (22050.0, False),
        ],
    )
    def test_is_low_wall_reading(self, cutoff, expected):
        assert is_low_wall_reading(cutoff) is expected


class TestRules:
    def test_rule_2_names_a_low_wall_and_keeps_it_under_warning(self):
        # Restored 78 rpm reissues are low-passed as steeply as a 32 kbps codec
        # at the same 3-5 kHz: the wall is reported, it does not signal alone.
        score, reasons = apply_rule_2_cutoff(4000.0, SR)
        assert score == 30
        assert score < SCORE_WARNING
        assert "stops at 4000 Hz behind a wall" in reasons[0]

    def test_rule_2_keeps_its_ramp_above_14_khz(self):
        score, _ = apply_rule_2_cutoff(16000.0, SR)
        assert score == 20  # (20000 - 16000) / 200

    def test_rule_2_does_not_score_an_analysis_failure_as_a_wall(self):
        score, _ = apply_rule_2_cutoff(0.0, SR)
        assert score == 30  # the old ramp's cap, unchanged

    def test_rule_1_does_not_read_a_low_wall_as_an_mp3_cell(self):
        # The amendment: an 1890s gramophone at 11,750 Hz went SUSPICIOUS 80
        # through the never-calibrated part of the 128 kbps cell under 14 kHz.
        (score, reasons), bitrate = apply_rule_1_mp3_bitrate(11750.0, 480.0, float("nan"), SR)
        assert score == 0 and bitrate is None
        assert not rule1_may_consult_container(11750.0, SR)

    def test_rule_1_still_reads_the_128_cell_above_14_khz(self):
        (score, _), bitrate = apply_rule_1_mp3_bitrate(15000.0, 480.0, float("nan"), SR)
        assert score == 50 and bitrate == 128

    def test_rule_8_does_not_protect_a_low_wall(self):
        score, reasons = apply_rule_8_nyquist_exception(4000.0, SR, None, None)
        assert score == 0
        assert not reasons


def _shaped_noise(path, gain_db, seconds: int = 20, seed: int = 11):
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


class TestAnalyzeSpectrum:
    def test_a_low_rate_shape_reads_its_wall(self, tmp_path):
        path = _shaped_noise(tmp_path / "aac32.flac", lambda f: 0.0 if f < 5000 else -90.0)
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert 4750.0 <= cutoff <= 5250.0
        assert is_low_wall_reading(cutoff)

    def test_a_dark_recording_keeps_the_top_of_the_band(self, tmp_path):
        path = _shaped_noise(
            tmp_path / "dark.flac", lambda f: 0.0 if f < 3000 else max(-(f - 3000) / 100.0, -60.0)
        )
        cutoff = analyze_spectrum(path, 30.0)[0]
        assert not is_low_wall_reading(cutoff)
