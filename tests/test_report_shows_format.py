"""The report has to say what it read, not only what it concluded.

From issue #7. Someone had one album in four containers, saw the FLAC flagged and
the WAV clean, and reasonably concluded the wrapper was deciding the verdict. The
likely answer was that one file was 24-bit and another 16-bit — different audio,
which the engine is entitled to read differently — and the text report never said
so. The CSV and the HTML carried the bit depth; the report most people read did
not, so the one fact that would have ended the question in three seconds was the
one fact missing.

A verdict without the reading it was made from is an opinion.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.reporting.text_reporter import TextReporter  # noqa: E402


def _result(**overrides):
    base = {
        "filename": "track.flac",
        "filepath": "/music/track.flac",
        "verdict": "SUSPICIOUS",
        "score": 55,
        "cutoff_freq": 18_200.0,
        "estimated_mp3_bitrate": 224,
        "sample_rate": 44_100,
        "bit_depth": 16,
        "reason": "",
    }
    base.update(overrides)
    return base


def test_the_format_column_shows_rate_and_depth():
    reporter = TextReporter()
    assert reporter._format_label(_result()) == "44.1/16"
    assert reporter._format_label(_result(sample_rate=96_000, bit_depth=24)) == "96/24"


def test_an_unknown_reading_is_not_a_plausible_default():
    """A missing bit depth prints as unknown, never as 16.

    Filling it in would put a number in the column that nothing measured, which
    is the defect this column exists to prevent, one layer down.
    """
    reporter = TextReporter()
    assert reporter._format_label(_result(bit_depth=None)) == "44.1/?"
    assert reporter._format_label(_result(sample_rate=None)) == "?/16"
    assert reporter._format_label(_result(sample_rate=None, bit_depth=None)) == "-"


def test_two_files_that_differ_only_in_depth_are_distinguishable_in_the_report(tmp_path):
    """The whole point: the written report must not hide the difference.

    Two rows identical except for bit depth used to render identically, which is
    what let a 24-bit file and its 16-bit truncation look like a container bug.
    Checked on the file the reporter actually writes, not on a helper.
    """
    out = tmp_path / "report.txt"
    TextReporter().generate_report(
        [
            _result(filename="a.flac", filepath=str(tmp_path / "a.flac"), bit_depth=24),
            _result(filename="a.wav", filepath=str(tmp_path / "a.wav"), bit_depth=16),
        ],
        out,
        scan_paths=[tmp_path],
    )
    text = out.read_text(encoding="utf-8", errors="replace")
    assert "44.1/24" in text
    assert "44.1/16" in text
    assert "Format" in text, "la colonne doit etre nommee dans l'en-tete"
