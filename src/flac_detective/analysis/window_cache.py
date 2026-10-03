"""Process-wide cache of Hann windows, keyed by size.

Both getters share ONE dictionary keyed only by the window length, so whichever
of ``scipy.signal.windows.hann`` or ``numpy.hanning`` fills a size first is what
every later caller of either getter receives. The two differ by up to 4.4e-16
per sample. Rule 7's 30 s music segment and the spectrum pass's 30 s window are
the same length, so on files over 90 s Rule 7 already gets the scipy window.
Separating the keys is therefore a measured change to the engine (last-digit
floats move), not a refactor: leave the shared dictionary alone unless a
before/after pass on labelled files is part of the change.
"""

import logging
from typing import Dict

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Global window cache
_window_cache: Dict[int, np.ndarray] = {}


def get_hann_window(size: int) -> np.ndarray:
    """Get cached Hann window of specified size.

    PHASE 2 OPTIMIZATION: Windows are calculated once and cached.

    Args:
        size: Window size in samples

    Returns:
        Hann window array
    """
    if size not in _window_cache:
        logger.debug(f"⚡ WINDOW CACHE: Creating Hann window of size {size}")
        _window_cache[size] = signal.windows.hann(size)
    else:
        logger.debug(f"⚡ WINDOW CACHE: Using cached Hann window of size {size}")

    return _window_cache[size]


def get_hanning_window(size: int) -> np.ndarray:
    """Get cached Hanning window (alias for Hann).

    PHASE 2 OPTIMIZATION: Windows are calculated once and cached.

    Args:
        size: Window size in samples

    Returns:
        Hanning window array
    """
    if size not in _window_cache:
        logger.debug(f"⚡ WINDOW CACHE: Creating Hanning window of size {size}")
        _window_cache[size] = np.hanning(size)
    else:
        logger.debug(f"⚡ WINDOW CACHE: Using cached Hanning window of size {size}")

    return _window_cache[size]
