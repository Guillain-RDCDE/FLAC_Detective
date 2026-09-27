"""Rule 16 — the MP3 granule grid, read back through the Layer III analysis filterbank.

These tests pin the instrument (``mp3_grid``) on a real MP3 round trip, the
witness contract of the rule (zero points, a family, silence when it cannot
measure), and the calculator's gate that runs it only where it can change a
verdict. Every test fails on the 1.18.0 tree, where neither module exists.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import soundfile as sf

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
)
from flac_detective.analysis.new_scoring.evidence import (
    POINTLESS_WITNESS_RULES,
    evidence_families,
)
from flac_detective.analysis.new_scoring.mp3_grid import WINDOW, grid_peak_ratio
from flac_detective.analysis.new_scoring.rules.mp3_grid import GRID_BAR, apply_rule_16_mp3_grid
from flac_detective.analysis.new_scoring.verdict import determine_verdict

SR = 44100
_MP3 = "MP3" in sf.available_formats()


def _music_like(seconds: float = 20.0, seed: int = 3) -> np.ndarray:
    """Pink-ish stereo noise with a slow envelope: something an encoder has to work on."""
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / np.sqrt(np.maximum(f, 50) / 50)
    x = np.fft.irfft(spec, n)
    x = x / np.abs(x).max() * 0.5
    x *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.7 * np.arange(n) / SR))
    return np.stack([x, 0.9 * np.roll(x, 37)], axis=1).astype(np.float32)


class TestTheWindow:
    def test_the_iso_window_peak_and_symmetry(self):
        # C[256] = 0.035780907 in ISO/IEC 11172-3; C[512 - i] = -C[i] off the 64-sample blocks.
        assert WINDOW[256] == pytest.approx(0.035780907, abs=1e-6)
        assert WINDOW[257] == pytest.approx(-WINDOW[255])
        assert WINDOW[512 - 64] == pytest.approx(WINDOW[64])


class TestTheInstrument:
    def test_uncompressed_audio_has_no_preferred_alignment(self):
        ratio, _ = grid_peak_ratio(_music_like(), SR)
        assert ratio < GRID_BAR

    @pytest.mark.skipif(not _MP3, reason="libsndfile built without MP3 support")
    def test_an_mp3_round_trip_shows_its_grid(self, tmp_path):
        path = tmp_path / "x.mp3"
        sf.write(str(path), _music_like(), SR, format="MP3")
        decoded, rate = sf.read(str(path), always_2d=True)
        ratio, offset = grid_peak_ratio(decoded, rate)
        assert ratio >= GRID_BAR
        assert 0 <= offset < 576

    def test_too_short_to_read_is_nan_not_a_number(self):
        ratio, offset = grid_peak_ratio(np.zeros((1000, 2)), SR)
        assert math.isnan(ratio) and offset == -1


class TestTheWitness:
    @pytest.mark.skipif(not _MP3, reason="libsndfile built without MP3 support")
    def test_zero_points_and_a_witness(self, tmp_path):
        path = tmp_path / "x.mp3"
        sf.write(str(path), _music_like(), SR, format="MP3")
        decoded, rate = sf.read(str(path), always_2d=True)
        score, reasons, details = apply_rule_16_mp3_grid(decoded, rate)
        assert score == 0
        assert details["mp3_witness"] is True
        assert "no points" in reasons[0]

    def test_no_audio_no_witness(self):
        score, reasons, details = apply_rule_16_mp3_grid(None, None)
        assert score == 0 and not reasons and details["mp3_witness"] is False

    def test_it_is_a_declared_pointless_witness(self):
        assert POINTLESS_WITNESS_RULES.get("Rule16MP3Grid") == "mp3grid"

    def test_a_lone_witness_cannot_convict(self):
        verdict, _ = determine_verdict(140, families={"mp3grid"})
        assert verdict != "FAKE_CERTAIN"

    def test_it_completes_a_corroboration_at_the_bar(self):
        families = evidence_families(
            {"Rule1MP3Bitrate": 50, "Rule2Cutoff": 10}, witnesses={"mp3grid"}
        )
        assert len(families) >= CONVICTION_MIN_FAMILIES
        verdict, _ = determine_verdict(CONVICTION_MIN_SCORE, families)
        assert verdict == "FAKE_CERTAIN"


class TestItRunsOnlyWhereItCanDecide:
    def _ctx(self, score: int, rule_scores: dict, witnesses=()):
        from pathlib import Path

        from flac_detective.analysis.new_scoring.models import (
            AudioMetadata,
            BitrateMetrics,
            ScoringContext,
        )

        ctx = ScoringContext(
            filepath=Path("x.flac"),
            audio_meta=AudioMetadata(sample_rate=SR, bit_depth=16, channels=2, duration=20.0),
            bitrate_metrics=BitrateMetrics(
                real_bitrate=600.0, apparent_bitrate=1411, variance=None
            ),
            cutoff_freq=16000.0,
        )
        ctx.current_score = score
        ctx.rule_scores.update(rule_scores)
        ctx.witness_families.update(witnesses)
        ctx.audio_data = _music_like(5.0)
        ctx.loaded_sample_rate = SR
        return ctx

    def _ran(self, ctx) -> bool:
        from flac_detective.analysis.new_scoring import calculator

        before = ctx.mp3_grid_ratio
        calculator._run_rule_16_if_decisive(ctx)
        return not (math.isnan(ctx.mp3_grid_ratio) and math.isnan(before))

    def test_skipped_under_the_conviction_bar(self):
        assert not self._ran(self._ctx(40, {"Rule1MP3Bitrate": 40}))

    def test_skipped_when_already_corroborated(self):
        assert not self._ran(self._ctx(80, {"Rule1MP3Bitrate": 50}, witnesses={"stereo"}))

    def test_runs_on_a_single_family_file_at_the_bar(self):
        assert self._ran(self._ctx(60, {"Rule1MP3Bitrate": 50, "Rule2Cutoff": 10}))
