"""Rule 15 — the stereo-image witness, and the gate without which it is dangerous.

Rule 15 reads what joint stereo leaves behind: above its coupling frequency the
encoder quantises the side channel toward zero, leaving long contiguous holes there
while the mid stays alive. It is the strongest independent observable this engine
holds — AUC 0.96 on Opus, Vorbis and mp3_320 — and it is also the one that can be
manufactured out of nothing.

**Mono material has no side channel.** Every high bin is then trivially dead and the
statistic reads maximal, on a file that has been through no encoder at all. Provir
came within a few units of convicting a legitimate mono master exactly that way.
Twenty of this project's own 258 genuine files are mono-gated, so it is not a
hypothetical.

The gate must therefore produce SILENCE rather than a low score, because a low
score is still an opinion about a file the statistic cannot see.
"""

from __future__ import annotations

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
)
from flac_detective.analysis.new_scoring.evidence import (
    POINTLESS_WITNESS_RULES,
    evidence_families,
)
from flac_detective.analysis.new_scoring.rules.stereo_seam import (
    MIN_CUTOFF_HZ,
    RUN_BAR,
    apply_rule_15_stereo_seam,
)
from flac_detective.analysis.new_scoring.stereo_image import MONO_GATE, side_dead_run
from flac_detective.analysis.new_scoring.verdict import determine_verdict

RATE = 44100


def _live_stereo(seconds: float = 8.0, seed: int = 11) -> np.ndarray:
    """Independent channels: a real stereo image, side channel alive everywhere."""
    rng = np.random.default_rng(seed)
    n = int(RATE * seconds)
    return np.stack([rng.normal(0, 0.25, n), rng.normal(0, 0.25, n)], axis=1).astype(np.float32)


def _coupled_above(lo_hz: float, hi_hz: float, seconds: float = 8.0, seed: int = 11) -> np.ndarray:
    """Live stereo with the side channel zeroed between ``lo_hz`` and ``hi_hz``.

    BOUNDED on purpose. Killing the side all the way to Nyquist produces a run that
    touches the top bin, which the interior rule discards as a lowpass edge —
    correctly, and a control that does it tests the exclusion instead of the
    statistic. Real transcodes leave dither at the very top, so their runs are
    interior.
    """
    data = _live_stereo(seconds, seed)
    mid = (data[:, 0] + data[:, 1]) / 2.0
    side = data[:, 0] - data[:, 1]
    spectrum = np.fft.rfft(side)
    freqs = np.fft.rfftfreq(len(side), 1.0 / RATE)
    spectrum[(freqs >= lo_hz) & (freqs < hi_hz)] = 0.0
    side = np.fft.irfft(spectrum, len(side))
    return np.stack([mid + side / 2.0, mid - side / 2.0], axis=1).astype(np.float32)


def _mono(seconds: float = 8.0, seed: int = 11) -> np.ndarray:
    """Identical channels — no stereo image at all."""
    data = _live_stereo(seconds, seed)
    data[:, 1] = data[:, 0]
    return data


class TestTheStatistic:
    def test_live_stereo_reads_low(self) -> None:
        """A side channel that is alive everywhere has no dead runs."""
        run, ratio = side_dead_run(_live_stereo(), RATE)
        assert np.isfinite(run)
        assert ratio > MONO_GATE
        assert run < RUN_BAR, f"live stereo read {run:.2f}, at or above the bar"

    def test_a_coupled_band_is_found(self) -> None:
        """The artefact, imposed on the side channel, is read."""
        run, _ratio = side_dead_run(_coupled_above(12000.0, 18000.0), RATE)
        assert np.isfinite(run)
        assert run >= RUN_BAR, f"a killed side band read only {run:.2f}"

    def test_mono_abstains_rather_than_scoring_low(self) -> None:
        """The gate that stops this convicting masters for having no stereo image.

        NaN, not zero. A file the statistic cannot see must produce silence — a low
        score would still be an opinion, and the next person to build a rule on
        "low means innocent" would be building on nothing.
        """
        run, ratio = side_dead_run(_mono(), RATE)
        assert ratio < MONO_GATE, f"mono material read side/mid {ratio:.2e}"
        assert not np.isfinite(run), (
            "mono material produced a number. Every high bin of a mono file is "
            "trivially dead, so that number is manufactured — Provir came within a "
            "few units of convicting a legitimate mono master this way."
        )

    def test_single_channel_files_abstain(self) -> None:
        """A genuinely 1-channel file has no side channel to read."""
        run, _ratio = side_dead_run(np.zeros((RATE * 4, 1), dtype=np.float32), RATE)
        assert not np.isfinite(run)


