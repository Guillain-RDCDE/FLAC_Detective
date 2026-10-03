"""A downsampled, peak-normalised magnitude spectrum for display.

Shared by the HTML report (inline SVG) and the GUI (matplotlib panel), so both
draw the same curve. This is a presentation reading, not an engine one: it uses
``numpy.hanning`` and a middle segment of its own, and nothing in the scoring
pipeline depends on it.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# A 10 s middle segment, downsampled to this many points (enough to render the
# cliff cleanly, small enough to keep an HTML page compact).
CURVE_POINTS = 240
CURVE_SECONDS = 10.0
DB_FLOOR = -100.0  # clamp the normalised magnitude floor (peak = 0 dB)


def compute_spectrum_curve(
    filepath: str,
) -> Optional[Tuple[List[float], List[float], float]]:
    """Compute a downsampled, peak-normalised magnitude spectrum for a file.

    Reads a middle segment, mono-mixes, applies a Hann window, takes the rfft,
    converts to dB, downsamples to ``CURVE_POINTS`` (max-per-bin, which preserves
    the cliff edge), and normalises so the peak is 1.0 and ``DB_FLOOR`` is 0.0.

    Returns ``(freqs_hz, norm_0_1, nyquist_hz)`` or ``None`` if the file cannot be
    read (the caller renders a placeholder instead of failing).
    """
    if not filepath:
        return None
    try:
        import numpy as np
        import soundfile as sf

        info = sf.info(filepath)
        sr = int(info.samplerate)
        total_frames = int(info.frames)
        if sr <= 0 or total_frames <= 0:
            return None

        seg_frames = min(int(CURVE_SECONDS * sr), total_frames)
        start = max(0, (total_frames - seg_frames) // 2)
        data, sr = sf.read(filepath, start=start, frames=seg_frames, always_2d=True)
        if data.size == 0:
            return None

        mono = data.mean(axis=1)
        window = np.hanning(len(mono))
        mag = np.abs(np.fft.rfft(mono * window))
        freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
        mag_db = 20.0 * np.log10(mag + 1e-10)

        # Downsample to a fixed number of points by max-per-bin (keeps the cliff).
        n = min(CURVE_POINTS, len(mag_db))
        if n < 2:
            return None
        idx = np.linspace(0, len(mag_db), n + 1).astype(int)
        ds_db = np.array([mag_db[idx[i] : max(idx[i] + 1, idx[i + 1])].max() for i in range(n)])
        ds_freq = np.array([float(freqs[min(idx[i], len(freqs) - 1)]) for i in range(n)])

        # Peak-normalise to 0..1 with a fixed dB floor.
        peak = float(ds_db.max())
        norm = (ds_db - peak - DB_FLOOR) / (-DB_FLOOR)
        norm = np.clip(norm, 0.0, 1.0)

        return ds_freq.tolist(), norm.tolist(), float(sr) / 2.0
    except Exception as exc:  # pragma: no cover - defensive: any decode/read failure
        logger.debug(f"Spectrum curve unavailable for {filepath}: {exc}")
        return None
