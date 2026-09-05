"""The report has to say which rule decided, and which line is not a reason.

The sequel to ``test_report_shows_format``, from the same issue and the same
principle taken one layer further: a verdict without the reading it was made from
is an opinion — and the readings were already published while the inference was
not.

Issue #7 ran for three rounds with both the reporter and the maintainer believing
a silence rule had convicted a file. It had not. ``Issues: Silence: 1`` is a
run-level tally of audio-quality observations that contributes nothing to any
score, and it was printed four lines above the verdict table with no label saying
so. The reporter cited it twice in writing as the motive; so did the maintainer's
first analysis of his report. The rule that actually decided — the MP3-bitrate
signature — appeared nowhere in the report at all.

Both halves are pinned here: what the table must now say, and what the tally must
no longer be mistaken for.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.reporting.text_reporter import TextReporter  # noqa: E402


def _result(**overrides):
    """The reporter's own case: a genuine 18.2 kHz master read as a 224 kbps MP3.

    Score 58 = Rule 1's +50 for the bitrate signature plus Rule 2's +8 for the low
    cutoff. Both belong to the ``spectral`` family, so a single observation is
    carrying the whole accusation — which is precisely what the reader cannot see
    without this line.
    """
    base = {
        "filename": "04.flac",
        "filepath": "/music/04.flac",
        "verdict": "SUSPICIOUS",
        "score": 58,
        "cutoff_freq": 18_250.0,
        "estimated_mp3_bitrate": 224,
        "sample_rate": 44_100,
        "bit_depth": 16,
        "reason": "",
        "score_breakdown": {"Rule1MP3Bitrate": 50, "Rule2Cutoff": 8},
        "evidence_families": ["spectral"],
        "has_silence_issue": True,
    }
    base.update(overrides)
    return base


def test_the_deciding_rule_is_named():
    reporter = TextReporter()
    why = reporter._deciding_evidence(_result())
    assert "MP3 bitrate signature" in why
    assert "+50" in why
    assert "cutoff below the expected range" in why


def test_the_witness_count_is_shown():
    """A reader of a SUSPICIOUS row cannot otherwise tell one source from two."""
    reporter = TextReporter()
    assert "1 evidence family: spectral" in reporter._deciding_evidence(_result())
    two = _result(
        score_breakdown={"Rule1MP3Bitrate": 50, "Rule12MLClassifier": 30},
        evidence_families=["cnn", "spectral"],
    )
    assert "2 evidence families: cnn, spectral" in reporter._deciding_evidence(two)


def test_protective_rules_are_shown_as_offsets():
    """A file cleared by a protection deserves to know which one, too."""
    reporter = TextReporter()
    why = reporter._deciding_evidence(
        _result(score_breakdown={"Rule1MP3Bitrate": 50, "Rule8NyquistException": -50})
    )
    assert "offset by" in why and "spectrum reaches Nyquist -50" in why


def test_a_rule_with_no_label_still_prints_its_name():
    """Silence is the failure mode here; an unnamed rule must not disappear."""
    reporter = TextReporter()
    why = reporter._deciding_evidence(_result(score_breakdown={"Rule99Whatever": 40}))
    assert "Rule99Whatever +40" in why


def test_a_file_with_no_attribution_says_nothing_rather_than_guessing():
    reporter = TextReporter()
    assert reporter._deciding_evidence(_result(score_breakdown={})) == ""
    assert reporter._deciding_evidence(_result(score_breakdown=None)) == ""


def test_the_written_report_carries_the_reason_next_to_the_verdict(tmp_path):
    """Checked on the file the reporter actually writes, not on the helper."""
    out = tmp_path / "report.txt"
    TextReporter().generate_report(
        [_result(filepath=str(tmp_path / "04.flac"))], out, scan_paths=[tmp_path]
    )
    text = out.read_text(encoding="utf-8", errors="replace")
    assert "why:" in text
    assert "MP3 bitrate signature" in text

    # and the reason must sit with its verdict, not in some later section
    lines = text.splitlines()
    verdict_line = next(i for i, ln in enumerate(lines) if "SUSPICIOUS" in ln and "58/100" in ln)
    assert "why:" in lines[verdict_line + 1], "le motif doit suivre immediatement le verdict"


def test_the_quality_tally_no_longer_reads_as_a_motive(tmp_path):
    """The exact misreading that cost this issue two of its three rounds."""
    out = tmp_path / "report.txt"
    TextReporter().generate_report(
        [_result(filepath=str(tmp_path / "04.flac"))], out, scan_paths=[tmp_path]
    )
    text = out.read_text(encoding="utf-8", errors="replace")

    assert "Silence: 1" in text, "le compteur reste affiche, il informe"
    assert "do not affect any verdict" in text, "il doit dire qu'il ne pese pas sur le verdict"
    # The bare label is what invited the inference; it must not come back.
    assert "\n Issues: " not in text