class TestTheRuleNeverScores:
    @pytest.mark.parametrize("band", [(12000.0, 18000.0), (14000.0, 20000.0)])
    def test_zero_points_whatever_it_reads(self, band) -> None:
        score, _reasons, details = apply_rule_15_stereo_seam(
            "x.flac", 20000.0, audio_data=_coupled_above(*band), sample_rate=RATE
        )
        assert score == 0, (
            f"Rule 15 returned {score} points. Like Rule 14 it must return zero: a "
            "family that both witnesses AND scores pushes mid-scoring genuine "
            "recordings past the conviction bar and then corroborates them."
        )

    def test_mono_produces_no_witness(self) -> None:
        _score, _reasons, details = apply_rule_15_stereo_seam(
            "x.flac", 20000.0, audio_data=_mono(), sample_rate=RATE
        )
        assert details["stereo_witness"] is False

    def test_a_lone_witness_cannot_convict(self) -> None:
        verdict, _ = determine_verdict(140, families={"stereo"})
        assert verdict != "FAKE_CERTAIN"

    def test_it_cannot_carry_a_file_to_the_points_bar(self) -> None:
        below = CONVICTION_MIN_SCORE - 1
        families = evidence_families({"Rule1MP3Bitrate": below}, witnesses={"stereo"})
        assert len(families) >= CONVICTION_MIN_FAMILIES
        verdict, _ = determine_verdict(below, families)
        assert verdict != "FAKE_CERTAIN"

    def test_it_is_declared_as_a_pointless_witness(self) -> None:
        assert POINTLESS_WITNESS_RULES.get("Rule15StereoSeam") == "stereo"


class TestGates:
    def test_band_limited_files_are_left_alone(self) -> None:
        _score, _reasons, details = apply_rule_15_stereo_seam(
            "x.flac",
            MIN_CUTOFF_HZ - 1000.0,
            audio_data=_coupled_above(12000.0, 18000.0),
            sample_rate=RATE,
        )
        assert details["stereo_witness"] is False

    def test_no_audio_means_no_witness(self) -> None:
        _score, _reasons, details = apply_rule_15_stereo_seam("x.flac", 20000.0)
        assert details["stereo_witness"] is False


class TestLevelInvariance:
    """The absolute threshold is guarded, so gain must not decide the verdict.

    Provir measured their version reading 16 / 54 / 137 / 283 for identical audio at
    0 / -12 / -24 / -36 dB, with six files out of six changing verdict on gain
    alone. The floor-guarded restore in ``stereo_image`` exists for that, and this
    is what checks it actually works.
    """

    @pytest.mark.parametrize("gain_db", [-12.0, -24.0, -36.0])
    def test_gain_does_not_flip_the_witness(self, gain_db: float) -> None:
        audio = _coupled_above(12000.0, 18000.0)
        loud, _ = side_dead_run(audio, RATE)
        quiet, _ = side_dead_run((audio * 10 ** (gain_db / 20.0)).astype(np.float32), RATE)
        assert np.isfinite(loud) and np.isfinite(quiet)
        assert (loud >= RUN_BAR) == (quiet >= RUN_BAR), (
            f"the witness flipped on gain alone: {loud:.2f} at 0 dB against "
            f"{quiet:.2f} at {gain_db:.0f} dB. The floor-guarded restore is there "
            "precisely so an absolute threshold does not become a level meter."
        )
