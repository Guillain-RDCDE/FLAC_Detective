"""Tests for the CSV (library-triage) report writer."""

from __future__ import annotations

import csv

from flac_detective.reporting import CSVReporter


def _rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_csv_is_ranked_most_suspicious_first(tmp_path):
    """Rows must be sorted by descending score, with a 1-based rank column."""
    results = [
        {"filename": "a.flac", "score": 10, "verdict": "AUTHENTIC", "cutoff_freq": 22050.0},
        {"filename": "b.flac", "score": 95, "verdict": "FAKE_CERTAIN", "cutoff_freq": 16000.0},
        {"filename": "c.flac", "score": 58, "verdict": "SUSPICIOUS", "cutoff_freq": 19000.0},
    ]
    out = tmp_path / "report.csv"
    CSVReporter().generate_report(results, out)

    rows = _rows(out)
    assert [r["filename"] for r in rows] == ["b.flac", "c.flac", "a.flac"]
    assert [r["rank"] for r in rows] == ["1", "2", "3"]
    assert [r["score"] for r in rows] == ["95", "58", "10"]


def test_csv_header_and_columns(tmp_path):
    out = tmp_path / "r.csv"
    CSVReporter().generate_report([{"filename": "x.flac", "score": 0, "verdict": "AUTHENTIC"}], out)
    rows = _rows(out)
    assert set(rows[0].keys()) == {
        "rank",
        "score",
        "verdict",
        "hires_verdict",
        "filename",
        "cutoff_freq_hz",
        "sample_rate",
        "bit_depth",
        "reason",
        "filepath",
    }
    # Cutoff rounds to an int; absent cutoff stays blank.
    assert rows[0]["cutoff_freq_hz"] == ""
    # Hi-res verdict blank for an ordinary file (no/NOT_HIRES value).
    assert rows[0]["hires_verdict"] == ""


def test_csv_cutoff_rounded_and_reason_single_line(tmp_path):
    results = [
        {
            "filename": "y.flac",
            "score": 60,
            "verdict": "SUSPICIOUS",
            "cutoff_freq": 16384.7,
            "reason": "R2: cutoff low\nR9: artefacts",
        }
    ]
    out = tmp_path / "r.csv"
    CSVReporter().generate_report(results, out)
    row = _rows(out)[0]
    assert row["cutoff_freq_hz"] == "16385"  # rounded
    assert "\n" not in row["reason"] and "R2: cutoff low R9: artefacts" == row["reason"]


def test_csv_handles_empty_results(tmp_path):
    """No results → just the header row, no crash."""
    out = tmp_path / "empty.csv"
    CSVReporter().generate_report([], out)
    assert _rows(out) == []
    assert out.read_text(encoding="utf-8").startswith("rank,score,verdict")
