"""Rule 12 multi-window inference (#3): probability aggregation across windows.

Needs torch (importorskip), so it is skipped where the ML extra isn't installed.
A stateful fake model returns a different probability per successive call (one
call per window), letting us check the mean/spread aggregation without a real
TorchScript model or audio decode.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.rules import ml_classifier as mc

torch = pytest.importorskip("torch")


class _SeqModel:
    """Fake model returning a preset probability per successive call (one per window)."""

    def __init__(self, probs):
        self._logits = [math.log(p / (1 - p)) for p in probs]
        self._i = 0

    def __call__(self, x):  # noqa: D401
        logit = self._logits[self._i % len(self._logits)]
        self._i += 1
        return torch.tensor([[0.0, logit]])


def _patch_windows(monkeypatch, probs, rolloff=mc._ROLLOFF_GATE_HZ + 5000):
    mel = np.zeros((1, 2, mc._N_MELS, 8), dtype=np.float32)
    monkeypatch.setattr(mc, "_load_model", lambda: _SeqModel(probs))
    monkeypatch.setattr(
        mc, "_compute_mel_windows", lambda _fp, **_kw: ([mel] * len(probs), rolloff)
    )


def test_aggregates_mean_over_windows(monkeypatch):
    """The file probability is the mean of per-window probabilities (no calibration)."""
    _patch_windows(monkeypatch, probs=[0.99, 0.51])  # mean 0.75 -> flagged, not saturated
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac")
    assert score > 0
    assert "2 windows" in reasons[0]


def test_one_clean_window_pulls_down_a_single_spike(monkeypatch):
    """A lone high-p window is tempered by clean ones (robustness vs single-window)."""
    _patch_windows(monkeypatch, probs=[0.97, 0.12, 0.12])  # mean ~0.40 < 0.5 -> no score
    score, _ = mc.apply_rule_12_ml_classifier("d.flac")
    assert score == 0


def test_spread_surfaced_when_windows_disagree(monkeypatch):
    """A large per-window spread is reported as a low-confidence signal."""
    _patch_windows(monkeypatch, probs=[0.99, 0.55])  # spread 0.44 >= 0.25
    score, reasons = mc.apply_rule_12_ml_classifier("d.flac")
    assert score > 0
    assert "spread" in reasons[0]
