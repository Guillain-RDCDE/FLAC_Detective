"""Unit tests for Rule 11: cassette detection.

Two of these were skipped for a year behind a "TODO: rewrite mocks" — the rule
had moved from ``sf.read`` to ``sf.info`` + ``load_audio_segment`` and the
patches stopped intercepting anything. They are rewritten here against the real
call path, because Rule 11's contract changed in v1.8 and an unverified rule is
how the project got Rule 9.

The contract change is the important part. Rule 11's score is evidence that a
file is a GENUINE analog transfer. It used to be added to the transcode score,
which meant sounding like a cassette made you look more like a fake: the audit
measured AUC 0.321, an inverted rule handing genuine files +18.3 points on
average against +11.2 for transcodes. It is now a signal the calculator reads,
never a penalty, and ``test_rule_11_never_penalises_the_score`` pins that down.
"""

from unittest.mock import patch

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import CASSETTE_THRESHOLD
from flac_detective.analysis.new_scoring.rules.cassette import apply_rule_11_cassette_detection

SR = 44100
CASSETTE_MODULE = "flac_detective.analysis.new_scoring.rules.cassette"


class _FakeInfo:
    """Minimal stand-in for ``soundfile.info``."""

    def __init__(self, duration: float, samplerate: int):
        self.duration = duration
        self.samplerate = samplerate


@pytest.fixture
def fake_audio():
    """Patch the two calls Rule 11 actually makes, and hand it a signal.

    Returns a setter: call it with an ndarray and the rule will analyse that.
    """
    with (
        patch(f"{CASSETTE_MODULE}.sf.info") as info,
        patch(f"{CASSETTE_MODULE}.load_audio_segment") as load,
    ):

        def _set(audio: np.ndarray, sr: int = SR):
            info.return_value = _FakeInfo(duration=len(audio) / sr, samplerate=sr)
            load.return_value = (audio, sr)

        yield _set


def _tape_like(seconds: float = 6.0, sr: int = SR) -> np.ndarray:
    """Music plus broadband hiss — the acoustic signature Rule 11A looks for."""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    music = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 1320 * t)
    rng = np.random.default_rng(11)
    hiss = rng.normal(0, 10 ** (-30 / 20), t.size)
    return (music + hiss).astype(np.float64)


def _rolloff_only(seconds: float = 6.0, sr: int = SR) -> np.ndarray:
    """A gentle high-frequency roll-off with no hiss: 11B fires, 11A does not.

    Rule 11B measures the 12-18 kHz slope and wants -6 < slope < -3 dB/kHz, so
    the band energy is shaped explicitly rather than hoped for, and the noise
    floor is kept far below 11A's -55 dB bar.
    """
    rng = np.random.default_rng(11)
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    music = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 1320 * t)
    # Sum of narrow tones from 12 to 18 kHz whose amplitude falls ~4.5 dB/kHz.
    hf = np.zeros_like(t)
    for khz in np.arange(12.0, 18.01, 0.25):
        amp = 10 ** ((-40.0 - 4.5 * (khz - 12.0)) / 20.0)
        hf += amp * np.sin(2 * np.pi * khz * 1000 * t + rng.uniform(0, 2 * np.pi))
    return (music + hf).astype(np.float64)


def _flat(seconds: float = 6.0, sr: int = SR) -> np.ndarray:
    """Tones only: no hiss for 11A, no 12-18 kHz slope for 11B."""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * 440 * t) + 0.25 * np.sin(2 * np.pi * 1320 * t)).astype(
        np.float64
    )


def test_rule11_skipped_high_cutoff():
    """Rule 11 is a low-cutoff rule; above 19 kHz it must not even run."""
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=20000, cutoff_std=100, sample_rate=SR
    )
    assert score == 0
    assert reasons == []


def test_rule11_recognises_a_tape_profile(fake_audio):
    """Hiss plus wow/flutter must read as cassette evidence, above the gate."""
    fake_audio(_tape_like())
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=150, sample_rate=SR
    )
    assert score >= CASSETTE_THRESHOLD, f"tape profile scored {score}, reasons={reasons}"
    assert any("R11A" in r for r in reasons), reasons  # tape hiss
    assert any("R11D" in r for r in reasons), reasons  # wow/flutter


def test_rule11_rejects_a_digital_profile(fake_audio):
    """Digital silence with a rock-stable cutoff is the opposite of a tape.

    It is rejected by the ABSENCE of cassette evidence, not by a penalty: 11D's
    "very stable, suspect digital" -10 was removed in v1.13.1 (on a 250 Hz grid
    a stable cutoff is the ordinary case, for genuine and transcode alike) and
    CASSETTE_THRESHOLD rose by the same 10 so no other test changed weight.
    """
    fake_audio(np.zeros(SR * 3, dtype=np.float64))
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=10, sample_rate=SR
    )
    assert score == 0
    assert score < CASSETTE_THRESHOLD
    assert not any("R11D" in r for r in reasons), reasons


def test_rule11_no_longer_has_a_test_c(fake_audio):
    """Test 11C is gone; nothing may award points for "no MP3 pattern".

    11C read Rule 9C's flag, which measured AUC 0.497. It was a constant +15
    wearing the costume of evidence, and it must not come back.
    """
    fake_audio(_tape_like())
    _, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=150, sample_rate=SR
    )
    assert not any("R11C" in r for r in reasons), reasons


