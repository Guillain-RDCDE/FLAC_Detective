"""Tests for the MDCT frame-alignment detector.

These do not need ffmpeg, an audio corpus, or a network: the positive case is
*synthesised* by doing to a signal exactly what a lossy encoder does — take its
MDCT at a fixed alignment, zero most of the coefficients, and resynthesise. If
the detector cannot see that, it cannot see a transcode either, and the failure
is in the detector rather than in the corpus.

That matters because the rule this backs was added specifically to be measurable.
Rule 9 shipped for a year on plausible physics and no measurement; the tests here
are the standing check that the replacement actually separates.
"""

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.mdct import (
    HOP,
    WINDOW_LEN,
    alignment_stat,
    kbd_window,
    sine_window,
)

SAMPLE_RATE = 44100


def _full_basis() -> np.ndarray:
    """Unrestricted (WINDOW_LEN x HOP) MDCT basis, for synthesis in these tests."""
    half = HOP
    n = np.arange(WINDOW_LEN)[:, None]
    k = np.arange(half)[None, :]
    return np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float64)


def _synthesise(zero_fraction: float, n_frames: int = 120, seed: int = 7) -> np.ndarray:
    """Build a signal whose MDCT was quantised to zero at a known alignment.

    This is the encoder's arithmetic in miniature: coefficients with a plausible
    1/f envelope, a share of them set to exactly zero, then overlap-added back
    through the same window. ``zero_fraction=0`` gives the control — same
    synthesis path, nothing zeroed — so a positive result cannot be an artefact
    of the synthesis itself.
    """
    rng = np.random.default_rng(seed)
    basis = _full_basis()
    window = kbd_window().astype(np.float64)
    envelope = 1.0 / (1.0 + np.arange(HOP) / 40.0)

    out = np.zeros(WINDOW_LEN + n_frames * HOP)
    for frame in range(n_frames):
        coeffs = rng.standard_normal(HOP) * envelope
        if zero_fraction > 0:
            mask = rng.random(HOP) < zero_fraction
            coeffs[mask] = 0.0
        block = (basis @ coeffs) * window * (2.0 / HOP)
        start = frame * HOP
        out[start : start + WINDOW_LEN] += block
    peak = np.abs(out).max()
    return (out / peak if peak > 0 else out).astype(np.float32)


class TestWindows:
    """The window is the one detail that silently kills this detector."""

    def test_kbd_is_symmetric(self):
        w = kbd_window()
        assert w.shape == (WINDOW_LEN,)
        np.testing.assert_allclose(w, w[::-1], atol=1e-6)

    def test_kbd_satisfies_princen_bradley(self):
        # w[n]^2 + w[n + N/2]^2 == 1 is what makes overlap-add reconstruct
        # exactly. A window failing this is not a KBD window.
        w = kbd_window().astype(np.float64)
        np.testing.assert_allclose(w[:HOP] ** 2 + w[HOP:] ** 2, np.ones(HOP), atol=1e-6)

    def test_sine_satisfies_princen_bradley(self):
        w = sine_window().astype(np.float64)
        np.testing.assert_allclose(w[:HOP] ** 2 + w[HOP:] ** 2, np.ones(HOP), atol=1e-6)

    def test_kbd_and_sine_differ(self):
        # If these ever coincide, the "wrong window reads at the floor" finding
        # would be untestable — and the alpha=4 detail would be silently lost.
        assert np.abs(kbd_window() - sine_window()).max() > 0.05


