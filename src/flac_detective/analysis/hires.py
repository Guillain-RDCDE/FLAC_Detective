"""Fake high-resolution detection: upsampling and padded bit depth.

A *separate axis* from the transcode (lossy→lossless) verdict. A file can be a
genuine lossless CD rip and still be a **fake hi-res** product:

* **Upsampled** — 44.1/48 kHz content resampled to 88.2/96/176/192 kHz and sold
  as "hi-res". The giveaway is a hard spectral **cliff** at the *original*
  Nyquist (≈22.05 / 24 kHz) with **digital silence** above it — a real 96 kHz
  recording keeps an analog/dither floor up to its own Nyquist; an upsample has
  literally nothing up there because the samples were invented by interpolation.
* **Padded depth** — 16-bit audio written into a 24-bit container, the low 8 bits
  all zero. Detected by :class:`...quality.BitDepthDetector` (already shipped).

The cliff test deliberately reuses the same discriminator as Rule 1's
near-Nyquist gate (a *silent* floor vs an *analog* floor): a natural high-Nyquist
rolloff is NOT flagged, only an interpolation cliff with digital silence above it.
This keeps faith with "protect authentic files first" — a real 96 kHz recording
that simply has little ultrasonic content must read GENUINE_HIRES, not UPSAMPLED.

The verdict labels (analogous to the transcode traffic light):

* ``GENUINE_HIRES``        — >48 kHz / >16-bit with real content; keep it.
* ``UPSAMPLED``            — resampled from a lower rate (cliff + silent floor).
* ``PADDED_DEPTH``         — 24-bit container holding only 16-bit data.
* ``UPSAMPLED_AND_PADDED`` — both.
* ``NOT_HIRES``            — standard CD-quality (≤48 kHz, ≤16-bit); axis N/A.
* ``UNKNOWN``              — analysis unavailable (too short / decode failed).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Standard "original" sample rates a fake hi-res file is typically upsampled FROM.
# A cliff at one of these rates' Nyquist (rate/2) is the upsampling fingerprint.
_STANDARD_SOURCE_RATES = (44100, 48000, 88200, 96000)

# A detected content edge counts as "at" a candidate Nyquist if within this
# fraction of it (resamplers don't land exactly on rate/2 — there's transition band).
_NYQUIST_TOLERANCE = 0.06  # ±6%

# Floor above the cliff, relative to the in-band reference, below which we call it
# digital silence (an interpolation void) rather than a natural analog rolloff.
# Same spirit as spectrum.compute_residual_floor_db's −55 dB near-Nyquist gate;
# a touch stricter here because a true upsample void is profoundly empty (≈ −90 dB).
_SILENT_FLOOR_DB = -70.0

# Verdict labels.
GENUINE_HIRES = "GENUINE_HIRES"
UPSAMPLED = "UPSAMPLED"
PADDED_DEPTH = "PADDED_DEPTH"
UPSAMPLED_AND_PADDED = "UPSAMPLED_AND_PADDED"
NOT_HIRES = "NOT_HIRES"
UNKNOWN = "UNKNOWN"


def detect_upsampling(audio: np.ndarray, samplerate: int) -> dict:  # noqa: C901
    """Detect sample-rate upsampling from the decoded audio.

    Args:
        audio: PCM samples, mono or multi-channel float array.
        samplerate: The file's reported sample rate (Hz).

    Returns:
        A dict ``{is_upsampled, suspected_original_rate, content_edge_hz,
        floor_above_db}``. ``floor_above_db`` is the median spectral level just
        above the content edge minus the in-band reference (NaN if unknown). For
        ``samplerate <= 48000`` upsampling is not applicable and ``is_upsampled`` is
        False with ``suspected_original_rate == samplerate``.
    """
    result = {
        "is_upsampled": False,
        "suspected_original_rate": samplerate,
        "content_edge_hz": float("nan"),
        "floor_above_db": float("nan"),
    }
    if samplerate <= 48000:
        return result

    # Welch-averaged magnitude spectrum (reuse the spectrum module's helper so the
    # estimate matches the rest of the pipeline). Mono-sum first.
    from .spectrum import _welch_magnitude_db

    data = audio
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    data = np.asarray(data[: int(30.0 * samplerate)], dtype=np.float64)
    freq, mag_db = _welch_magnitude_db(data, samplerate)
    if freq is None or mag_db is None:
        return result

    nyq = samplerate / 2.0
    in_band = (freq >= 0.05 * nyq) & (freq <= 0.45 * nyq)
    if not np.any(in_band):
        return result
    ref = float(np.median(mag_db[in_band]))

    # Find the actual CONTENT EDGE: the highest frequency whose smoothed level is
    # still within 40 dB of the in-band reference. Above an upsampling cliff there
    # is digital silence, so the edge sits at the original Nyquist; for genuine
    # hi-res the edge runs close to the file's own Nyquist. Smoothing (~500 Hz)
    # rejects isolated bins so a lone noise spike near Nyquist can't fake an edge.
    from scipy.ndimage import uniform_filter1d

    # A one-bin spectrum has no bin width to speak of, and the smoothing size
    # below would be derived from a fabricated 1.0 Hz. Typed as "unanalysable"
    # rather than defaulted: same species as cutoff_wander's NaN, caught by
    # ml/typed_absence_audit.py shape C on 2026-08-30.
    if len(freq) < 2:
        return result
    bin_hz = freq[1] - freq[0]
    smooth_bins = max(3, int(round(500.0 / max(bin_hz, 1e-6))))
    mag_smooth = uniform_filter1d(mag_db, size=smooth_bins)
    above_thresh = np.where(mag_smooth >= ref - 40.0)[0]
    if above_thresh.size == 0:
        return result
    content_edge = float(freq[above_thresh[-1]])

    # Genuine hi-res: content reaches near the file's own Nyquist — not upsampled.
    if content_edge >= 0.92 * nyq:
        return result

    # Snap the edge to the nearest standard original Nyquist (rate/2). If it doesn't
    # land near a known rate, this isn't a recognised upsample — stay conservative.
    best_rate = None
    for r0 in _STANDARD_SOURCE_RATES:
        if r0 >= samplerate:
            continue
        n0 = r0 / 2.0
        if abs(content_edge - n0) <= _NYQUIST_TOLERANCE * n0:
            if best_rate is None or n0 > best_rate / 2.0:
                best_rate = r0
    if best_rate is None:
        return result

    # Confirm a HARD cliff to digital silence above the edge (vs a gentle analog
    # rolloff, which would keep an analog/dither floor — that's genuine, not a fake).
    above = (freq > content_edge * 1.03) & (freq <= 0.98 * nyq)
    if not np.any(above):
        return result
    floor_rel = float(np.median(mag_db[above])) - ref
    if floor_rel >= _SILENT_FLOOR_DB:
        return result  # floor is too high to be an interpolation void

    result.update(
        {
            "is_upsampled": True,
            "suspected_original_rate": best_rate,
            "content_edge_hz": content_edge,
            "floor_above_db": floor_rel,
        }
    )
    return result


def classify_hires(
    sample_rate: Optional[int],
    bit_depth: Optional[int],
    is_upsampled: bool,
    suspected_original_rate: int,
    is_fake_high_res: bool,
    estimated_depth: int,
    floor_above_db: float = float("nan"),
) -> Tuple[str, List[str]]:
    """Combine upsampling + bit-depth signals into a single hi-res verdict.

    Args:
        sample_rate: Reported sample rate (Hz).
        bit_depth: Reported bit depth.
        is_upsampled: From :func:`detect_upsampling`.
        suspected_original_rate: From :func:`detect_upsampling`.
        is_fake_high_res: From the bit-depth detector (24-bit holding 16-bit data).
        estimated_depth: The detector's estimated true depth.
        floor_above_db: Silent-floor margin (for the human-readable reason).

    Returns:
        ``(verdict_label, reasons)``. ``NOT_HIRES`` when neither high rate nor high
        depth is claimed (the axis doesn't apply), and also when either is
        **unknown** — with a reason that says so, rather than silently.

    ``sample_rate`` and ``bit_depth`` are Optional because ``read_metadata``
    returns ``{}`` on any exception: a file whose header could not be read has no
    rate, and until v1.13.2 the caller coerced that absence to ``0``, which reads
    here as "not high rate" and produced a confident ``NOT_HIRES`` with no reason
    attached. It now returns ``UNKNOWN``, which is what that label has always
    meant — "analysis unavailable" — and which ``gui/worker.py`` already emits on
    its own failure path, so no consumer meets a value it has not seen before.
    """
    if sample_rate is None or bit_depth is None:
        unknown = "sample rate" if sample_rate is None else "bit depth"
        return UNKNOWN, [f"Hi-res axis not evaluated: {unknown} unknown (header unreadable)"]

    is_high_rate = sample_rate > 48000
    is_high_depth = bit_depth > 16
    if not is_high_rate and not is_high_depth:
        return NOT_HIRES, []

    reasons: List[str] = []
    upsampled = bool(is_upsampled and is_high_rate)
    padded = bool(is_fake_high_res and is_high_depth)

    if upsampled:
        edge = ""
        if not np.isnan(floor_above_db):
            edge = f", {floor_above_db:.0f} dB void above the cliff"
        reasons.append(
            f"Upsampled: spectral cliff at ~{suspected_original_rate / 2 / 1000:.1f} kHz "
            f"(original rate ~{suspected_original_rate} Hz) with digital silence above"
            f"{edge} — sold as {sample_rate} Hz hi-res"
        )
    if padded:
        reasons.append(
            f"Padded depth: {bit_depth}-bit container holds only {estimated_depth}-bit data "
            f"(the low {bit_depth - estimated_depth} bits are silent)"
        )

    if upsampled and padded:
        return UPSAMPLED_AND_PADDED, reasons
    if upsampled:
        return UPSAMPLED, reasons
    if padded:
        return PADDED_DEPTH, reasons

    # Claims hi-res and we found no upsampling / padding evidence.
    return GENUINE_HIRES, ["Genuine high-resolution: real content above the CD band"]
