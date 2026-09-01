"""The dependency guard: two families that read one observation count once.

Priced in ``ml/exchange/INDEPENDENCE_GUARD_REGISTRATION_2026-09-01.md`` on 524
files. These pin the behaviour the measurement chose, including the two ways the
guard must stay silent — an unknown cutoff, and a cutoff above the constant.
"""

import math

from flac_detective.analysis.new_scoring.constants import (
    CONVICTION_MIN_FAMILIES,
    FAMILY_INDEPENDENCE_MIN_CUTOFF_HZ,
)
from flac_detective.analysis.new_scoring.evidence import collapse_dependent_families

LOW = FAMILY_INDEPENDENCE_MIN_CUTOFF_HZ - 500.0
HIGH = FAMILY_INDEPENDENCE_MIN_CUTOFF_HZ + 500.0


def test_the_pair_becomes_one_witness_below_the_constant():
    """The band-limited case: two names, one observation, one witness."""
    got = collapse_dependent_families({"cnn", "spectral"}, LOW)
    assert len(got) == 1
    assert len(got) < CONVICTION_MIN_FAMILIES


def test_the_pair_stays_two_witnesses_above_the_constant():
    """A real low-bitrate transcode keeps its corroboration."""
    assert collapse_dependent_families({"cnn", "spectral"}, HIGH) == {"cnn", "spectral"}


def test_an_unknown_cutoff_is_not_a_low_cutoff():
    """Absence is not a value. NaN and None must both leave the evidence alone."""
    for unknown in (None, float("nan")):
        assert collapse_dependent_families({"cnn", "spectral"}, unknown) == {"cnn", "spectral"}


def test_the_boundary_is_exclusive():
    """Exactly at the constant the guard is silent; just under it, it fires."""
    at = FAMILY_INDEPENDENCE_MIN_CUTOFF_HZ
    assert collapse_dependent_families({"cnn", "spectral"}, at) == {"cnn", "spectral"}
    assert len(collapse_dependent_families({"cnn", "spectral"}, math.nextafter(at, 0.0))) == 1


def test_one_family_of_the_pair_alone_is_untouched():
    """The guard merges a pair; it never removes a lone witness."""
    assert collapse_dependent_families({"spectral"}, LOW) == {"spectral"}
    assert collapse_dependent_families({"cnn"}, LOW) == {"cnn"}


def test_an_independent_third_family_still_corroborates():
    """The point is not to stop convicting band-limited files, only to stop
    convicting them on one observation counted twice. A stereo or MDCT witness
    that read something else still supplies the second family."""
    got = collapse_dependent_families({"cnn", "spectral", "mdct"}, LOW)
    assert len(got) == CONVICTION_MIN_FAMILIES
    assert "mdct" in got


def test_families_outside_the_table_are_never_merged():
    """A rule absent from the dependency table keeps its independence by default."""
    got = collapse_dependent_families({"mdct", "stereo", "silence"}, LOW)
    assert got == {"mdct", "stereo", "silence"}