class TestNull:
    """Genuine-like audio must sit at the null, or the rule is a false-positive machine."""

    def test_white_noise_has_no_preferred_alignment(self):
        rng = np.random.default_rng(3)
        x = rng.standard_normal(SAMPLE_RATE * 8).astype(np.float32) * 0.2
        ratio, _ = alignment_stat(x, SAMPLE_RATE)
        assert ratio < 3.0, f"white noise should be flat, got peak_ratio={ratio}"

    def test_sparse_tonal_signal_makes_the_rule_abstain(self):
        """Four bare sine waves must produce no verdict at all, not a low one.

        This is the detector's one real false-positive mode and it was found by
        this test. With almost the whole 2–16 kHz band empty, the baseline hole
        fraction collapses to 0.00019 against ~0.005 for real music, and
        peak_ratio — a ratio of two near-zero numbers — drifted to 3.0 on nothing.
        That is above the +55 threshold. The reliability gate now catches it:
        below MIN_BASELINE_HOLE_FRACTION the statistic abstains.
        """
        t = np.arange(SAMPLE_RATE * 8) / SAMPLE_RATE
        x = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate([220, 440, 660, 1320]))
        x = (x / np.abs(x).max() * 0.8).astype(np.float32)
        ratio, offset = alignment_stat(x, SAMPLE_RATE)
        assert not np.isfinite(ratio), f"expected abstention, got peak_ratio={ratio}"
        assert offset == -1

    def test_unzeroed_synthesis_is_the_control(self):
        # Same synthesis path as the positive case with nothing zeroed. This is
        # what proves a high ratio comes from the zeros, not from the framing.
        ratio, _ = alignment_stat(_synthesise(zero_fraction=0.0), SAMPLE_RATE)
        assert ratio < 3.0, f"control synthesis should be flat, got peak_ratio={ratio}"


class TestDetection:
    """The positive case: coefficients zeroed at a known alignment must show up."""

    @pytest.mark.parametrize("zero_fraction", [0.15, 0.3, 0.5])
    def test_quantised_signal_peaks(self, zero_fraction):
        ratio, offset = alignment_stat(_synthesise(zero_fraction), SAMPLE_RATE)
        assert ratio > 8.0, f"zeroed MDCT should peak, got peak_ratio={ratio}"
        # The synthesis puts frame boundaries on multiples of HOP starting at 0,
        # so the detected alignment must land at (or adjacent to) 0 mod HOP.
        assert min(offset, HOP - offset) <= 2, f"peak found at offset {offset}, expected ~0"

    def test_extreme_zeroing_defeats_the_median_reference(self):
        """Documented blind spot, asserted so it cannot be forgotten.

        Above ~60 % zeroed coefficients the ±16-bin median reference is itself
        zero, so nothing reads as "far below its neighbourhood" and the statistic
        collapses to the null. That regime means a very low bitrate — where the
        spectral-cliff rules already convict easily — so it is an acceptable
        trade, but it is a real hole and it belongs in the test suite rather than
        in a footnote.
        """
        ratio, _ = alignment_stat(_synthesise(zero_fraction=0.7), SAMPLE_RATE)
        assert ratio < 4.0, (
            "if this now detects, the reference statistic changed — re-measure "
            f"the whole corpus rather than trusting it (got {ratio})"
        )

    def test_wrong_window_loses_the_signal(self):
        # Jamie Dodd's trap, made into a regression test: analysing KBD-encoded
        # material with a sine window drops the statistic toward the floor. If a
        # future refactor swaps the default window, this test fails loudly
        # instead of the detector quietly going blind.
        x = _synthesise(zero_fraction=0.3)
        right, _ = alignment_stat(x, SAMPLE_RATE, window_kind="kbd")
        wrong, _ = alignment_stat(x, SAMPLE_RATE, window_kind="sine")
        assert right > wrong * 1.5, f"kbd={right}, sine={wrong} — window choice must matter"


