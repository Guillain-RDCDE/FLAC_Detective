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
