"""The depth detector reads the file, not its first tenth of a second.

Hi-res axis registration, 2026-10-07. Until 2.2.0 ``BitDepthDetector`` read the
first 10,000 frames of the left channel and decided "16-bit exact" on them. A
genuine 24-bit track that opens with digital silence or a fade-in was labelled
PADDED_DEPTH on that chunk. It now reads eight windows spread over the file,
skips silence, and estimates 16, 24 or 32 bits from the trailing zero bits the
samples actually carry — which also covers a 32-bit container (integer or
float), which the old test never estimated.
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from flac_detective.analysis.quality import BitDepthDetector, estimate_true_depth

SR = 48_000


def _int24_noise(n: int, seed: int, bits: int) -> np.ndarray:
    """Random samples that use exactly ``bits`` bits, left-justified in int32."""
    rng = np.random.default_rng(seed)
    full = rng.integers(-(2 ** (bits - 1)), 2 ** (bits - 1), size=n, dtype=np.int64)
    full[full == 0] = 1  # every sample non-zero: the depth must be read from data
    return (full << (32 - bits)).astype(np.int32)


def _write(path, data: np.ndarray, subtype: str) -> None:
    """Write left-justified int32 samples in ``subtype``.

    A float file gets the samples SCALED to [-1, 1), as every encoder writes
    them (ffmpeg's pcm_f32le, a DAW export): sf.write would otherwise store the
    raw integers as floats, which no real file does and which libsndfile reads
    back unscaled — the case that hid the float defect found on 2026-10-07.
    """
    if subtype in ("FLOAT", "DOUBLE"):
        sf.write(str(path), data.astype(np.float64) / 2147483648.0, SR, subtype=subtype)
    else:
        sf.write(str(path), data, SR, subtype=subtype)


def test_genuine_24_bit_with_a_silent_opening_is_not_padded(tmp_path):
    """Two seconds of digital silence, then real 24-bit audio: True 24-bit.

    The 1.x detector read only the silence and called the file padded.
    """
    silence = np.zeros(2 * SR, dtype=np.int32)
    audio = _int24_noise(6 * SR, seed=1, bits=24)
    path = tmp_path / "fade.wav"
    _write(path, np.concatenate([silence, audio]), "PCM_24")
    out = BitDepthDetector().detect(filepath=path, reported_depth=24)
    assert out["is_fake_high_res"] is False
    assert out["estimated_depth"] == 24


def test_16_bit_data_in_a_24_bit_container_is_padded(tmp_path):
    path = tmp_path / "padded.wav"
    _write(path, _int24_noise(8 * SR, seed=2, bits=16), "PCM_24")
    out = BitDepthDetector().detect(filepath=path, reported_depth=24)
    assert out["is_fake_high_res"] is True
    assert out["estimated_depth"] == 16


def test_a_single_window_of_full_depth_audio_clears_the_file(tmp_path):
    """16-bit-looking everywhere except its last second: the file does use 24 bits.

    The windows are samples of the file, not the whole file: the stretch has to
    fall under one of them (here the last window, which ends at the last frame),
    and one window that carries 24-bit audio is enough to clear it.
    """
    sixteen = _int24_noise(8 * SR, seed=3, bits=16)
    sixteen[-SR:] = _int24_noise(SR, seed=4, bits=24)
    path = tmp_path / "mostly16.wav"
    _write(path, sixteen, "PCM_24")
    out = estimate_true_depth(path)
    assert out["estimated_depth"] == 24


@pytest.mark.parametrize("subtype", ["PCM_32", "FLOAT"])
def test_16_bit_data_in_a_32_bit_container_is_read_as_16(tmp_path, subtype):
    """A 32-bit container (integer or float) holding CD audio: estimated 16."""
    path = tmp_path / f"wide_{subtype}.wav"
    _write(path, _int24_noise(4 * SR, seed=5, bits=16), subtype)
    out = BitDepthDetector().detect(filepath=path, reported_depth=32)
    assert out["is_fake_high_res"] is True
    assert out["estimated_depth"] == 16


def test_true_32_bit_data_is_read_as_32(tmp_path):
    path = tmp_path / "true32.wav"
    _write(path, _int24_noise(4 * SR, seed=6, bits=32), "PCM_32")
    out = BitDepthDetector().detect(filepath=path, reported_depth=32)
    assert out["is_fake_high_res"] is False
    assert out["estimated_depth"] == 32


def test_an_all_silent_file_is_not_assessed(tmp_path):
    """No non-zero sample anywhere: there is no depth to read, and no accusation."""
    path = tmp_path / "silent.wav"
    _write(path, np.zeros(3 * SR, dtype=np.int32), "PCM_24")
    out = BitDepthDetector().detect(filepath=path, reported_depth=24)
    assert out["is_fake_high_res"] is False
    assert out["estimated_depth"] == 24
    assert "not assessed" in out["details"]


def test_a_short_file_is_read_whole(tmp_path):
    """Shorter than eight windows: every frame is read once, nothing is skipped."""
    path = tmp_path / "short.wav"
    _write(path, _int24_noise(15_000, seed=7, bits=24), "PCM_24")
    out = estimate_true_depth(path)
    assert out["windows_read"] == 2
    assert out["nonzero_samples"] == 15_000
    assert out["estimated_depth"] == 24


def test_16_bit_container_is_never_questioned(tmp_path):
    path = tmp_path / "cd.wav"
    _write(path, _int24_noise(SR, seed=8, bits=16), "PCM_16")
    out = BitDepthDetector().detect(filepath=path, reported_depth=16)
    assert out == {"is_fake_high_res": False, "estimated_depth": 16}
