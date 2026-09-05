"""Verdict determination — score for the tier, corroboration for the conviction."""

from typing import Optional, Set, Tuple

from .constants import (
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
    SCORE_WARNING,
)


def determine_verdict(score: int, families: Optional[Set[str]] = None) -> Tuple[str, str]:
    """Determine verdict and confidence.

    The three lower tiers are read off the score, unchanged. **FAKE_CERTAIN is
    not**: since v1.9 a conviction requires ``CONVICTION_MIN_FAMILIES``
    independent evidence families (see ``evidence.py``) as well as points, and a
    file that has them convicts from ``CONVICTION_MIN_SCORE`` rather than from
    the old flat 86.

    Since ``CONVICTION_MIN_SCORE == SCORE_SUSPICIOUS``, SUSPICIOUS is structurally
    the uncorroborated accusation and nothing else. Since v1.13.11 it says so —
    the tier is unchanged, its confidence line is not. See the comment there.

    Both directions matter, and both were forced by the same audit:

    * **A single family cannot convict, at any score.** Every false conviction
      in the 800-file corpus scored 100+ on Rules 1 and 3 alone — one bitrate
      inference counted twice.
    * **Two families convict earlier.** Fifty-four files carrying agreement
      between the CNN and the MDCT statistic — genuinely independent physics —
      sat at exactly 85 against an 86-point bar.

    Args:
        score: The calculated score (0-150).
        families: Independent evidence families accusing this file. ``None``
            means "not computed", which is treated as not corroborated: callers
            that do not supply it get the conservative answer rather than a
            silently unguarded conviction.

    Returns:
        Tuple of (verdict_string, confidence_level).
    """
    corroborated = families is not None and len(families) >= CONVICTION_MIN_FAMILIES

    if corroborated and score >= CONVICTION_MIN_SCORE:
        return "FAKE_CERTAIN", "❌ Transcoding confirmed — corroborated by independent evidence"
    if score >= SCORE_SUSPICIOUS:
        # SUSPICIOUS says what it rests on, as of v1.13.11.
        #
        # ``CONVICTION_MIN_SCORE`` equals ``SCORE_SUSPICIOUS``, so this tier is
        # already, structurally, *exactly* the uncorroborated accusation: a file
        # with the points AND two families convicted on the branch above. Anything
        # arriving here has enough points and only one source.
        #
        # Requiring corroboration here as well was written, measured and thrown
        # away, because it does not tighten the tier — it deletes it. The bars are
        # the same number; there is no band left for a corroborated SUSPICIOUS to
        # occupy. A verdict silently becoming unreachable is a worse defect than
        # the one being fixed.
        #
        # What is real is what the tier SAYS. Issue #7's reporter has a master he
        # can prove genuine — official store purchase, four containers bit-identical
        # after decode — that reads 58: Rule 1's +50 for an MP3-bitrate signature
        # plus Rule 2's +8 for a low cutoff, on a legitimately band-limited
        # 18.25 kHz master. Both rules are the ``spectral`` family, so one reading,
        # "the wall is low", scored twice. He was told "Probable transcoding".
        #
        # Measured on the labelled exchange set (59 genuine, 120 transcodes): of
        # the 30 transcodes reaching 55 points, every one carries two to five
        # families and convicts. Of the three genuine files reaching it, the one
        # accused on a single family lands here. On that sample this tier's entire
        # population is genuine — n is small and the wording is what changes, not
        # the threshold, but a label reading "probable transcoding" over it is not
        # supportable.
        #
        # Same repair as v1.13.7 made to the AUTHENTIC pass, and for the same
        # reason: what was wrong was not when it fires but what it claimed. The
        # report now prints the deciding rules and the family count beside it.
        if families is not None and len(families) < CONVICTION_MIN_FAMILIES:
            return (
                "SUSPICIOUS",
                "⚠️  Marks of a transcode, but from a single line of evidence — "
                "not corroborated, worth a listen before you act",
            )
        return "SUSPICIOUS", "⚠️  Probable transcoding, manual check recommended"
    if score >= SCORE_WARNING:
        return "WARNING", "⚡ Anomalies detected, may be legitimate"
    return "AUTHENTIC", "✅ Authentic file"


def uncorroborated_conviction_blocked(score: int, families: Optional[Set[str]]) -> bool:
    """True if points alone would have convicted but corroboration was missing.

    Surfaced as a reason string so a capped verdict explains itself rather than
    looking like the score was simply lower than the user expects.
    """
    if score < SCORE_FAKE_CERTAIN:
        return False
    return families is None or len(families) < CONVICTION_MIN_FAMILIES