def test_rule_11_never_penalises_the_score(fake_audio):
    """The strategy must record cassette evidence without adding a single point.

    This is the regression pin for the inverted-sign bug: whatever Rule 11
    concludes, a genuine analog transfer must not be pushed toward WARNING for it.
    """
    from pathlib import Path

    from flac_detective.analysis.new_scoring.models import (
        AudioMetadata,
        BitrateMetrics,
        ScoringContext,
    )
    from flac_detective.analysis.new_scoring.strategies import Rule11CassetteDetection

    fake_audio(_tape_like())
    context = ScoringContext(
        filepath=Path("dummy.flac"),
        audio_meta=AudioMetadata(sample_rate=SR, bit_depth=16, channels=2, duration=6.0),
        bitrate_metrics=BitrateMetrics(real_bitrate=700.0, apparent_bitrate=1411, variance=50.0),
        cutoff_freq=15000,
        cutoff_std=150,
    )
    Rule11CassetteDetection().apply(context)

    assert context.current_score == 0, "Rule 11 must contribute zero points"
    assert context.cassette_score > 0, "…while still recording the evidence it found"


# ---------------------------------------------------------------------------
# TEST 11D and the typed absence (v1.13.1)
#
# Provir reported the mirror defect in his own engine on 2026-08-29: a measured
# 0.0 coerced to a sentinel. His could only lose recall. Ours could not: for any
# file of 90 s or less, analyze_spectrum sampled ONE window, the wander was not
# computable, and it was returned as 0.0 — which 11D read as "very stable,
# suspect digital" for -10. That is exactly enough to push a roll-off-only file
# (11B alone, 20 points) under CASSETTE_THRESHOLD and cost it the -40
# protection. These four tests pin the repair so it cannot rot back.
# ---------------------------------------------------------------------------

# The reachable values of the wander, from the 250 Hz reporting grid and the
# three windows analyze_spectrum samples: one cell, one window one cell away,
# three cells, one window two cells away.
ONE_CELL = 117.85
THREE_CELLS = 204.12
TWO_CELLS_AWAY = 235.70


def test_11d_absence_and_stability_are_the_same_non_event(fake_audio):
    """An uncomputable wander and a stable one both contribute nothing.

    The defect was that they contributed nothing versus -10 — a 10-point gap
    between "measured stable" and "never measured", on files where the second
    was the only possible outcome.
    """
    fake_audio(_tape_like())
    score_absent, reasons_absent = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=float("nan"), sample_rate=SR
    )
    score_zero, reasons_zero = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=0.0, sample_rate=SR
    )
    assert score_absent == score_zero
    assert not any("R11D" in r for r in reasons_absent), reasons_absent
    assert not any("R11D" in r for r in reasons_zero), reasons_zero


@pytest.mark.parametrize(
    "hiss,rolloff,wander,protected",
    [
        # (11A fires, 11B fires, wander, does the file clear the gate?)
        # The v1.13.0 decision for the same inputs, recomputed by hand from
        # max(0, S + D_old) >= 15 with D_old = -10 below 30 Hz and +15 in
        # (50, 300). Every row below is what SHIPPED; the repair must reproduce
        # it, which is the whole point of moving the 10 into the threshold.
        (False, False, float("nan"), False),  # nothing found
        (False, True, float("nan"), False),  # roll-off only: 20 - 10 = 10 < 15
        (True, False, float("nan"), True),  # hiss only:     30 - 10 = 20 >= 15
        (True, True, float("nan"), True),  # both:          50 - 10 = 40 >= 15
        (False, False, 0.0, False),
        (False, True, 0.0, False),
        (True, False, 0.0, True),
        (True, True, 0.0, True),
        (False, True, 204.12, True),  # real flutter: 20 + 15 = 35 >= 15
        (True, True, 204.12, True),
    ],
)
def test_11d_repair_preserves_the_shipped_gate_decision(
    fake_audio, hiss, rolloff, wander, protected
):
    """The compensation is exact: same inputs, same gate decision as v1.13.0.

    Removing the -10 without raising the threshold was measured first and
    refused: 44 of 132 files lost their conviction against a registered bound of
    5 (ml/exchange/R11D_ABSENCE_REGISTRATION_2026-08-30.md). This table is the
    pin for the version that shipped instead.
    """
    fake_audio(_tape_like() if hiss else (_rolloff_only() if rolloff else _flat()))
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=wander, sample_rate=SR
    )
    assert any("R11A" in r for r in reasons) == hiss, reasons
    assert (score >= CASSETTE_THRESHOLD) == protected, f"score {score}, reasons {reasons}"


def test_11d_one_grid_cell_is_not_flutter(fake_audio):
    """117.9 Hz is the smallest non-zero value of a quantised statistic.

    It used to earn +15 as "natural cutoff variation (wow/flutter)" because the
    band opened at 50 Hz, below the instrument's own quantum. Rule 1's gate A
    has read the same statistic against 130 Hz since v1.12; the two now agree.
    """
    fake_audio(_tape_like())
    _, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=ONE_CELL, sample_rate=SR
    )
    assert not any("R11D" in r for r in reasons), reasons


@pytest.mark.parametrize("wander", [THREE_CELLS, TWO_CELLS_AWAY, 150.0])
def test_11d_real_wander_still_reads_as_flutter(fake_audio, wander):
    """Two cells or more is movement the grid cannot manufacture."""
    fake_audio(_tape_like())
    _, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=wander, sample_rate=SR
    )
    assert any("R11D" in r and "wow/flutter" in r for r in reasons), reasons


@pytest.mark.parametrize("wander", [0.0, ONE_CELL, THREE_CELLS, TWO_CELLS_AWAY, float("nan")])
def test_11d_has_no_unreachable_branch(fake_audio, wander):
    """Every reachable input lands in a live branch.

    The removed ``elif cutoff_std < 50`` covered [30, 50), where nothing on a
    250 Hz grid can land. It read as a calibrated neutral zone for five
    versions. This walks the whole reachable ladder instead of trusting it.
    """
    fake_audio(_tape_like())
    score, _ = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=wander, sample_rate=SR
    )
    assert isinstance(score, int) and score >= 0
