"""An AUTHENTIC that means "nothing fired" versus one that means "nothing ran".

Registered, with the amendment its own control population forced, in
``ml/exchange/ABSTENTION_REGISTRATION_2026-09-01.md``.
"""

from flac_detective.analysis.assessability import (
    MIN_ASSESSABLE_RATE_HZ,
    MIN_ASSESSABLE_SAMPLES,
    SILENCE_FLOOR_RMS,
    unassessable_reason,
)

OK = (44100, 60.0, 19000.0, 0.1)


def test_a_normal_file_is_assessable():
    assert unassessable_reason(*OK) is None


def test_a_rate_below_the_domain_abstains():
    reason = unassessable_reason(MIN_ASSESSABLE_RATE_HZ - 1, 60.0, 4000.0, 0.1)
    assert reason is not None and "below" in reason


def test_the_domain_edge_is_inclusive():
    """Exactly at the floor the file is assessable; one hertz under, it is not."""
    assert unassessable_reason(MIN_ASSESSABLE_RATE_HZ, 60.0, 15000.0, 0.1) is None
    assert unassessable_reason(MIN_ASSESSABLE_RATE_HZ - 1, 60.0, 15000.0, 0.1) is not None


def test_silence_abstains_even_though_it_has_a_cutoff():
    """The reason this is not a cutoff question: a silent file still has one."""
    reason = unassessable_reason(44100, 60.0, 19845.0, SILENCE_FLOOR_RMS)
    assert reason is not None and "no measurable signal" in reason


def test_an_unmeasured_level_is_not_silence():
    """None is an absence, not a zero. It must not abstain on its own."""
    assert unassessable_reason(44100, 60.0, 19000.0, None) is None


def test_an_unanalysable_spectrum_abstains():
    for cutoff in (None, float("nan"), 0.0):
        assert unassessable_reason(44100, 60.0, cutoff, 0.1) is not None


def test_a_file_below_one_frame_reading_abstains():
    """The floor is the frame witness's own arithmetic, not a round number."""
    just_under = (MIN_ASSESSABLE_SAMPLES - 1) / 44100
    assert unassessable_reason(44100, just_under, 19000.0, 0.1) is not None


def test_a_two_second_file_is_assessable():
    """Two seconds is plenty for every instrument that reads this axis.

    A 10-second threshold, chosen because it sounded reasonable, abstained on
    these. The real floor is 0.39 s at 44.1 kHz, and two existing tests that
    build 2-second synthetic WAVs caught the error by failing.
    """
    assert unassessable_reason(44100, 2.0, 19000.0, 0.1) is None


def test_an_unreadable_rate_abstains():
    reason = unassessable_reason(None, 60.0, 19000.0, 0.1)
    assert reason is not None and "sample rate" in reason


def test_a_mono_file_is_not_a_reason_here():
    """Mono is the control that must NOT abstain.

    It loses the stereo and temporal witnesses and keeps the spectral family, the
    CNN and the MDCT statistic. Channel count is therefore absent from the
    signature on purpose — listing it as unreadable was this registration's own
    error, caught by building the population before measuring.
    """
    assert unassessable_reason(*OK) is None


def test_every_reason_is_a_sentence_a_user_can_argue_with():
    """An abstention that does not say why is worse than a wrong answer."""
    cases = [
        (None, 60.0, 19000.0, 0.1),
        (8000, 60.0, 4000.0, 0.1),
        (44100, 60.0, 19000.0, 0.0),
        (44100, 60.0, float("nan"), 0.1),
        (44100, 0.1, 19000.0, 0.1),
    ]
    for case in cases:
        reason = unassessable_reason(*case)
        assert reason and len(reason) > 20 and not reason.endswith(".")
