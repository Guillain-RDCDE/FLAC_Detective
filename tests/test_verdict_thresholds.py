"""Verdict-threshold mapping, incl. the v0.15.1 SUSPICIOUS recalibration (61 -> 55).

A score-distribution study found real transcodes have a median score of ~58, i.e.
inside the old WARNING band, so genuine fakes were under-called. The SUSPICIOUS
floor moved to 55. These tests pin the boundaries so they can't drift silently.
"""

from __future__ import annotations

import pytest

from flac_detective.analysis.new_scoring.constants import (
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
)
from flac_detective.analysis.new_scoring.verdict import determine_verdict


def v(score: int) -> str:
    return determine_verdict(score)[0]


def test_suspicious_floor_is_55():
    assert SCORE_SUSPICIOUS == 55


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, "AUTHENTIC"),
        (30, "AUTHENTIC"),
        (31, "WARNING"),
        (54, "WARNING"),
        (55, "SUSPICIOUS"),  # the recalibrated boundary
        (58, "SUSPICIOUS"),  # median transcode now lands here (was WARNING)
        (85, "SUSPICIOUS"),
        (86, "FAKE_CERTAIN"),
    ],
)
def test_verdict_boundaries(score, expected):
    assert v(score) == expected


def test_fake_certain_unchanged():
    assert SCORE_FAKE_CERTAIN == 86
    assert v(86) == "FAKE_CERTAIN"
