"""Independent evidence families — what a conviction has to be made of.

A score is a sum, and a sum cannot tell you whether it came from one thing
repeated or several things agreeing. That distinction is the whole of this
module, and it was forced by measurement rather than taste.

The v1.8 per-rule audit found that **every** false conviction in an 800-file
corpus, and **every one** of the 26 convictions on the 320 kbps MP3 arm, rested
on Rules 1 and 3 contributing +50 each — and Rule 3 reads the bitrate Rule 1
inferred. One measurement, counted twice, clearing an 86-point bar unaided.

The opposite case appeared in the same audit. Rule 12 (a CNN on a mid/side
mel-spectrogram) and Rule 13 (MDCT frame alignment) both scored on 90 files, and
54 of those sat at exactly 85 against that same 86-point bar — two genuinely
independent physical measurements agreeing, and losing to arithmetic by one
point. Jamie Dodd of Provir found the same composition from the outside, on a
different codec arm, the same week.

So the fix is not to re-tune thresholds. It is to make the score answer a
different question: **how many independent ways do we know this?**

Grouping rationale, rule by rule:

``spectral``
    Rules 1, 2 and 4. All read the spectral cutoff or the MP3 bitrate inferred
    *from* that cutoff — Rule 4 gates on Rule 1's inference. However many fire, they
    are one look at one thing. (Rule 3 belonged here too and was removed outright in
    v1.10: it could not fire unless Rule 1 already had, so it only ever doubled the
    points.)
``container``
    Rule 5, bitrate variance across the file. Measured from FLAC block sizes
    rather than from the spectrum, so it stands on its own.
``silence``
    Rule 7, high-frequency energy in silent passages. Reads a region the cutoff
    rules ignore.
``cnn``
    Rule 12, the learned classifier.
``mdct``
    Rule 13, frame-alignment quantisation structure.

Deliberately absent:

* **Protection rules** (6, 8, 11) are evidence of *innocence*; they can never
  contribute to a conviction and are not families.
* **Rule 10** re-scores several segments through the same pipeline. Agreement
  between a rule and itself on a different second of audio is consistency, not
  corroboration — counting it would reintroduce exactly the double-count this
  module exists to prevent.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional, Set

from .constants import MIN_FAMILY_CONTRIBUTION

# Rule class name -> evidence family. A rule absent from this map contributes no
# family, which is the safe default: a new rule cannot silently earn conviction
# power just by existing.
RULE_FAMILY: Dict[str, str] = {
    "Rule1MP3Bitrate": "spectral",
    "Rule2Cutoff": "spectral",
    "Rule424BitSuspect": "spectral",
    "Rule5HighVariance": "container",
    "Rule7SilenceAnalysis": "silence",
    "Rule12MLClassifier": "cnn",
    "Rule13MDCTAlignment": "mdct",
    # Rule 14 contributes no points, so it can never appear here — a points map
    # cannot express a witness that does not score. See ``witnesses`` below.
}

# Families that qualify as a source WITHOUT contributing points.
#
# Until v1.11 a family existed only if some rule had added score to it, which
# silently welded two different questions together: how much does this file look
# like a transcode, and how many independent things say so. MIN_FAMILY_CONTRIBUTION
# was a patch on that confusion — it filtered witnesses by their point total
# because point total was the only handle available.
#
# Rule 14 forces them apart. Its statistic reads AUC 0.84 on Opus, where every
# other family is dead, and it also fires on ~8 % of real music (heavy HF limiting,
# dense synthetic pads). Giving it points to make it count as a witness was tried
# and measured: three new false convictions on 258 genuine files, because the
# points pushed mid-scoring real recordings past CONVICTION_MIN_SCORE and then
# corroborated them. Awarding zero and declaring the witness separately measures 0.
POINTLESS_WITNESS_RULES: Dict[str, str] = {
    "Rule14TemporalSeam": "temporal",
    # Rule 15 reads the STEREO IMAGE — joint-stereo coupling kills the side channel
    # above ~10 kHz while the mid stays alive. Independent of spectral geometry, of
    # frame alignment and of temporal variance, which is what makes it a fifth
    # family rather than a variant of any of them.
    "Rule15StereoSeam": "stereo",
}


def family_totals(rule_scores: Mapping[str, int]) -> Dict[str, int]:
    """Total positive points each family contributed.

    Negative contributions are dropped rather than netted: a protection rule
    arguing for innocence must not reduce an accuser's weight, and vice versa.
    """
    totals: Dict[str, int] = {}
    for rule, family in RULE_FAMILY.items():
        points = rule_scores.get(rule, 0)
        if points > 0:
            totals[family] = totals.get(family, 0) + points
    return totals


def evidence_families(
    rule_scores: Mapping[str, int],
    min_contribution: int = MIN_FAMILY_CONTRIBUTION,
    witnesses: Optional[Set[str]] = None,
) -> Set[str]:
    """Return the independent evidence families that meaningfully accuse this file.

    A family counts as a witness only if it contributes at least
    ``min_contribution`` points. v1.9 accepted any positive contribution, and the
    blind exchange with Provir found what that costs: a genuine 2003 audience
    recording convicted at 128 points, of which 112 were Rules 1+3 (one inference,
    doubled) and 16 were a hesitant CNN. The CNN was doing the work of a second
    witness while barely speaking.

    ``witnesses`` carries families that qualify without scoring (see
    ``POINTLESS_WITNESS_RULES``). They are unioned in rather than filtered by
    ``min_contribution``, because that threshold answers "did this family say
    enough to count?" using points, and a family with no points is not saying
    nothing — it is saying something the score deliberately does not encode.

    Pass ``min_contribution=0`` to recover the v1.9 reading — used by the audit
    harness to measure what the threshold changed.
    """
    scored = {f for f, total in family_totals(rule_scores).items() if total >= min_contribution}
    return scored | (witnesses or set())
