"""Tests for evidence families — the thing that decides what may convict.

Rule 9 shipped for a year because nothing measured a rule alone. The corroboration
gate is the next layer up: nothing was measuring rule *combinations*, so one
inference wearing two hats (Rules 1 and 3) convicted innocent files while two
genuinely independent measurements (Rules 12 and 13) lost to an 86-point bar by a
single point. These tests pin the grouping, because the grouping is the argument.
"""

import pytest

from flac_detective.analysis.new_scoring.evidence import RULE_FAMILY, evidence_families
from flac_detective.analysis.new_scoring.strategies import ScoringRule


class TestGrouping:
    """Which rules count as the same source of evidence."""

    def test_rules_1_2_4_are_one_family(self):
        """They all read the cutoff, or the bitrate inferred from it.

        Rule 4 gates on Rule 1's inference. However many fire, it is one look at one
        thing — and that pattern produced every false conviction measured. (Rule 3
        was here too until v1.10, when it was removed for never firing alone.)
        """
        assert (
            len(
                {
                    RULE_FAMILY["Rule1MP3Bitrate"],
                    RULE_FAMILY["Rule2Cutoff"],
                    RULE_FAMILY["Rule424BitSuspect"],
                }
            )
            == 1
        )
        assert "Rule3SourceVsContainer" not in RULE_FAMILY, "Rule 3 was removed in v1.10"
        assert evidence_families({"Rule1MP3Bitrate": 50, "Rule2Cutoff": 11}) == {"spectral"}

    def test_cnn_and_mdct_are_independent(self):
        """A mel-spectrogram model and a frame-alignment statistic are not the same look."""
        families = evidence_families({"Rule12MLClassifier": 30, "Rule13MDCTAlignment": 55})
        assert families == {"cnn", "mdct"}

    def test_protection_rules_are_not_evidence(self):
        """Rules 6, 8 and 11 argue for innocence; they can never help convict."""
        for rule in (
            "Rule6HighQualityProtection",
            "Rule8NyquistException",
            "Rule11CassetteDetection",
        ):
            assert rule not in RULE_FAMILY

    def test_rule_10_is_not_a_family(self):
        """Rule 10 re-scores segments through the same pipeline.

        A rule agreeing with itself on a different second of audio is consistency,
        not corroboration. Counting it would reintroduce the double-count this
        module exists to stop.
        """
        assert "Rule10Consistency" not in RULE_FAMILY


class TestPositiveOnly:
    """Only accusations count."""

    def test_negative_contributions_do_not_accuse(self):
        assert evidence_families({"Rule1MP3Bitrate": -20}) == set()

    def test_zero_contributions_do_not_accuse(self):
        """A rule that ran and found nothing has said nothing."""
        assert evidence_families({"Rule12MLClassifier": 0, "Rule13MDCTAlignment": 0}) == set()

    def test_unknown_rules_contribute_nothing(self):
        """A new rule earns conviction power only by being classified deliberately."""
        assert evidence_families({"RuleFutureSomething": 99}) == set()


def test_every_scoring_rule_is_classified_or_deliberately_excluded():
    """A rule must be either in a family or knowingly left out — never forgotten.

    This is the sibling of the "no unmeasured rule ships" guard, at the level
    above it: adding a rule without deciding whether it is independent evidence
    would let it silently change what counts as a conviction.
    """
    # Protection and consistency rules, excluded on purpose. Anything else showing
    # up here means someone added a rule and did not classify it.
    DELIBERATELY_EXCLUDED = {
        "Rule6HighQualityProtection",
        "Rule8NyquistException",
        "Rule10Consistency",
        "Rule11CassetteDetection",
    }
    concrete = {
        cls.__name__
        for cls in ScoringRule.__subclasses__()
        if not getattr(cls, "__abstractmethods__", None)
    }
    # Rules that testify without scoring are classified too — just not by points.
    # A points map cannot express them, which is exactly why they have their own.
    from flac_detective.analysis.new_scoring.evidence import POINTLESS_WITNESS_RULES

    unclassified = (
        concrete - set(RULE_FAMILY) - set(POINTLESS_WITNESS_RULES) - DELIBERATELY_EXCLUDED
    )
    assert not unclassified, (
        f"these scoring rules are neither assigned an evidence family nor listed as "
        f"deliberately excluded: {sorted(unclassified)}. Decide before shipping — an "
        f"unclassified rule cannot corroborate, which may be right, but it must be a "
        f"choice rather than an oversight."
    )


@pytest.mark.parametrize(
    "scores,expected_count",
    [
        ({}, 0),
        ({"Rule2Cutoff": 5}, 0),  # below MIN_FAMILY_CONTRIBUTION: a mumble, not a witness
        ({"Rule2Cutoff": 25}, 1),
        ({"Rule2Cutoff": 5, "Rule1MP3Bitrate": 50}, 1),  # same family, points add up
        ({"Rule2Cutoff": 25, "Rule12MLClassifier": 30}, 2),
        ({"Rule5HighVariance": 25, "Rule7SilenceAnalysis": 20, "Rule13MDCTAlignment": 55}, 3),
    ],
)
def test_family_counts(scores, expected_count):
    assert len(evidence_families(scores)) == expected_count


class TestMinimumContribution:
    """A family must say something substantial to count as a second witness.

    Found by the blind exchange with Provir: a genuine 2003 audience recording
    scored 128 and was convicted, of which 112 points were Rules 1+3 (one inference,
    doubled) and 16 were a hesitant CNN. Under v1.9 that 16 counted as a full
    independent witness and unlocked the conviction. Provir, whose gate requires two
    substantive legs, cleared the same file.
    """

    def test_a_mumbling_family_is_not_a_witness(self):
        from flac_detective.analysis.new_scoring.constants import MIN_FAMILY_CONTRIBUTION

        scores = {
            "Rule1MP3Bitrate": 50,
            "Rule2Cutoff": 12,
            "Rule12MLClassifier": MIN_FAMILY_CONTRIBUTION - 1,
        }
        assert evidence_families(scores) == {"spectral"}

    def test_a_confident_family_is(self):
        from flac_detective.analysis.new_scoring.constants import MIN_FAMILY_CONTRIBUTION

        scores = {"Rule1MP3Bitrate": 50, "Rule12MLClassifier": MIN_FAMILY_CONTRIBUTION}
        assert evidence_families(scores) == {"spectral", "cnn"}

    def test_points_accumulate_within_a_family(self):
        """Three small spectral contributions are still one witness, but a loud one."""
        assert evidence_families(
            {"Rule1MP3Bitrate": 8, "Rule2Cutoff": 8, "Rule424BitSuspect": 8}
        ) == {"spectral"}

    def test_the_v19_reading_is_still_available_for_measurement(self):
        """The audit harness needs to compare against the old behaviour."""
        scores = {"Rule1MP3Bitrate": 50, "Rule12MLClassifier": 16}
        assert evidence_families(scores, min_contribution=0) == {"spectral", "cnn"}
