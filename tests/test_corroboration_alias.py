"""The one place a family's size is computed from another family's size.

Jamie Dodd's third lesson from Provir's own corroboration bug: an exclusion is
only as good as your confidence that nothing downstream is a synonym. He had
deliberately kept one statistic out of his tell set, and it walked back in under
a different name — the same measurement wearing a different hat, sitting inside
the test it had been excluded from.

Audited here after he described it, and FLAC Detective has exactly one instance
of the shape. Rule 12 receives ``heuristic_score`` — the total every other rule
produced, which on real material is dominated by the ``spectral`` family — and
its high-confidence floor computes::

    bump = SCORE_WARNING - heuristic_score - score

So the size of the ``cnn`` family's contribution is a *function of* the size of
the ``spectral`` family's. That is the alias pattern, in our code, today.

It is currently harmless, and these tests pin **why**, so that it stays harmless
rather than staying harmless by luck:

1. The floor lands the file on exactly ``SCORE_WARNING``, which is below
   ``CONVICTION_MIN_SCORE``. A floored file cannot reach the corroborated bar at
   all, whatever its families say.
2. The floor can only ever leave *one* qualifying family, because a ``cnn``
   contribution large enough to be a witness arithmetically forces the rest of
   the score too low for any other family to be one.

Both properties are consequences of constants that live in different files, and
either could be broken by a threshold change made for unrelated reasons. That is
precisely the failure mode worth a test rather than a comment.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
    MIN_FAMILY_CONTRIBUTION,
    SCORE_WARNING,
)
from flac_detective.analysis.new_scoring.evidence import evidence_families
from flac_detective.analysis.new_scoring.verdict import determine_verdict


def test_floored_score_cannot_reach_the_corroborated_bar() -> None:
    """The invariant the whole containment rests on.

    The floor lifts a file to exactly ``SCORE_WARNING``. If that ever reached
    ``CONVICTION_MIN_SCORE``, the alias would become a route to conviction whose
    second witness was computed from the first.
    """
    assert SCORE_WARNING < CONVICTION_MIN_SCORE, (
        "Rule 12's high-confidence floor lands a file on exactly SCORE_WARNING, and "
        "its size is derived from the heuristic (spectral) total. That is only safe "
        f"while SCORE_WARNING ({SCORE_WARNING}) stays below CONVICTION_MIN_SCORE "
        f"({CONVICTION_MIN_SCORE}). Raising one or lowering the other turns a "
        "derived second witness into a conviction route."
    )


def test_floored_score_never_convicts_even_if_families_are_claimed() -> None:
    """Behavioural form of the same guarantee, through the real verdict function."""
    every_family = {"spectral", "container", "silence", "cnn", "mdct"}
    verdict, _ = determine_verdict(SCORE_WARNING, families=every_family)
    assert verdict != "FAKE_CERTAIN", (
        "A file sitting on the Rule 12 floor was convicted. The floor's magnitude "
        "is computed from the heuristic total, so this would be a conviction whose "
        "corroboration is an alias of the evidence it corroborates."
    )


@pytest.mark.parametrize("heuristic_score", list(range(0, SCORE_WARNING)))
def test_floor_leaves_at_most_one_qualifying_family(heuristic_score: int) -> None:
    """A cnn contribution big enough to be a witness starves every other family.

    Swept across every heuristic total the floor can fire on, rather than spot
    checked: the property is arithmetic, so the test should be too.
    """
    # What the floor produces: the two parts always sum to exactly SCORE_WARNING.
    cnn_points = SCORE_WARNING - heuristic_score

    # Give the whole remaining budget to a single other family — the most
    # favourable case for manufacturing a second witness.
    families = evidence_families(
        {"Rule12MLClassifier": cnn_points, "Rule1MP3Bitrate": heuristic_score}
    )

    assert len(families) < CONVICTION_MIN_FAMILIES, (
        f"heuristic={heuristic_score} + floored cnn={cnn_points} produced "
        f"{sorted(families)}: two witnesses out of a total that only sums to "
        f"{SCORE_WARNING}. With MIN_FAMILY_CONTRIBUTION={MIN_FAMILY_CONTRIBUTION} "
        "this should be arithmetically impossible."
    )


def test_when_the_floor_fires_it_lands_exactly_on_warning_and_no_higher() -> None:
    """The coupling exists, and it is bounded — measured, not assumed.

    Swept across every heuristic total rather than spot-checked, because the
    interesting behaviour is a boundary: the floor's own condition is
    ``heuristic + score < SCORE_WARNING``, and Rule 12's base contribution is
    capped. Together those mean the floor stops firing well before the heuristic
    total gets anywhere near the conviction bar — it only ever rescues files the
    heuristics left silent, which is what its docstring claims and what this
    pins.
    """
    torch = pytest.importorskip("torch")
    from flac_detective.analysis.new_scoring.rules import ml_classifier as mc

    class _PModel:
        def __init__(self, p: float) -> None:
            self._logit = math.log(p / (1 - p))

        def __call__(self, x):  # noqa: D401
            return torch.tensor([[0.0, self._logit]])

    fired_at = []
    with pytest.MonkeyPatch.context() as monkeypatch:
        mel = np.zeros((1, 2, mc._N_MELS, 8), dtype=np.float32)
        monkeypatch.setattr(mc, "_load_model", lambda: _PModel(0.99))
        monkeypatch.setattr(
            mc, "_compute_mel_windows", lambda _fp, **_kw: ([mel], mc._ROLLOFF_GATE_HZ + 5000)
        )
        monkeypatch.setattr(mc, "calibrate_probability", lambda value: value)

        for heuristic in range(0, CONVICTION_MIN_SCORE + 20):
            score, reasons = mc.apply_rule_12_ml_classifier(__file__, heuristic_score=heuristic)
            floored = any("high-confidence floor" in r for r in reasons)
            if not floored:
                continue
            fired_at.append(heuristic)
            total = heuristic + score
            assert total == SCORE_WARNING, (
                f"floor fired at heuristic={heuristic} and produced a total of {total}, "
                f"not {SCORE_WARNING}. The containment argument in this module's "
                "docstring depends on the floor landing exactly on WARNING."
            )
            assert total < CONVICTION_MIN_SCORE, (
                f"floor fired at heuristic={heuristic} and reached {total}, at or above "
                f"the corroborated bar ({CONVICTION_MIN_SCORE}). That is a conviction "
                "whose second witness was computed from the first."
            )

    assert fired_at, (
        "The high-confidence floor never fired anywhere in the sweep, so this test "
        "verified nothing. Its trigger condition or the fake model's probability has "
        "drifted — fix the test rather than deleting it."
    )
    assert max(fired_at) < MIN_FAMILY_CONTRIBUTION, (
        f"The floor fired with a heuristic total as high as {max(fired_at)}. Above "
        f"{MIN_FAMILY_CONTRIBUTION} the heuristic side could itself qualify as a "
        "family, and the floor would be manufacturing the second one."
    )
