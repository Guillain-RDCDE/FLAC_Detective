"""Verdict-threshold mapping, incl. the v0.15.1 SUSPICIOUS recalibration (61 -> 55).

A score-distribution study found real transcodes have a median score of ~58, i.e.
inside the old WARNING band, so genuine fakes were under-called. The SUSPICIOUS
floor moved to 55. These tests pin the boundaries so they can't drift silently.
"""

from __future__ import annotations

import pytest

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_SCORE,
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
)
from flac_detective.analysis.new_scoring.verdict import determine_verdict

# Two independent evidence families — enough to convict since v1.9.
CORROBORATED = {"spectral", "mdct"}
# One family, however loud. Rules 1 and 3 both live here, which is the whole point.
SINGLE_FAMILY = {"spectral"}


def v(score: int, families=None) -> str:
    return determine_verdict(score, families)[0]


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
        (86, "SUSPICIOUS"),  # v1.9: points alone no longer convict
    ],
)
def test_verdict_boundaries(score, expected):
    """The three lower tiers are read off the score alone, unchanged since v0.15.1.

    Parameterised with a single evidence family, which is the case where the score
    is the only thing deciding. Corroborated conviction is tested separately below,
    because it deliberately does not follow the score alone.
    """
    assert v(score, SINGLE_FAMILY) == expected


def test_fake_certain_threshold_still_defined():
    """86 remains the uncorroborated ceiling; it is simply no longer reachable."""
    assert SCORE_FAKE_CERTAIN == 86
    assert v(86, SINGLE_FAMILY) == "SUSPICIOUS"
    assert v(86, CORROBORATED) == "FAKE_CERTAIN"


class TestCorroborationGate:
    """Conviction needs independent sources, not just a big number (v1.9).

    The audit that forced this: all three false convictions on 80 certified-genuine
    files, and all 26 convictions on the 320 kbps MP3 arm, scored 100+ on Rules 1
    and 3 alone — and Rule 3 reads the bitrate Rule 1 inferred. One measurement,
    counted twice, clearing 86 unaided. No score threshold can tell that apart from
    real evidence; only counting sources can.
    """

    @pytest.mark.parametrize("score", [86, 100, 111, 150])
    def test_one_family_never_convicts_however_high(self, score):
        assert v(score, SINGLE_FAMILY) == "SUSPICIOUS", (
            "a single evidence family must not convict at any score — this is the "
            "Rule1+Rule3 double-count, and it produced every false conviction measured"
        )

    def test_missing_families_is_treated_as_uncorroborated(self):
        """Callers that don't supply families get the conservative answer."""
        assert v(150, None) == "SUSPICIOUS"

    def test_two_families_convict_below_the_old_bar(self):
        """Fifty-four corroborated files sat at exactly 85 against an 86-point bar."""
        assert CONVICTION_MIN_SCORE < SCORE_FAKE_CERTAIN
        assert v(CONVICTION_MIN_SCORE, CORROBORATED) == "FAKE_CERTAIN"
        assert v(CONVICTION_MIN_SCORE - 1, CORROBORATED) != "FAKE_CERTAIN"

    def test_corroboration_does_not_promote_a_quiet_file(self):
        """Two families agreeing on almost nothing is still almost nothing."""
        assert v(20, CORROBORATED) == "AUTHENTIC"

    def test_blocked_conviction_is_reported(self):
        from flac_detective.analysis.new_scoring.verdict import (
            uncorroborated_conviction_blocked,
        )

        assert uncorroborated_conviction_blocked(100, SINGLE_FAMILY) is True
        assert uncorroborated_conviction_blocked(100, CORROBORATED) is False
        assert uncorroborated_conviction_blocked(50, SINGLE_FAMILY) is False


def test_console_label_follows_verdict_not_score(caplog):
    """The console line renders the authoritative verdict, not its own score cut.

    Discriminating case: score 82 is SUSPICIOUS (< FAKE_CERTAIN 86), but the old
    console recomputed "FAKE" from a hard-coded score>=80. The label must now be
    SUSPICIOUS, matching the reports/API.
    """
    import logging as _logging

    from flac_detective.main import _log_formatted_result

    with caplog.at_level(_logging.INFO):
        _log_formatted_result({"score": 82, "verdict": "SUSPICIOUS", "filename": "x.flac"}, 1, 1)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "SUSPICIOUS" in text and "FAKE" not in text


class TestSuspiciousSaysWhatItRestsOn:
    """SUSPICIOUS is structurally the uncorroborated accusation, and now says so.

    ``CONVICTION_MIN_SCORE`` equals ``SCORE_SUSPICIOUS``, so a file with the points
    AND a second family has already convicted one branch earlier. Everything that
    reaches SUSPICIOUS has enough points and exactly one source of evidence.

    Requiring corroboration here too was written and measured before this was
    understood, and it does not tighten the tier — it empties it. That attempt is
    pinned as a non-behaviour below so it cannot be made again by accident.

    From issue #7: a master the owner can prove genuine reads 58 — Rule 1's +50
    for an MP3-bitrate signature plus Rule 2's +8 for a low cutoff, both
    ``spectral``, on a legitimately band-limited 18.25 kHz master. It was labelled
    "Probable transcoding". On the labelled exchange set the whole population of
    this tier was genuine: of 120 transcodes, the 30 that reach 55 points carry two
    to five families each and convict.
    """

    def test_the_tier_is_unchanged(self):
        """The verdict string must not move — only what it claims about itself."""
        assert v(58, SINGLE_FAMILY) == "SUSPICIOUS"
        assert v(150, SINGLE_FAMILY) == "SUSPICIOUS"

    def test_it_remains_reachable(self):
        """The trap: with both bars at 55, a corroboration gate here deletes the tier.

        Guarding the repair that was rejected. If someone later adds
        ``len(families) >= CONVICTION_MIN_FAMILIES`` to this branch, no score and
        no evidence set can produce SUSPICIOUS at all, and the engine loses a
        verdict silently.
        """
        assert CONVICTION_MIN_SCORE == SCORE_SUSPICIOUS
        reachable = [
            s for s in range(0, 151) if determine_verdict(s, SINGLE_FAMILY)[0] == "SUSPICIOUS"
        ]
        assert reachable, "SUSPICIOUS est devenu injoignable"

    def test_the_uncorroborated_case_is_labelled_as_such(self):
        _, confidence = determine_verdict(58, SINGLE_FAMILY)
        assert "single line of evidence" in confidence
        assert "not corroborated" in confidence

    def test_an_unknown_witness_list_does_not_claim_corroboration_either_way(self):
        """None is not one family and not two; it must not assert either."""
        _, confidence = determine_verdict(58, None)
        assert "single line of evidence" not in confidence
