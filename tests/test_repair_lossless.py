"""End-to-end proof that FLAC repair is lossless and safe.

The mock-based tests in tests/unit/test_repair_functions.py cover the repair
*orchestration*. These tests use the real `flac` CLI to prove the property that
matters for a hi-fi audience: repairing a FLAC returns the **exact same PCM
samples** (bit for bit), keeps a backup, and preserves metadata. The whole module
is skipped if the `flac` binary isn't on PATH.
"""

from __future__ import annotations

import os
import shutil

import numpy as np
import pytest

sf = pytest.importorskip("soundfile")

if shutil.which("flac") is None:
    pytest.skip("the `flac` CLI is not on PATH", allow_module_level=True)

from flac_detective.analysis.new_scoring.audio_loader import repair_flac_file  # noqa: E402


def _make_flac(path, seconds=2.0, sr=44100):
    """Write a deterministic stereo FLAC and return its exact PCM samples."""
    rng = np.random.default_rng(7)
    pcm = (rng.standard_normal((int(sr * seconds), 2)) * 0.25).astype(np.float32)
    sf.write(str(path), pcm, sr, format="FLAC", subtype="PCM_16")
    # Read back what the FLAC actually stores (16-bit ints) — this is ground truth.
    data, _ = sf.read(str(path), dtype="int16")
    return data


def test_repair_roundtrip_is_bit_identical(tmp_path):
    """The core hi-fi guarantee: repaired audio == original audio, sample for sample."""
    src = tmp_path / "song.flac"
    original_pcm = _make_flac(src)

    # Repair into a temp file (no source replacement) and decode it back.
    repaired = repair_flac_file(corrupted_path=str(src))
    assert repaired is not None, "repair returned no file"
    try:
        repaired_pcm, _ = sf.read(repaired, dtype="int16")
        # Bit-for-bit identical: repair re-encodes the same PCM, it does not process audio.
        assert repaired_pcm.shape == original_pcm.shape
        assert np.array_equal(repaired_pcm, original_pcm)
    finally:
        os.remove(repaired)


def test_repair_preserves_metadata(tmp_path):
    """Tags survive the repair round-trip."""
    from mutagen.flac import FLAC

    src = tmp_path / "tagged.flac"
    _make_flac(src)
    audio = FLAC(str(src))
    audio["title"] = "Test Title"
    audio["artist"] = "Test Artist"
    audio.save()

    repaired = repair_flac_file(corrupted_path=str(src))
    assert repaired is not None
    try:
        tags = FLAC(repaired)
        assert tags.get("title") == ["Test Title"]
        assert tags.get("artist") == ["Test Artist"]
    finally:
        os.remove(repaired)


def test_repair_replace_source_keeps_backup(tmp_path):
    """replace_source=True overwrites the original but always leaves a .bak first."""
    src = tmp_path / "replaceme.flac"
    original_pcm = _make_flac(src)
    original_bytes = src.read_bytes()

    repaired = repair_flac_file(corrupted_path=str(src), source_path=str(src), replace_source=True)
    assert repaired is not None
    try:
        backup = tmp_path / "replaceme.flac.corrupted.bak"
        # A backup of the pre-repair original must exist, byte-identical to the original.
        assert backup.exists(), "no .corrupted.bak backup was written"
        assert backup.read_bytes() == original_bytes
        # The (now replaced) source is still a valid, lossless FLAC of the same audio.
        replaced_pcm, _ = sf.read(str(src), dtype="int16")
        assert np.array_equal(replaced_pcm, original_pcm)
    finally:
        if os.path.exists(repaired):
            os.remove(repaired)
