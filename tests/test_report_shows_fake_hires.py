"""The text report prints the hi-res verdict.

Hi-res axis registration, 2026-10-07. ``hires_verdict`` reached the CSV, the
JSON and the GUI; the text report — default (easy) and ``--advanced`` — never
printed it, so a command-line user could scan a folder of upsampled "96 kHz"
files and read "All clear". Both modes now list them.
"""

from __future__ import annotations

from flac_detective.reporting.text_reporter import TextReporter


def _result(**overrides):
    base = {
        "filename": "track.flac",
        "filepath": "/music/track.flac",
        "verdict": "AUTHENTIC",
        "score": 0,
        "cutoff_freq": 22_000.0,
        "estimated_mp3_bitrate": 0,
        "sample_rate": 96_000,
        "bit_depth": 24,
        "reason": "",
        "hires_verdict": "NOT_HIRES",
        "hires_reason": "",
    }
    base.update(overrides)
    return base


UPSAMPLED = {
    "hires_verdict": "UPSAMPLED",
    "hires_reason": "Upsampled: spectral cliff at ~22.1 kHz (original rate ~44100 Hz)",
    "suspected_original_rate": 44_100,
}
PADDED = {
    "hires_verdict": "PADDED_DEPTH",
    "hires_reason": "Padded depth: 24-bit container holds only 16-bit data",
    "sample_rate": 44_100,
}


def _easy(tmp_path, results):
    out = tmp_path / "easy.txt"
    TextReporter(advanced=False).generate_report(results, out, scan_paths=[tmp_path])
    return out.read_text(encoding="utf-8")


def _advanced(tmp_path, results):
    out = tmp_path / "advanced.txt"
    TextReporter(advanced=True).generate_report(results, out, scan_paths=[tmp_path])
    return out.read_text(encoding="utf-8")


def test_easy_mode_lists_a_fake_hires_file_that_is_otherwise_authentic(tmp_path):
    text = _easy(tmp_path, [_result(filename="up.flac", **UPSAMPLED)])
    assert "FAKE HI-RES" in text
    assert "up.flac" in text
    assert "upsampled" in text  # the plain-language sentence
    assert "1 need attention" in text
    assert "All clear" not in text


def test_easy_mode_stays_clear_for_genuine_hires(tmp_path):
    text = _easy(tmp_path, [_result(hires_verdict="GENUINE_HIRES")])
    assert "All clear" in text
    assert "FAKE HI-RES" not in text


def test_easy_mode_does_not_list_a_flagged_transcode_twice(tmp_path):
    text = _easy(
        tmp_path, [_result(filename="both.flac", verdict="FAKE_CERTAIN", score=80, **UPSAMPLED)]
    )
    assert text.count("both.flac") == 1
    assert "1 need attention" in text


def test_advanced_mode_has_the_fake_hires_table_with_verdict_and_reason(tmp_path):
    text = _advanced(
        tmp_path,
        [_result(filename="up.flac", **UPSAMPLED), _result(filename="pad.flac", **PADDED)],
    )
    assert "FAKE HI-RES FILES (2)" in text
    assert "UPSAMPLED" in text and "PADDED_DEPTH" in text
    assert "why: Padded depth: 24-bit container holds only 16-bit data" in text
    assert "96/24" in text and "44.1/24" in text


def test_advanced_mode_says_none_when_there_are_none(tmp_path):
    text = _advanced(tmp_path, [_result()])
    assert "No fake hi-res files found." in text
