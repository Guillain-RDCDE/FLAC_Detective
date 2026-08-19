"""Rule 14 — the witness that must never score, and never convict alone.

Rule 14 is the first rule in this engine that declares an evidence family while
contributing zero points, and both halves of that sentence are load-bearing.

The zero is not stylistic. Awarding the family 25 points — just enough to clear
``MIN_FAMILY_CONTRIBUTION`` and count as a witness — was measured before it was
written, and produced **three new false convictions on 258 genuine files**: real
recordings sitting at 52, 38 and 31 spectral points were pushed past
``CONVICTION_MIN_SCORE`` by the appended points and then convicted by their own
new second family. Wiring it at zero measured 0 across the same corpus, at every
threshold from 0.55 to 0.708.

So the properties worth pinning are structural, not statistical:

* the rule contributes nothing to the score, whatever it reads;
* it can complete a corroboration, but cannot create the conditions for one;
* it abstains rather than guessing when it cannot see.
"""

from __future__ import annotations

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
    SCORE_WARNING,
)
from flac_detective.analysis.new_scoring.evidence import (
    POINTLESS_WITNESS_RULES,
    evidence_families,
)
from flac_detective.analysis.new_scoring.rules.temporal_seam import (
    MIN_CUTOFF_HZ,
    SEAM_BAR,
    apply_rule_14_temporal_seam,
)
from flac_detective.analysis.new_scoring.temporal import temporal_seam
from flac_detective.analysis.new_scoring.verdict import determine_verdict


def _restless(rate: int = 44100, seconds: float = 6.0, seed: int = 7) -> np.ndarray:
    """Broadband noise: every bin varies over time, so no seam exists."""
    rng = np.random.default_rng(seed)
    return rng.normal(0, 0.2, int(rate * seconds)).astype(np.float32)


def _stationary_band(
    lo_hz: float, hi_hz: float, rate: int = 44100, seconds: float = 6.0, seed: int = 7
) -> np.ndarray:
    """Restless everywhere except a steady tone-bed between ``lo_hz`` and ``hi_hz``.

    The artefact in its purest form: energy is still present in that band, so no
    cutoff rule would see anything, but it has stopped moving.

    Two things had to be got right and both were wrong first:

    * Flattening the magnitudes of a full-length FFT and keeping random phases just
      produces noise again, whose STFT magnitudes fluctuate frame to frame exactly
      like the material it was meant to contrast with. It read 0.12.
    * A stationary band running to Nyquist creates a second, larger seam where the
      spectrum ends, and the statistic correctly reported that one instead. Hence a
      BOUNDED band with restless content above it, which is also what a codec
      actually leaves.
    """
    rng = np.random.default_rng(seed)
    n = int(rate * seconds)
    t = np.arange(n) / rate

    # NOTCH the noise out of the band first. Adding a comb on top of noise leaves
    # the noise dominating there, so the variance barely falls and the whole
    # construction reads ~0.3 — which is what the previous version did.
    spectrum = np.fft.rfft(rng.normal(0, 1, n))
    freqs = np.fft.rfftfreq(n, 1.0 / rate)
    spectrum[(freqs >= lo_hz) & (freqs < hi_hz)] = 0.0
    noise = np.fft.irfft(spectrum, n)
    noise /= np.abs(noise).max() + 1e-9

    # Steady partials filling the gap: constant amplitude for the whole excerpt, so
    # every STFT frame sees the same magnitudes there.
    comb = np.zeros(n)
    for freq in np.arange(lo_hz, hi_hz, 60.0):
        comb += np.sin(2 * np.pi * freq * t + rng.uniform(0, 2 * np.pi))
    comb /= np.abs(comb).max() + 1e-9

    out = (0.7 * noise + 0.3 * comb).astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def _stationary_above(
    cut_hz: float, rate: int = 44100, seconds: float = 6.0, seed: int = 7
) -> np.ndarray:
    """A stationary band starting at ``cut_hz``, 3 kHz wide."""
    return _stationary_band(cut_hz, min(cut_hz + 3000.0, rate / 2 - 60.0), rate, seconds, seed)