class TestRobustness:
    """Degenerate inputs must return a null, never raise."""

    def test_silence_returns_non_finite_or_null(self):
        x = np.zeros(SAMPLE_RATE * 5, dtype=np.float32)
        ratio, _ = alignment_stat(x, SAMPLE_RATE)
        assert (not np.isfinite(ratio)) or ratio <= 3.0

    def test_too_short_input_does_not_raise(self):
        x = np.random.default_rng(1).standard_normal(WINDOW_LEN // 2).astype(np.float32)
        ratio, offset = alignment_stat(x, SAMPLE_RATE)
        assert offset == -1 or np.isnan(ratio) or ratio >= 0


class TestRule8Precedence:
    """Rule 13 must override Rule 8's protection, and only when it has evidence.

    Rule 8 grants −50 to a full-range spectrum on the reasoning that a transcode
    would have left a cliff — the exact reasoning that stops holding at 256–320
    kbps. When Rule 13 finds the encoder's quantisation grid, that −50 has to go,
    or the protection swallows the detection. It did, in the audit: fixing an
    unrelated clamp bug made Rule 8 real and 320 kbps AAC detection fell from
    97.5 % to 26.2 % overnight.
    """

    @staticmethod
    def _context(cutoff: float = 22050.0):
        from pathlib import Path

        from flac_detective.analysis.new_scoring.models import (
            AudioMetadata,
            BitrateMetrics,
            ScoringContext,
        )

        return ScoringContext(
            filepath=Path("dummy.flac"),
            audio_meta=AudioMetadata(sample_rate=44100, bit_depth=16, channels=2, duration=60.0),
            bitrate_metrics=BitrateMetrics(
                real_bitrate=700.0, apparent_bitrate=1411, variance=50.0
            ),
            cutoff_freq=cutoff,
        )

    def test_protection_is_withdrawn_when_rule_13_fires(self, monkeypatch):
        from flac_detective.analysis.new_scoring import calculator

        context = self._context()
        context.rule_scores["Rule8NyquistException"] = -50
        context.current_score = -50

        monkeypatch.setattr(
            calculator.Rule13MDCTAlignment,
            "_apply",
            lambda self, ctx: ctx.add_score(55, ["R13: grid found"]),
        )
        calculator._run_rule_13(context)

        assert context.current_score == 55, (
            "Rule 8's protection must be withdrawn once Rule 13 has direct evidence; "
            f"got {context.current_score}"
        )
        assert any("withdrawn" in r for r in context.reasons)

    def test_protection_survives_when_rule_13_is_silent(self, monkeypatch):
        """The override must be earned. A silent Rule 13 removes nothing."""
        from flac_detective.analysis.new_scoring import calculator

        context = self._context()
        context.rule_scores["Rule8NyquistException"] = -50
        context.current_score = -50

        monkeypatch.setattr(
            calculator.Rule13MDCTAlignment, "_apply", lambda self, ctx: ctx.add_score(0, [])
        )
        calculator._run_rule_13(context)

        assert context.current_score == -50, "a silent Rule 13 must not touch Rule 8"
        assert not any("withdrawn" in r for r in context.reasons)


class TestScoreClamping:
    """The running total is clamped once, at the end — never per addition."""

    def test_protection_survives_until_the_end(self):
        from pathlib import Path

        from flac_detective.analysis.new_scoring.models import (
            AudioMetadata,
            BitrateMetrics,
            ScoringContext,
        )

        context = ScoringContext(
            filepath=Path("dummy.flac"),
            audio_meta=AudioMetadata(sample_rate=44100, bit_depth=16, channels=2, duration=60.0),
            bitrate_metrics=BitrateMetrics(
                real_bitrate=700.0, apparent_bitrate=1411, variance=50.0
            ),
            cutoff_freq=22050.0,
        )
        context.add_score(-50, ["protection first"])
        assert (
            context.current_score == -50
        ), "clamping here is what made every early protection rule inert before v1.8"
        context.add_score(45, ["penalty second"])
        assert context.current_score == -5


class TestHypothesisCountIsCertified:
    """The shipped statistic is a maximum over draws, so the draw count is calibration.

    ``best_alignment_stat`` takes the strongest reading across ``HYPOTHESES``. A
    maximum does not converge as draws are added — it creeps upward. Jamie Dodd of
    Provir found this in v1.10's own release numbers: the genuine ceiling moved
    1.42 -> 1.427 exactly when the second hypothesis landed, and across 80
    certified-genuine files the two hypotheses split the maximum 33/47, so they
    compete for it on nearly every file.

    Rule 13's bars (2.0 review, 3.0 hard) sit above a genuine population measured
    under a fixed number of draws. A third hypothesis would lift that population
    toward bars set when there were two — silently, and only ever against
    authentic files. These tests do not forbid adding one; they forbid adding one
    without re-certifying.
    """

    def test_hypothesis_count_matches_the_certified_calibration(self) -> None:
        """Adding or removing a hypothesis invalidates the genuine baseline."""
        from flac_detective.analysis.new_scoring.mdct import (
            CERTIFIED_HYPOTHESIS_COUNT,
            HYPOTHESES,
        )

        assert len(HYPOTHESES) == CERTIFIED_HYPOTHESIS_COUNT, (
            f"HYPOTHESES now has {len(HYPOTHESES)} entries but the genuine baseline was "
            f"certified against {CERTIFIED_HYPOTHESIS_COUNT}. The statistic is a maximum "
            "over draws, so more draws raise the genuine ceiling toward thresholds that "
            "were calibrated for fewer. Re-run ml/mdct_probe_v110-style calibration over "
            "the certified-genuine corpus, update CERTIFIED_GENUINE_MAX and this count, "
            "then confirm RATIO_REVIEW still clears the new ceiling."
        )

    def test_review_bar_clears_the_certified_genuine_quantile(self) -> None:
        """Calibrated against a quantile, because a sample maximum is not a bound.

        The bars were originally set against the highest genuine file in an
        880-file draw (1.494). Re-certifying over 877 files under the shipped
        configuration produced a maximum of 2.418 — the old figure was a lucky
        sample, not a property of the population. A max over a finite sample is a
        lower bound and cannot be extrapolated; p99.9 can.
        """
        from flac_detective.analysis.new_scoring.mdct import CERTIFIED_GENUINE_P999
        from flac_detective.analysis.new_scoring.rules.mdct_alignment import (
            RATIO_HARD,
            RATIO_REVIEW,
        )

        assert RATIO_REVIEW > CERTIFIED_GENUINE_P999, (
            f"the review bar ({RATIO_REVIEW}) no longer clears the genuine p99.9 "
            f"({CERTIFIED_GENUINE_P999}). Rule 13 would start reviewing authentic audio "
            "at a rate well above the documented one."
        )
        assert RATIO_HARD > RATIO_REVIEW, "the hard bar must sit above the review bar"

        margin = (RATIO_REVIEW - CERTIFIED_GENUINE_P999) / CERTIFIED_GENUINE_P999
        assert margin > 0.20, (
            f"the review bar is only {margin:.1%} above the certified genuine p99.9. "
            "Rule 13's bars are meant to sit clear of the body of the distribution, "
            "not against it."
        )

    def test_a_lone_review_cannot_flag_a_genuine_file(self) -> None:
        """The arithmetic the tail's non-emptiness is tolerable *because of*.

        Re-certification found 1 genuine file in 877 reaching the review bar. That
        is acceptable only while a lone Rule 13 review stays below the WARNING
        threshold, so the outlier cannot flag its own file without independent
        corroboration. If SCORE_REVIEW ever reached SCORE_WARNING, that measured
        0.11 % would become a false-flag rate instead of a harmless reading.
        """
        from flac_detective.analysis.new_scoring.constants import SCORE_WARNING
        from flac_detective.analysis.new_scoring.rules.mdct_alignment import SCORE_REVIEW

        assert SCORE_REVIEW < SCORE_WARNING, (
            f"Rule 13's review tier ({SCORE_REVIEW}) now reaches the WARNING threshold "
            f"({SCORE_WARNING}) on its own. Measured, that turns 1 genuine file in 877 "
            "into a false flag with no second opinion involved."
        )
