"""Rule 12 high-confidence WARNING floor (v1.2).

On full-range material the v4 CNN detects high-bitrate AAC/Vorbis fakes well, but
those leave ~0 heuristic score and R12's capped +30 lands exactly on AUTHENTIC
(30, one short of WARNING). The floor lifts a *confident* detection on an
otherwise-silent file just to WARNING — never beyond, never below the normal
value, and only above the reliability gate. These tests pin that behaviour with a
fake model whose probability is controllable, so no real TorchScript/audio is
needed. See ``ml_classifier._WARNING_FLOOR_P`` and ml/calibrate_r12_threshold.py.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import SCORE_WARNING
from flac_detective.analysis.new_scoring.rules import ml_classifier as mc
from flac_detective.analysis.new_scoring.verdict import determine_verdict

torch = pytest.importorskip("torch")


class _PModel:
    """Fake model emitting logits that softmax to a chosen p(transcoded)."""

    def __init__(self, p: float) -> None:
        self._logit = math.log(p / (1 - p))

    def __call__(self, x):  # noqa: D401
        return torch.tensor([[0.0, self._logit]])


def _patch(monkeypatch, p, rolloff=mc._ROLLOFF_GATE_HZ + 5000):
    mel = np.zeros((1, 2, mc._N_MELS, 8), dtype=np.float32)
    monkeypatch.setattr(mc, "_load_model", lambda: _PModel(p))
    monkeypatch.setattr(mc, "_compute_mel_windows", lambda _fp, **_kw: ([mel], rolloff))
    # Neutralise the bundled calibration so the floor logic is tested on the chosen p.
    monkeypatch.setattr(mc, "calibrate_probability", lambda p: p)


def test_floor_lifts_silent_high_confidence_to_warning(monkeypatch):
    """High confidence (p >= floor) and silent heuristics lift the verdict to WARNING."""
    _patch(monkeypatch, p=0.99)
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac", heuristic_score=0)
    assert score == SCORE_WARNING
    assert determine_verdict(score)[0] == "WARNING"
    assert any("floor" in r for r in reasons)


def test_floor_not_applied_below_p_threshold(monkeypatch):
    """Moderate confidence (p < floor) keeps the normal mapping; stays AUTHENTIC."""
    _patch(monkeypatch, p=0.85)
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac", heuristic_score=0)
    assert score < SCORE_WARNING
    assert not any("floor" in r for r in reasons)


def test_floor_inactive_when_baseline_already_warns(monkeypatch):
    """If the heuristics already reach WARNING, R12 adds its normal points only."""
    _patch(monkeypatch, p=0.99)
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac", heuristic_score=40)
    assert score == 30  # saturated normal contribution, no bump
    assert not any("floor" in r for r in reasons)


def test_floor_does_not_fire_below_the_gate(monkeypatch):
    """Band-limited input abstains before the model or the floor can act."""
    _patch(monkeypatch, p=0.99, rolloff=mc._ROLLOFF_GATE_HZ - 1000)
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac", heuristic_score=0)
    assert score == 0
    assert reasons == []
