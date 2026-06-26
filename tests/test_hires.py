"""Tests for fake high-resolution detection (analysis/hires.py).

Two layers: ``classify_hires`` (pure label logic) and ``detect_upsampling``
(spectral, exercised on synthetic signals — a band-limited-then-upsampled file
vs a genuine broadband hi-res file — so no real audio is needed).
"""

from __future__ import annotations

import numpy as np

from flac_detective.analysis import hires

# ---------------------------------------------------------------------------
# classify_hires — pure label logic
# ---------------------------------------------------------------------------


def test_cd_quality_is_not_hires():
    """44.1 kHz / 16-bit: the hi-res axis does not apply."""
    verdict, reasons = hires.classify_hires(44100, 16, False, 44100, False, 16)
    assert verdict == hires.NOT_HIRES
    assert reasons == []


def test_genuine_hires():
    """High rate + high depth with no upsample/pad evidence -> GENUINE_HIRES."""
    verdict, _ = hires.classify_hires(96000, 24, False, 96000, False, 24)
    assert verdict == hires.GENUINE_HIRES


def test_upsampled_label():
    """A detected upsample on a high-rate file -> UPSAMPLED."""
    verdict, reasons = hires.classify_hires(96000, 24, True, 44100, False, 24, floor_above_db=-85.0)
    assert verdict == hires.UPSAMPLED
    assert any("Upsampled" in r for r in reasons)


def test_padded_depth_label():
    """24-bit container holding 16-bit data, standard rate -> PADDED_DEPTH."""
    verdict, reasons = hires.classify_hires(44100, 24, False, 44100, True, 16)
    assert verdict == hires.PADDED_DEPTH
    assert any("Padded depth" in r for r in reasons)


def test_upsampled_and_padded():
    """Both fake signals present -> the combined label."""
    verdict, _ = hires.classify_hires(96000, 24, True, 48000, True, 16)
    assert verdict == hires.UPSAMPLED_AND_PADDED


# ---------------------------------------------------------------------------
# detect_upsampling — synthetic spectral tests
# ---------------------------------------------------------------------------


def _bandlimited_noise(sr, n_seconds, cutoff_hz, seed=0):
    """White noise hard-bandlimited below cutoff_hz (digital silence above)."""
    rng = np.random.default_rng(seed)
    n = int(sr * n_seconds)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    X[freqs > cutoff_hz] = 0.0  # hard brickwall -> silence above (the upsample void)
    return np.fft.irfft(X, n=n).astype(np.float32)


def test_rate_at_or_below_48k_not_applicable():
    """<=48 kHz can't be a fake-hi-res upsample; detector returns not-upsampled."""
    sig = _bandlimited_noise(44100, 6, 15000)
    out = hires.detect_upsampling(sig, 44100)
    assert out["is_upsampled"] is False
    assert out["suspected_original_rate"] == 44100


def test_upsampled_from_44k_detected():
    """96 kHz holding only <22.05 kHz content (silent above) -> upsampled from 44.1k."""
    sig = _bandlimited_noise(96000, 6, 22050, seed=1)
    out = hires.detect_upsampling(sig, 96000)
    assert out["is_upsampled"] is True
    assert out["suspected_original_rate"] == 44100
    assert out["floor_above_db"] < hires._SILENT_FLOOR_DB


def test_genuine_hires_not_flagged():
    """Broadband 96 kHz noise (content up to ~Nyquist) is NOT flagged as upsampled."""
    sig = _bandlimited_noise(96000, 6, 46000, seed=2)  # content nearly to 48 kHz
    out = hires.detect_upsampling(sig, 96000)
    assert out["is_upsampled"] is False


def test_natural_rolloff_with_analog_floor_not_flagged():
    """A soft rolloff that keeps a high floor above the edge is genuine, not a cliff."""
    # Full-band noise scaled down (not zeroed) above 22.05 kHz: an analog-like floor,
    # ~25 dB down — above the silent-floor threshold, so it must NOT be called upsampled.
    rng = np.random.default_rng(3)
    sr, n = 96000, 96000 * 6
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    X[freqs > 22050] *= 10 ** (-25 / 20)  # -25 dB, not silence
    sig = np.fft.irfft(X, n=n).astype(np.float32)
    out = hires.detect_upsampling(sig, sr)
    assert out["is_upsampled"] is False
