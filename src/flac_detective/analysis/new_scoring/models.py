"""Data models for the new scoring system."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Dict, List, NamedTuple, Optional, Set

if TYPE_CHECKING:
    import numpy as np

    from ..audio_cache import AudioCache


class BitrateMetrics(NamedTuple):
    """Container for bitrate-related metrics."""

    real_bitrate: float
    apparent_bitrate: int
    variance: float


class AudioMetadata(NamedTuple):
    """Container for parsed audio metadata."""

    sample_rate: int
    bit_depth: int
    channels: int
    duration: float


@dataclass
class ScoringContext:
    """Context holding all data for the scoring process."""

    filepath: Path
    audio_meta: AudioMetadata
    bitrate_metrics: BitrateMetrics
    cutoff_freq: float
    cutoff_std: float = 0.0
    energy_ratio: float = 0.0
    # Residual spectral floor above the ~20.5 kHz wall (NaN = unknown / not in the
    # near-Nyquist 320 kbps zone). Drives Rule 1's wall-hardness gate.
    residual_floor_db: float = float("nan")

    # State updated during scoring
    mp3_bitrate_detected: Optional[int] = None
    silence_ratio: Optional[float] = None
    # Rule 11's cassette evidence (0-70). NOT part of the transcode score — the
    # calculator reads it to decide whether to protect the file. See Rule 11.
    cassette_score: int = 0
    # Rule 13's statistic, kept for reporting (NaN = the rule did not run).
    mdct_peak_ratio: float = float("nan")
    # Rule 14's statistic, and the families it declares as witnesses without
    # scoring. Kept separate from rule_scores on purpose: a family that adds no
    # points cannot be expressed in a points map, and conflating the two is what
    # MIN_FAMILY_CONTRIBUTION had to paper over. See evidence.POINTLESS_WITNESS_RULES.
    temporal_seam: float = float("nan")
    witness_families: Set[str] = field(default_factory=set)
    current_score: int = 0
    reasons: List[str] = field(default_factory=list)

    # Per-rule score attribution (v1.8). Every add_score is credited to whichever
    # rule is executing, so a rule's own contribution can be read back per file —
    # which is what makes ml/rule_audit.py able to measure a single rule's AUC.
    # Without it, a dead rule (see Rule 9, AUC 0.51) is invisible inside the total.
    # The recorded delta is the RAW requested one, before ``max(0, …)`` clamping:
    # the clamp is a property of the running total, not of the rule's signal.
    rule_scores: Dict[str, int] = field(default_factory=dict)
    # Score changes made by the calculator itself rather than by a rule object
    # (e.g. the cassette −40 bonus, the Rule 8 refinement rollback).
    UNCREDITED: "ClassVar[str]" = "_calculator"
    active_rule: Optional[str] = None

    # Cache for heavy rules (Rules 11/13) - avoids reloading the file
    audio_data: "Optional[np.ndarray]" = None  # numpy only imported under TYPE_CHECKING
    loaded_sample_rate: Optional[int] = None
    cache: "Optional[AudioCache]" = None  # AudioCache instance

    def add_score(self, score: int, new_reasons: List[str]):
        """Update score and reasons, crediting the delta to the running rule.

        The running total is deliberately allowed to go negative. Clamping at
        zero on *every* addition — as this did until v1.8 — silently destroys
        protection. Rule 8 is calculated first by design and contributes −50 to a
        genuine full-band file; that −50 was immediately clamped away, so when a
        later rule added +45 the file scored 45 instead of 0. Every protection
        rule that happened to run before a penalty was doing nothing at all,
        which is the exact opposite of "protect authentic files first".

        The clamp now happens once, on the final score, in ``new_calculate_score``.
        """
        key = self.active_rule or self.UNCREDITED
        self.rule_scores[key] = self.rule_scores.get(key, 0) + score
        self.current_score += score
        self.reasons.extend(new_reasons)
