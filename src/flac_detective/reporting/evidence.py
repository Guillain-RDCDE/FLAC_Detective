"""The one line every report has to carry: which rule decided, and on how many witnesses.

Extracted from the text reporter in v1.13.13 so the GUI can print the same
line. Issue #8's second question showed why the extraction matters: a user
looking at a `Fake 63` in the GUI had the cutoff and the per-rule bullets but
no way to see that the whole accusation rested on one spectral reading. The
text report had said so since 1.13.11; the GUI, which is what he was looking
at, had not. One function, three surfaces (text, GUI, and whatever comes next),
so they cannot drift.
"""

from __future__ import annotations

from typing import Any

RULE_LABEL: dict[str, str] = {
    "Rule1MP3Bitrate": "MP3 bitrate signature",
    "Rule2Cutoff": "cutoff below the expected range",
    "Rule424BitSuspect": "24-bit with a low-bitrate source",
    "Rule5HighVariance": "high variable bitrate",
    "Rule6HighQualityProtection": "high-quality protection",
    "Rule7SilenceAnalysis": "silence analysis",
    "Rule8NyquistException": "spectrum reaches Nyquist",
    "Rule10Consistency": "multi-segment consistency",
    "Rule11CassetteDetection": "cassette source",
    "Rule12MLClassifier": "CNN classifier",
    "Rule13MDCTAlignment": "MDCT frame alignment",
    "Rule14TemporalSeam": "temporal seam",
    "Rule15StereoSeam": "stereo seam",
}


def deciding_evidence(result: dict[str, Any]) -> str:
    """What actually carried this verdict, in one line.

    Every report publishes the readings the engine took — score, format,
    cutoff, implied bitrate — and, until 1.13.11, not the one thing the reader
    actually wants: WHICH RULE DECIDED. That gap is not cosmetic. Issue #7 ran
    for three rounds with both sides believing the silence rule had convicted a
    file, because ``Issues: Silence: 1`` sat four lines above the table and
    read like a motive. It is a run-level count of audio-quality observations
    and contributes nothing to any score.

    Built from ``score_breakdown`` rather than by parsing the reason string,
    because that dict is the engine's own attribution and cannot drift from it.
    Returns an empty string when nothing accused and nothing protected.
    """
    breakdown = result.get("score_breakdown") or {}
    accusing = sorted(
        ((rule, pts) for rule, pts in breakdown.items() if pts > 0),
        key=lambda kv: -kv[1],
    )
    protecting = sorted(
        ((rule, pts) for rule, pts in breakdown.items() if pts < 0),
        key=lambda kv: kv[1],
    )
    if not accusing and not protecting:
        return ""

    def render(items: list) -> str:
        return ", ".join(f"{RULE_LABEL.get(rule, rule)} {pts:+d}" for rule, pts in items)

    parts = []
    if accusing:
        parts.append(render(accusing))
    if protecting:
        parts.append(f"offset by {render(protecting)}")

    # The witness count belongs here too: a conviction needs two independent
    # families, and a reader looking at a SUSPICIOUS file has no other way to
    # see whether one observation was counted twice or two things agreed.
    families = result.get("evidence_families") or []
    if families:
        plural = "family" if len(families) == 1 else "families"
        parts.append(f"{len(families)} evidence {plural}: {', '.join(families)}")

    return " — ".join(parts)
