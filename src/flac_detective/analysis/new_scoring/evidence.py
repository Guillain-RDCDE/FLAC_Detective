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
    Rules 1, 2, 3 and 4. All of them read the spectral cutoff or the MP3 bitrate
    inferred *from* that cutoff — Rule 3 compares Rule 1's inference against the
    container, and Rule 4 gates on the same inference. However many of them fire,
    they are one look at one thing.
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

from typing import Dict, Mapping, Set

# Rule class name -> evidence family. A rule absent from this map contributes no
# family, which is the safe default: a new rule cannot silently earn conviction
# power just by existing.
RULE_FAMILY: Dict[str, str] = {
    "Rule1MP3Bitrate": "spectral",
    "Rule2Cutoff": "spectral",
    "Rule3SourceVsContainer": "spectral",
    "Rule424BitSuspect": "spectral",
    "Rule5HighVariance": "container",
    "Rule7SilenceAnalysis": "silence",
    "Rule12MLClassifier": "cnn",
    "Rule13MDCTAlignment": "mdct",
}


def evidence_families(rule_scores: Mapping[str, int]) -> Set[str]:
    """Return the set of independent evidence families that accuse this file.

    Only *positive* contributions count. A protection rule handing out negative
    points is not evidence of guilt, and a rule that ran and found nothing has
    said nothing.
    """
    return {family for rule, family in RULE_FAMILY.items() if rule_scores.get(rule, 0) > 0}
