"""The three Rule 1 admission gates, repaired in v1.12 and pinned here.

Each gate was calibrated on direct-lab material and measured silencing the rule
on the owner-attested wild population (ml/wild53_cliff.py mechanisms a-c;
ml/r1_gates_repricing.py G-series, registered before measurement). Every test
below encodes the repaired behaviour and was verified CAPABLE OF FAILING by
running it against the pre-repair rule.
"""

from __future__ import annotations

import pytest

from flac_detective.analysis.new_scoring.rules.spectral import (
    apply_rule_1_mp3_bitrate,
)


def _r1(**kw):
    defaults = {
        "cutoff_freq": 20250.0,
        "container_bitrate": 900.0,
        "cutoff_std": 0.0,
        "sample_rate": 44100,
        "energy_ratio": 1e-5,
        "residual_floor_db": -60.0,
    }
    defaults.update(kw)
    (score, _reasons), est = apply_rule_1_mp3_bitrate(**defaults)
    return score, est


class TestGateA_VarianceVsGrid:
    def test_one_cell_wander_is_admitted(self):
        """A stable wall near a cell boundary reads std ~118 and must score."""
        score, est = _r1(cutoff_std=117.9)
        assert score == 50 and est == 320

    def test_above_one_cell_bound_still_exits(self):
        score, _ = _r1(cutoff_std=131.0)
        assert score == 0

    def test_two_cell_wander_still_exits(self):
        score, _ = _r1(cutoff_std=235.7)
        assert score == 0


class TestGateB_20kExactDecidesOnDepth:
    def test_deep_wall_at_20000_scores_despite_hf_energy(self):
        """Press noise guarantees energy > 1e-6 on wild files; depth decides."""
        score, est = _r1(
            cutoff_freq=20000.0, energy_ratio=3.4e-5, residual_floor_db=-63.8, cutoff_std=0.0
        )
        assert score == 50 and est == 320

    def test_shallow_floor_at_20000_keeps_the_skip(self):
        score, _ = _r1(cutoff_freq=20000.0, energy_ratio=3.4e-5, residual_floor_db=-40.0)
        assert score == 0

    def test_nan_floor_at_20000_keeps_the_legacy_skip(self):
        score, _ = _r1(cutoff_freq=20000.0, energy_ratio=3.4e-5, residual_floor_db=float("nan"))
        assert score == 0


class TestGateCPrime_PCMContainerBypassRequiresDepth:
    def test_wav_at_pcm_level_scores_when_the_wall_proves_depth(self):
        """PCM-level container bitrate is format, not history.

        The bypass demands the proof the container can no longer give.
        """
        score, est = _r1(container_bitrate=1411.0, residual_floor_db=-60.0)
        assert score == 50 and est == 320

    def test_wav_without_depth_reading_is_refused(self):
        """G1-ter's lesson: no depth proof, no score.

        For sub-320 cells the container window was the only guard, so an
        uninformative container plus no depth reading must not score.
        """
        score, _ = _r1(container_bitrate=1411.0, residual_floor_db=float("nan"))
        assert score == 0

    def test_wav_with_shallow_floor_is_refused(self):
        score, _ = _r1(container_bitrate=1411.0, residual_floor_db=-40.0)
        assert score == 0

    def test_flac_outside_window_still_refused(self):
        """FLAC windows unchanged: dense material above 1050 but below PCM."""
        score, _ = _r1(container_bitrate=1200.0)
        assert score == 0

    def test_flac_inside_window_still_scores(self):
        score, est = _r1(container_bitrate=900.0)
        assert score == 50 and est == 320

    def test_flac_inside_window_needs_no_depth_reading(self):
        """The informative-container path is untouched.

        NaN residual keeps the legacy behaviour for in-window FLAC below the
        320 branch.
        """
        (score, _), est = apply_rule_1_mp3_bitrate(
            cutoff_freq=19750.0,
            container_bitrate=900.0,
            cutoff_std=0.0,
            sample_rate=44100,
            energy_ratio=1e-5,
            residual_floor_db=float("nan"),
        )
        assert score == 50 and est == 320


class TestGateD_WavDispatch:
    def test_rule1_runs_on_uncompressed_input(self, tmp_path):
        """The dispatcher must not remove Rule 1 for WAV input.

        Gate C-prime handles the uninformative container inside the rule.
        Before v1.12 every WAV was structurally beyond the rule's reach;
        found by G4's first end-to-end firing.
        """
        import numpy as np
        import soundfile as sf

        from flac_detective.analysis.analyzer import FLACAnalyzer

        rng = np.random.default_rng(20260821)
        wav = tmp_path / "probe.wav"
        sf.write(str(wav), 0.1 * rng.standard_normal((44100 * 12, 2)), 44100, subtype="PCM_16")
        result = FLACAnalyzer(deep=False).analyze_file(str(wav))
        assert (
            "Rule1MP3Bitrate" in result["score_breakdown"]
        ), "Rule 1 absent from the WAV path breakdown — gate D regressed"


class TestUntouchedGuards:
    """The gates that were NOT part of the campaign must not have moved."""

    def test_near_nyquist_exit_unmoved(self):
        score, _ = _r1(cutoff_freq=21000.0)
        assert score == 0  # >= 0.95 x Nyquist

    def test_shallow_residual_320_still_dropped(self):
        score, _ = _r1(residual_floor_db=-40.0)
        assert score == 0  # authentic band-limited, signature dropped

    @pytest.mark.parametrize("cutoff", [16000.0, 17500.0, 19750.0])
    def test_lower_bitrate_cells_unaffected(self, cutoff):
        (score, _), est = apply_rule_1_mp3_bitrate(
            cutoff_freq=cutoff,
            container_bitrate=600.0,
            cutoff_std=0.0,
            sample_rate=44100,
            energy_ratio=1e-5,
            residual_floor_db=float("nan"),
        )
        assert (score == 50) == (est is not None and est != 0)
