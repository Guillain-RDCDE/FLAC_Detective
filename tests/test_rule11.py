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
    """Digital silence with a rock-stable cutoff is the opposite of a tape."""
    fake_audio(np.zeros(SR * 3, dtype=np.float64))
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac", cutoff_freq=15000, cutoff_std=10, sample_rate=SR
    )
    assert score == 0
    assert any("R11D" in r and "stable" in r for r in reasons), reasons


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
