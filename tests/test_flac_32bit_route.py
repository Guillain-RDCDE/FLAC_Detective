"""A 32-bit integer FLAC is analysed, not an ERROR.

Hi-res axis registration, 2026-10-07. FLAC 1.4 encodes up to 32-bit samples;
libsndfile 1.2 implements 8, 16 and 24 and refuses the file ("data in an
unimplemented format"). Such a file ended in ERROR. It now goes through the
ffmpeg façade like an ALAC would, its header still read from the FLAC itself
(the declared 32 bits are what the hi-res axis has to judge), and the depth
detector reads the bits the samples actually use.

Needs the ``flac`` CLI to make the file (libsndfile cannot write one) and
``ffmpeg`` to decode it; skipped without either.
"""

from __future__ import annotations

import shutil
import subprocess

import numpy as np
import pytest
import soundfile as sf

if shutil.which("flac") is None or shutil.which("ffmpeg") is None:
    pytest.skip("the `flac` and `ffmpeg` CLIs are needed", allow_module_level=True)

from flac_detective.analysis.analyzer import (  # noqa: E402
    _flac_wider_than_libsndfile_reads,
    _read_source_metadata,
    _stage_local_copy,
)
from flac_detective.analysis.quality import BitDepthDetector  # noqa: E402


def _make_32bit_flac(tmp_path, bits: int):
    """A 32-bit FLAC whose samples use ``bits`` bits (16 = CD audio padded)."""
    rng = np.random.default_rng(bits)
    n = 44_100 * 3
    data = rng.integers(-(2 ** (bits - 1)), 2 ** (bits - 1), size=(n, 2), dtype=np.int64)
    data[data == 0] = 1
    pcm = (data << (32 - bits)).astype(np.int32)
    wav = tmp_path / f"src{bits}.wav"
    sf.write(str(wav), pcm, 44_100, subtype="PCM_32")
    flac = tmp_path / f"wide{bits}.flac"
    subprocess.run(["flac", "-f", "-s", "-o", str(flac), str(wav)], check=True)
    return flac


def test_libsndfile_refuses_it_and_the_header_says_why(tmp_path):
    flac = _make_32bit_flac(tmp_path, 16)
    with pytest.raises(sf.LibsndfileError):
        sf.info(str(flac))
    assert _flac_wider_than_libsndfile_reads(flac) is True


def test_a_24_bit_flac_is_not_rerouted(tmp_path):
    path = tmp_path / "ordinary.flac"
    sf.write(str(path), np.zeros((44_100, 2), dtype=np.int32), 44_100, subtype="PCM_24")
    assert _flac_wider_than_libsndfile_reads(path) is False
    staged, decoded = _stage_local_copy(path)
    try:
        assert decoded is False
        assert staged.suffix == ".flac"
    finally:
        staged.unlink(missing_ok=True)


def test_staged_through_ffmpeg_with_the_flac_header_kept(tmp_path):
    flac = _make_32bit_flac(tmp_path, 16)
    staged, decoded = _stage_local_copy(flac)
    try:
        assert decoded is True
        assert staged.suffix == ".wav"
        assert sf.info(str(staged)).subtype == "PCM_24"
        metadata = _read_source_metadata(flac, staged, decoded)
        assert metadata["bit_depth"] == 32
        assert metadata["sample_rate"] == 44_100
        # The depth detector reads the decoded copy against the declared depth.
        out = BitDepthDetector().detect(filepath=staged, reported_depth=metadata["bit_depth"])
        assert out["is_fake_high_res"] is True
        assert out["estimated_depth"] == 16
    finally:
        staged.unlink(missing_ok=True)


def test_true_24_bit_content_in_a_32_bit_flac_reads_24(tmp_path):
    """The façade keeps 24 bits, so 24-bit content in a 32-bit container reads 24.

    A true 32-bit source would read 24 as well: the low 8 bits are dropped by
    the decode. That is the stated limit, not a defect the test hides.
    """
    flac = _make_32bit_flac(tmp_path, 24)
    staged, decoded = _stage_local_copy(flac)
    try:
        out = BitDepthDetector().detect(filepath=staged, reported_depth=32)
        assert out["estimated_depth"] == 24
    finally:
        staged.unlink(missing_ok=True)
