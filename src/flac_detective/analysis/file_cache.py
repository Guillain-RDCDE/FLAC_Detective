"""File I/O cache wrapper for optimized audio file reading.

Phase 3 Optimization: Cache file reads to avoid redundant I/O operations.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class FileReadCache:
    """Global cache for file read operations.

    Caches full file reads and segments to avoid redundant I/O.
    Thread-safe for parallel execution.
    """

    _instance: Optional['FileReadCache'] = None

    def __init__(self):
        """Initialize the cache."""
        self._full_reads: Dict[str, Tuple[np.ndarray, int]] = {}
        self._segment_reads: Dict[Tuple[str, int, int], Tuple[np.ndarray, int]] = {}
        self._enabled = True

    @classmethod
    def get_instance(cls) -> 'FileReadCache':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the cache (useful for testing)."""
        if cls._instance is not None:
            cls._instance.clear()

    def enable(self):
        """Enable caching."""
        self._enabled = True
        logger.debug("CACHE: Enabled")

    def disable(self):
        """Disable caching."""
        self._enabled = False
        logger.debug("CACHE: Disabled")

    def clear(self):
        """Clear all cached data."""
        self._full_reads.clear()
        self._segment_reads.clear()
        logger.debug("CACHE: Cleared")

    def read_full(self, filepath: Path, **kwargs) -> Tuple[np.ndarray, int]:
        """Read full file with caching.

        Args:
            filepath: Path to audio file
            **kwargs: Additional arguments for sf.read

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not self._enabled:
            return sf.read(str(filepath), **kwargs)

        key = str(filepath)

        if key not in self._full_reads:
            logger.debug(f"CACHE MISS: Reading full file {filepath.name}")
            data, sr = sf.read(str(filepath), **kwargs)
            self._full_reads[key] = (data, sr)
            logger.debug(f"CACHE: Stored full file {filepath.name} ({data.shape}, {sr} Hz)")
        else:
            logger.debug(f"CACHE HIT: Using cached full file {filepath.name}")

        return self._full_reads[key]

    def read_segment(
        self,
        filepath: Path,
        start: int,
        frames: int,
        **kwargs
    ) -> Tuple[np.ndarray, int]:
        """Read file segment with caching.

        Args:
            filepath: Path to audio file
            start: Starting frame
            frames: Number of frames to read
            **kwargs: Additional arguments for sf.read

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not self._enabled:
            return sf.read(str(filepath), start=start, frames=frames, **kwargs)

        key = (str(filepath), start, frames)

        if key not in self._segment_reads:
            logger.debug(f"CACHE MISS: Reading segment {filepath.name}[{start}:{start+frames}]")
            data, sr = sf.read(str(filepath), start=start, frames=frames, **kwargs)
            self._segment_reads[key] = (data, sr)
            logger.debug(f"CACHE: Stored segment {filepath.name}[{start}:{start+frames}] ({data.shape})")
        else:
            logger.debug(f"CACHE HIT: Using cached segment {filepath.name}[{start}:{start+frames}]")

        return self._segment_reads[key]

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            'full_reads_cached': len(self._full_reads),
            'segment_reads_cached': len(self._segment_reads),
            'total_cached': len(self._full_reads) + len(self._segment_reads),
        }


# Global cache instance
_cache = FileReadCache.get_instance()


def cached_read(filepath: Path, start: Optional[int] = None, frames: Optional[int] = None, **kwargs):
    """Cached version of soundfile.read.

    Automatically uses cache for full reads and segments.

    Args:
        filepath: Path to audio file
        start: Optional starting frame for segment read
        frames: Optional number of frames for segment read
        **kwargs: Additional arguments for sf.read

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    if start is not None and frames is not None:
        return _cache.read_segment(filepath, start, frames, **kwargs)
    else:
        return _cache.read_full(filepath, **kwargs)


def enable_cache():
    """Enable file read caching."""
    _cache.enable()


def disable_cache():
    """Disable file read caching."""
    _cache.disable()


def clear_cache():
    """Clear file read cache."""
    _cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    return _cache.get_stats()
