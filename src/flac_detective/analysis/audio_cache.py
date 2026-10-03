"""Per-file audio cache: one decode, shared by every rule that reads the audio."""

import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Tuple

import numpy as np

from .new_scoring.audio_loader import load_audio_with_retry, sf_blocks_partial

logger = logging.getLogger(__name__)


class AudioCache:
    """Cache for the decoded audio of one file (full read and segments).

    Created by the analyzer for each file and cleared when the file is done, so
    the spectrum, quality and scoring passes read the file from disk once.
    """

    def __init__(self, filepath: Path, original_filepath: Optional[Path] = None):
        """Initialize cache for a specific file.

        Args:
            filepath: Path to the audio file (may be temporary)
            original_filepath: Original file path (for diagnostic reporting)
        """
        self.filepath = filepath
        self.original_filepath = original_filepath or filepath
        self._full_audio: Optional[Tuple[np.ndarray, int]] = None
        self._segments: Dict[Tuple[int, int], Tuple[np.ndarray, int]] = {}
        self._lock = Lock()
        self._is_partial = False  # Track if audio data is partial

    def get_full_audio(self) -> Tuple[np.ndarray, int]:
        """Get full audio data (cached).

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if self._full_audio is None:
            with self._lock:
                if self._full_audio is None:  # Double-check pattern
                    logger.debug(f"CACHE: Loading full audio from {self.filepath.name}")
                    data, sr = load_audio_with_retry(
                        str(self.filepath),
                        always_2d=True,
                        original_filepath=str(self.original_filepath),
                    )

                    if data is None or sr is None:
                        # Full load failed - try partial load
                        logger.warning(
                            f"CACHE: Full load failed for {self.filepath.name}, attempting partial load"
                        )
                        data_partial, sr_partial, is_complete = sf_blocks_partial(
                            str(self.filepath), original_filepath=str(self.original_filepath)
                        )

                        if data_partial is None or sr_partial is None:
                            raise RuntimeError(
                                f"Failed to load any audio data from {self.filepath}"
                            )

                        # Convert to 2D if needed (to match always_2d=True behavior)
                        if data_partial.ndim == 1:
                            data = data_partial.reshape(-1, 1)
                        else:
                            data = data_partial

                        sr = sr_partial
                        self._is_partial = not is_complete

                        logger.info(
                            f"CACHE: Loaded partial audio: {len(data)} frames ({'complete' if is_complete else 'partial'})"
                        )

                    self._full_audio = (data, sr)
        else:
            logger.debug(f"CACHE: Using cached full audio for {self.filepath.name}")

        assert self._full_audio is not None
        return self._full_audio

    def is_partial(self) -> bool:
        """Check if cached audio is partial (incomplete read).

        Returns:
            True if audio data is partial, False otherwise
        """
        return self._is_partial

    def get_segment(self, start_frame: int, frames: int) -> Tuple[np.ndarray, int]:
        """Get audio segment (cached).

        Args:
            start_frame: Starting frame
            frames: Number of frames to read

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        key = (start_frame, frames)

        if key not in self._segments:
            with self._lock:
                if key not in self._segments:  # Double-check pattern
                    logger.debug(
                        f"CACHE: Loading segment {start_frame}-{start_frame+frames} from {self.filepath.name}"
                    )
                    data, sr = load_audio_with_retry(
                        str(self.filepath),
                        start=start_frame,
                        frames=frames,
                        always_2d=True,
                        original_filepath=str(self.original_filepath),
                    )
                    if data is None or sr is None:
                        # Segment load failure is less critical, maybe return empty?
                        # But let's be consistent and raise, caught by caller
                        raise RuntimeError(
                            f"Failed to load segment from {self.filepath} after retries"
                        )
                    self._segments[key] = (data, sr)
        else:
            logger.debug(f"CACHE: Using cached segment {start_frame}-{start_frame+frames}")

        return self._segments[key]

    def clear(self):
        """Clear all cached data."""
        logger.debug(f"CACHE: Clearing cache for {self.filepath.name}")
        self._full_audio = None
        self._segments.clear()
