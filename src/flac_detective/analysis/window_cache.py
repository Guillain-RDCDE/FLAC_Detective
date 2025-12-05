"""Window cache for optimized signal processing.

Phase 2 Optimization: Pre-calculate and cache Hann windows to avoid
redundant calculations.
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


def clear_window_cache():
    """Clear the window cache to free memory."""
    global _window_cache
    size = len(_window_cache)
    _window_cache.clear()
    logger.debug(f"⚡ WINDOW CACHE: Cleared {size} cached windows")


def get_cache_stats() -> Dict[str, int]:
    """Get statistics about the window cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        "cached_windows": len(_window_cache),
        "total_samples": sum(len(w) for w in _window_cache.values())
    }