class TestTheStatistic:
    """The observable itself, before any scoring is attached to it."""

    def test_restless_audio_reads_low(self) -> None:
        """Noise varies everywhere, so there is no frequency where it stops."""
        score, _hz = temporal_seam(_restless(), 44100)
        assert np.isfinite(score)
        assert score < SEAM_BAR, (
            f"broadband noise read {score:.2f}, at or above the bar. Every bin of it "
            "varies over time, so a seam reader that fires here is reading something "
            "other than what it claims."
        )

    def test_a_stationary_top_band_is_found(self) -> None:
        """The artefact, imposed at a known frequency, is detected there."""
        score, hz = temporal_seam(_stationary_above(15000.0), 44100)
        assert np.isfinite(score)
        assert score >= SEAM_BAR, f"imposed stationary band read only {score:.2f}"
        assert (
            abs(hz - 15000.0) < 2500.0
        ), f"seam located at {hz:.0f} Hz for a band made stationary from 15000 Hz"

    def test_too_short_abstains(self) -> None:
        """A file that cannot carry the statistic gets no opinion, not a guess."""
        score, hz = temporal_seam(np.zeros(2048, dtype=np.float32), 44100)
        assert not np.isfinite(score) and not np.isfinite(hz)


class TestTheRuleNeverScores:
    """The property the whole design rests on."""

    @pytest.mark.parametrize("cut", [12000.0, 15000.0, 18000.0])
    def test_zero_points_whatever_it_reads(self, cut: float) -> None:
        """Firing or not, the contribution is zero."""
        audio = _stationary_above(cut)
        score, _reasons, details = apply_rule_14_temporal_seam(
            "x.flac", 20000.0, audio_data=audio, sample_rate=44100
        )
        assert score == 0, (
            f"Rule 14 returned {score} points. It must return zero: 25 points was "
            "measured and produced three false convictions on 258 genuine files, "
            "because the points pushed mid-scoring real recordings past the "
            "conviction bar and then corroborated them."
        )
        assert isinstance(details.get("temporal_witness"), bool)

    def test_a_lone_witness_cannot_convict(self) -> None:
        """One family is not two, whatever the score says."""
        verdict, _ = determine_verdict(140, families={"temporal"})
        assert verdict != "FAKE_CERTAIN"

    def test_the_witness_cannot_carry_a_file_to_the_points_bar(self) -> None:
        """Arithmetic: a zero-point family cannot move any file toward conviction.

        This is what makes the ~8 % genuine fire rate harmless. On a real recording
        the witness has nothing to corroborate, because nothing else got the file
        past ``CONVICTION_MIN_SCORE`` — and Rule 14 cannot help it get there.
        """
        below = CONVICTION_MIN_SCORE - 1
        families = evidence_families({"Rule1MP3Bitrate": below}, witnesses={"temporal"})
        assert len(families) >= CONVICTION_MIN_FAMILIES
        verdict, _ = determine_verdict(below, families)
        assert verdict != "FAKE_CERTAIN", (
            "a file below the points bar was convicted with the temporal witness. "
            "The witness adds no score, so it must be unable to reach a conviction "
            "on its own however many families it completes."
        )

    def test_it_is_declared_as_a_pointless_witness(self) -> None:
        """The classification must be explicit, not inferred from behaviour."""
        assert POINTLESS_WITNESS_RULES.get("Rule14TemporalSeam") == "temporal"


class TestGates:
    """When it declines to speak."""

    def test_band_limited_files_are_left_to_the_cutoff_rules(self) -> None:
        """Below the cutoff gate there is nothing up there to stop moving."""
        audio = _stationary_above(15000.0)
        _score, _reasons, details = apply_rule_14_temporal_seam(
            "x.flac", MIN_CUTOFF_HZ - 1000.0, audio_data=audio, sample_rate=44100
        )
        assert details["temporal_witness"] is False

    def test_no_audio_means_no_witness(self) -> None:
        """A rule that cannot look must not testify."""
        _score, _reasons, details = apply_rule_14_temporal_seam("x.flac", 20000.0)
        assert details["temporal_witness"] is False
        assert not np.isfinite(details["temporal_seam"])


def test_the_bar_sits_where_it_was_calibrated() -> None:
    """Pinned against the genuine population it was measured on.

    258 genuine files — 80 certified CD rips and 178 wild taper recordings —
    median 0.374, p90 0.573, p95 0.651, p99 0.797. The bar sits between p90 and
    p95, and the two populations agreed closely, unlike Rule 13's where a heavier
    wild tail made a published calibration wrong.
    """
    assert 0.573 <= SEAM_BAR <= 0.651, (
        f"SEAM_BAR is {SEAM_BAR}, outside the p90-p95 band of the genuine corpus it "
        "was calibrated against. Re-measure before moving it: the bar is a "
        "false-alarm budget set on genuine material, never a recall target."
    )
    # A witness that scored would need to stay under WARNING to be safe. It scores
    # nothing, so this is belt and braces — but if someone ever gives it points,
    # this is the line that should stop them.
    assert SCORE_WARNING > 0
