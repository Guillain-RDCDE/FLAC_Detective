"""The bitrate variance: measured correctly, and deliberately not consulted yet.

Found 2026-09-05 while working issue #7. ``calculate_bitrate_variance`` computed
every segment's size as ``file_size / num_segments`` and returned the standard
deviation of ten identical numbers. It answered 0.0 for every file this tool has
ever analysed, silently, as though it had looked. Rule 5 needs > 100 and Rule 6
needs > 50, so neither had fired since the day they were written — while their
own unit tests passed, because those tests hand the rule a variance and never ask
whether one could arrive.

Two things are pinned here, and the second is the one that will look wrong to a
future reader:

1. the measurement is real now, and reports None rather than a fabricated zero;
2. the scoring path does not consult it.

(2) is deliberate. Switching the rules on switches on their never-executed
conditions too, and both are broken: Rule 5's bar sits above the range the
statistic takes, and Rule 6 compares a 96 kHz file's cutoff against the literal
constant 19000, granting -30 to a file Rule 2 is penalising +30 for the same
reading. Measured, that turns one blind-corpus conviction into AUTHENTIC 0 by
dropping the file under the fast path. Reviving them is a calibration release
with its own measurements, not a line in a bug fix.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from flac_detective.analysis.audio_formats import flac_segment_bitrates
from flac_detective.analysis.new_scoring.bitrate import calculate_bitrate_variance
from flac_detective.analysis.new_scoring.rules.bitrate import (
    apply_rule_5_high_variance,
    apply_rule_6_variable_bitrate_protection,
)

SR = 44_100


@pytest.fixture(scope="module")
def varying(tmp_path_factory):
    """Twelve seconds whose second half is far denser than its first.

    A real encoder spends more bits on the noisy half, so the segment bitrates
    must differ. The old implementation could not see this, by construction.
    """
    rng = np.random.default_rng(20260905)
    n = SR * 12
    audio = np.zeros((n, 2))
    t = np.arange(n) / SR
    audio += (0.2 * np.sin(2 * np.pi * 220.0 * t))[:, None]
    audio[n // 2 :] += rng.normal(0.0, 0.30, size=(n - n // 2, 2))
    path = tmp_path_factory.mktemp("var") / "v.flac"
    sf.write(str(path), np.clip(audio, -1, 1), SR, subtype="PCM_16", format="FLAC")
    return path


def test_the_segments_are_actually_different(varying):
    """The old code returned ten copies of one number; these must really differ."""
    rates = flac_segment_bitrates(varying, 10)
    assert rates is not None and len(rates) == 10
    assert len({round(r) for r in rates}) > 1, "les segments sont identiques"
    assert max(rates) - min(rates) > 100, "la moitie bruitee doit couter nettement plus"


def test_the_variance_is_no_longer_structurally_zero(varying):
    v = calculate_bitrate_variance(varying, SR)
    assert v is not None and v > 0.0


def test_an_unmeasurable_file_returns_none_not_zero(tmp_path):
    """An absence must not impersonate a reading.

    A fabricated 0.0 reads as "no variation at all", which is the strongest
    possible evidence of a constant-bitrate source.
    """
    missing = tmp_path / "nope.flac"
    assert calculate_bitrate_variance(missing, SR) is None

    too_short = tmp_path / "short.flac"
    sf.write(str(too_short), np.zeros((SR // 2, 2)), SR, subtype="PCM_16", format="FLAC")
    assert calculate_bitrate_variance(too_short, SR) is None


class TestBothRulesAbstainOnAnAbsentReading:
    def test_rule_5_abstains(self):
        assert apply_rule_5_high_variance(1500.0, None) == (0, [])

    def test_rule_6_abstains(self):
        assert apply_rule_6_variable_bitrate_protection(None, 900.0, 20_000.0, None) == (0, [])

    def test_rule_6_would_otherwise_protect(self):
        """Not dead code: with a reading it grants -30, which is why (2) matters."""
        score, _ = apply_rule_6_variable_bitrate_protection(None, 900.0, 20_000.0, 61.0)
        assert score == -30


def test_the_scoring_path_does_not_consult_the_variance_yet(tmp_path):
    """Guarding decision (2) above, so re-wiring it is a deliberate act.

    If someone hands the metrics a real variance again without first fixing Rule
    5's out-of-range bar and Rule 6's unscaled 19 kHz constant, this fails and
    points them at the measurement that says why.
    """
    from flac_detective.analysis.new_scoring.calculator import _calculate_bitrate_metrics
    from flac_detective.analysis.new_scoring.models import AudioMetadata

    path = tmp_path / "any.flac"
    rng = np.random.default_rng(1)
    audio = rng.normal(0, 0.2, size=(SR * 12, 2))
    sf.write(str(path), np.clip(audio, -1, 1), SR, subtype="PCM_16", format="FLAC")

    metrics = _calculate_bitrate_metrics(
        path,
        AudioMetadata(sample_rate=SR, bit_depth=16, channels=2, duration=12.0),
        cutoff_freq=22_050.0,
    )
    assert metrics.variance is None, (
        "la variance est de nouveau branchee au scoring : verifier d'abord le seuil "
        "hors plage de la Regle 5 et la constante 19000 non mise a l'echelle de la Regle 6"
    )
