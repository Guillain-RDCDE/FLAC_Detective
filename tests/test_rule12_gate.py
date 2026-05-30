"""Rule 12 reliability gate: the CNN must abstain on band-limited input.

The gate exists because an empirical audit showed the model's precision collapses
to a coin flip below ~7 kHz of spectral rolloff (see ml/README.md). These tests
pin the gate logic without needing the real TorchScript model or audio decode —
``_load_model`` and ``_compute_mel`` are monkeypatched so we test only the gate.
"""

from __future__ import annotations

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.rules import ml_classifier as mc

torch = pytest.importorskip("torch")


class _FakeModel:
    """Stand-in TorchScript model: always returns 'transcoded' with high logit."""

    def __call__(self, x):  # noqa: D401
        return torch.tensor([[0.0, 5.0]])


def _patch(monkeypatch, rolloff):
    mel = np.zeros((1, 1, mc._N_MELS, 8), dtype=np.float32)
    monkeypatch.setattr(mc, "_load_model", lambda: _FakeModel())
    monkeypatch.setattr(mc, "_compute_mel", lambda _fp: (mel, rolloff))


def test_abstains_below_gate(monkeypatch):
    """Band-limited input (rolloff < gate) -> Rule 12 contributes nothing."""
    _patch(monkeypatch, rolloff=mc._ROLLOFF_GATE_HZ - 1000)
    score, reasons = mc.apply_rule_12_ml_classifier("dummy.flac")
    assert score == 0
    assert reasons == []


def test_scores_above_gate(monkeypatch):
    """Above the gate the model runs and a confident 'transcoded' scores > 0."""
    _patch(monkeypatch, rolloff=mc._ROLLOFF_GATE_HZ + 5000)
    score, reasons = mc.apply_rule_12_ml_classifier("dummy.flac")
    assert score > 0
    assert reasons and "CNN" in reasons[0]


def test_gate_threshold_is_boundary(monkeypatch):
    """Exactly at the threshold is treated as reliable (gate is strict <)."""
    _patch(monkeypatch, rolloff=mc._ROLLOFF_GATE_HZ)
    score, _ = mc.apply_rule_12_ml_classifier("dummy.flac")
    assert score > 0
