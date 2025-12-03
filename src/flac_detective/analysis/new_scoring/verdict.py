"""Verdict determination logic based on score."""

from typing import Tuple

from .constants import (
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
    SCORE_WARNING,
)


def determine_verdict(score: int) -> Tuple[str, str]:
    """Determine verdict and confidence based on score.

    Args:
        score: The calculated score (0-190, with Rule 9 adding up to +40)

    Returns:
        Tuple of (verdict_string, confidence_level)
    """
    if score >= SCORE_FAKE_CERTAIN:
        return "FAKE_CERTAIN", "❌ Transcoding confirmé avec certitude"
    elif score >= SCORE_SUSPICIOUS:
        return "SUSPICIOUS", "⚠️  Probable transcoding, vérification recommandée"
    elif score >= SCORE_WARNING:
        return "WARNING", "⚡ Anomalies détectées, peut être légitime"
    else:
        return "AUTHENTIC", "✅ Fichier authentique"
