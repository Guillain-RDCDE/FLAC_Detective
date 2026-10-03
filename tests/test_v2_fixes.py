"""The defects the 2.0 audit found, each pinned by the behaviour that was wrong.

Every test here failed on 1.21.0 for the reason its docstring gives.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from flac_detective.analysis import audio_formats
from flac_detective.analysis.diagnostic_tracker import (
    RESULT_ISSUES_KEY,
    DiagnosticTracker,
    IssueType,
    get_tracker,
    reset_tracker,
)
from flac_detective.analysis.new_scoring import audio_loader
from flac_detective.analysis.new_scoring.rules.spectral import apply_rule_2_cutoff
from flac_detective.analysis.quality import ClippingDetector, CorruptionDetector
from flac_detective.repair.encoding import reencode_flac

# ------------------------------------------------------------- diagnostics


def test_a_workers_issues_reach_the_parent_through_the_result():
    """The report was empty with more than one worker: the issues stayed in the child."""
    worker = DiagnosticTracker()
    worker.record_issue(
        "x.flac", IssueType.PARTIAL_READ, "short read", frames_read=10, total_frames=20
    )
    result = {"filepath": "x.flac", RESULT_ISSUES_KEY: worker.export_issues("x.flac")}

    parent = DiagnosticTracker()
    parent.absorb_result(result)
    parent.absorb_result(result)  # idempotent: an in-process run absorbs its own result

    stats = parent.get_statistics()
    assert stats["total_files"] == 1
    assert stats["files_with_issues"] == 1
    issues = parent.get_issues_for_file("x.flac")
    assert len(issues) == 1 and issues[0].issue_type is IssueType.PARTIAL_READ
    assert issues[0].frames_read == 10


def test_a_clean_result_counts_as_analysed_and_clean():
    parent = DiagnosticTracker()
    parent.absorb_result({"filepath": "y.flac", RESULT_ISSUES_KEY: []})
    assert parent.get_statistics() == {
        "total_files": 1,
        "files_with_issues": 0,
        "clean_files": 1,
        "issue_types": {},
        "critical_failures": 0,
    }


def test_an_error_row_is_still_a_file_analysed(tmp_path):
    """The counter was incremented on the success path only."""
    from flac_detective.analysis.analyzer import FLACAnalyzer

    reset_tracker()
    bad = tmp_path / "not-audio.flac"
    bad.write_bytes(b"not a flac at all")
    result = FLACAnalyzer().analyze_file(bad)
    assert result["verdict"] in ("ERROR", "NOT_ASSESSED")
    assert RESULT_ISSUES_KEY in result
    assert get_tracker().get_statistics()["total_files"] == 1


# ------------------------------------------------------------- the user's file


def test_an_analysis_read_never_rewrites_the_source_file(tmp_path):
    """load_audio_with_retry asked repair_flac_file to replace the source."""
    calls = []

    def fake_repair(corrupted_path, source_path=None, replace_source=False):
        calls.append(replace_source)
        return None

    with (
        patch.object(audio_loader.sf, "read", side_effect=RuntimeError("lost sync")),
        patch.object(audio_loader, "repair_flac_file", side_effect=fake_repair),
        patch.object(audio_loader.time, "sleep"),
    ):
        data, sr = audio_loader.load_audio_with_retry(
            str(tmp_path / "copy.flac"),
            max_attempts=2,
            original_filepath=str(tmp_path / "orig.flac"),
        )
    assert (data, sr) == (None, None)
    assert calls == [False]


def test_repair_in_place_is_an_explicit_request(tmp_path):
    """The same path, asked for: the source may then be replaced."""
    calls = []

    def fake_repair(corrupted_path, source_path=None, replace_source=False):
        calls.append((source_path, replace_source))
        return None

    with (
        patch.object(audio_loader.sf, "read", side_effect=RuntimeError("lost sync")),
        patch.object(audio_loader, "repair_flac_file", side_effect=fake_repair),
        patch.object(audio_loader.time, "sleep"),
    ):
        audio_loader.load_audio_with_retry(
            str(tmp_path / "copy.flac"),
            max_attempts=1,
            original_filepath=str(tmp_path / "orig.flac"),
            repair_in_place=True,
        )
    assert calls == [(str(tmp_path / "orig.flac"), True)]


def test_repair_temp_names_are_unique():
    a = audio_loader._unique_temp_path("repair_x_", ".wav")
    b = audio_loader._unique_temp_path("repair_x_", ".wav")
    try:
        assert a != b
        assert Path(a).name.startswith("repair_x_") and a.endswith(".wav")
    finally:
        Path(a).unlink(missing_ok=True)
        Path(b).unlink(missing_ok=True)


# ------------------------------------------------------------- repair encoding


@pytest.mark.parametrize("subtype", ["PCM_16", "PCM_24"])
def test_reencode_keeps_every_bit(tmp_path, subtype):
    """Level 5 (the default) wrote PCM_16: a 24-bit file lost its low 8 bits."""
    rng = np.random.default_rng(7)
    bits = 16 if subtype == "PCM_16" else 24
    samples = rng.integers(-(2 ** (bits - 1)), 2 ** (bits - 1), size=(4410, 2), dtype=np.int64)
    pcm = (samples << (32 - bits)).astype(np.int32)
    src = tmp_path / "src.flac"
    sf.write(src, pcm, 44100, format="FLAC", subtype=subtype)

    out = tmp_path / "out.flac"
    assert reencode_flac(src, out) is True
    assert sf.info(out).subtype == subtype
    back, _ = sf.read(out, dtype="int32")
    assert np.array_equal(back, pcm)


def test_reencode_refuses_a_subtype_flac_cannot_hold(tmp_path):
    src = tmp_path / "src.wav"
    sf.write(src, np.zeros((100, 1), dtype=np.float32), 44100, subtype="FLOAT")
    out = tmp_path / "out.flac"
    assert reencode_flac(src, out) is False
    assert not out.exists()


# ------------------------------------------------------------- quality


def test_clipping_percentage_is_over_samples_not_frames(tmp_path):
    """A fully clipped stereo file read 200 %."""
    full_scale = np.ones((2000, 2), dtype=np.float32)
    f = tmp_path / "clip.wav"
    sf.write(f, full_scale, 44100, subtype="FLOAT")
    result = ClippingDetector().detect(filepath=f)
    assert result["clipped_samples"] == 4000
    assert result["clipping_percentage"] == 100.0


def test_a_nan_in_the_middle_of_the_file_is_a_corruption(tmp_path):
    """Only the last block was checked."""
    data = np.zeros((16384 * 3, 1), dtype=np.float32)
    data[100, 0] = np.nan
    f = tmp_path / "nan.wav"
    sf.write(f, data, 44100, subtype="FLOAT")
    result = CorruptionDetector().detect(filepath=f)
    assert result["is_corrupted"] is True
    assert "NaN" in result["error"]


# ------------------------------------------------------------- rule text


def test_rule_2_reason_prints_the_points_it_scored():
    """17,250 Hz under a 20,000 Hz threshold is 13.75: scored 13, printed +14."""
    score, reasons = apply_rule_2_cutoff(17250.0, 44100)
    assert score == 13
    assert reasons and reasons[0].endswith("(+13pts)")


# ------------------------------------------------------------- ffmpeg decode


def test_decode_to_wav_leaves_no_temp_file_when_ffmpeg_cannot_run(tmp_path, monkeypatch):
    monkeypatch.setattr(audio_formats.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(audio_formats, "probe_stream", lambda p: None)
    monkeypatch.setattr(audio_formats, "_pcm_codec_for", lambda s: "pcm_s16le")
    created = []
    real_mkstemp = audio_formats.tempfile.mkstemp

    def recording_mkstemp(*a, **k):
        fd, name = real_mkstemp(*a, **k)
        created.append(Path(name))
        return fd, name

    monkeypatch.setattr(audio_formats.tempfile, "mkstemp", recording_mkstemp)
    monkeypatch.setattr(
        audio_formats.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("gone"))
    )
    assert audio_formats.decode_to_wav(tmp_path / "x.m4a") is None
    assert created and not created[0].exists()
