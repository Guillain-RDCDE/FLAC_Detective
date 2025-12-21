"""Audio cache for optimized file reading and spectral analysis.

Phase 3 Optimization: Avoid multiple file reads and spectrum calculations.
"""

import logging
from threading import Lock
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq, set_workers

from .window_cache import get_hann_window
from .new_scoring.audio_loader import load_audio_with_retry, sf_blocks_partial

logger = logging.getLogger(__name__)


class AudioCache:
    """Cache for audio data and spectral analysis results.

    Avoids multiple file reads and redundant FFT calculations.
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
        self._segments: dict = {}
        self._spectrum: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]] = None
        self._cutoff: Optional[float] = None
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

                    if data is None:
                        # Full load failed - try partial load
                        logger.warning(
                            f"CACHE: Full load failed for {self.filepath.name}, attempting partial load"
                        )
                        data_partial, sr_partial, is_complete = sf_blocks_partial(
                            str(self.filepath), original_filepath=str(self.original_filepath)
                        )

                        if data_partial is None:
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
                    if data is None:
                        # Segment load failure is less critical, maybe return empty?
                        # But let's be consistent and raise, caught by caller
                        raise RuntimeError(
                            f"Failed to load segment from {self.filepath} after retries"
                        )
                    self._segments[key] = (data, sr)
        else:
            logger.debug(f"CACHE: Using cached segment {start_frame}-{start_frame+frames}")

        return self._segments[key]

    def get_spectrum(
        self, segment_duration: float = 10.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get spectrum analysis (cached).

        Analyzes first segment_duration seconds of the file.

        Args:
            segment_duration: Duration in seconds to analyze

        Returns:
            Tuple of (frequencies, magnitude_db, sample_rate)
        """
        if self._spectrum is None:
            logger.debug(f"CACHE: Computing spectrum for {self.filepath.name}")

            data, sr = self.get_full_audio()

            # Use first segment_duration seconds
            frames_to_use = int(segment_duration * sr)
            if len(data) > frames_to_use:
                data = data[:frames_to_use]

            # Convert to mono
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]

            # Windowing
            # PHASE 2 OPTIMIZATION: Use cached window
            window = get_hann_window(len(data))
            data_windowed = data * window

            # FFT
            # PHASE 3 OPTIMIZATION: Use parallel FFT
            with set_workers(1):
                fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1 / sr)

            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            with self._lock:
                self._spectrum = (fft_freq, magnitude_db, sr)
        else:
            logger.debug(f"CACHE: Using cached spectrum for {self.filepath.name}")

        return self._spectrum

    def get_cutoff(self) -> float:
        """Get cutoff frequency (cached).

        Uses cached spectrum if available.

        Returns:
            Cutoff frequency in Hz
        """
        if self._cutoff is None:
            from ..spectrum import detect_cutoff

            logger.debug(f"CACHE: Computing cutoff for {self.filepath.name}")
            frequencies, magnitude_db, _ = self.get_spectrum()
            cutoff = detect_cutoff(frequencies, magnitude_db)
            with self._lock:
                self._cutoff = cutoff
        else:
            logger.debug(f"CACHE: Using cached cutoff for {self.filepath.name}")

        return self._cutoff

    def clear(self):
        """Clear all cached data."""
        logger.debug(f"CACHE: Clearing cache for {self.filepath.name}")
        self._full_audio = None
        self._segments.clear()
        self._spectrum = None
        self._cutoff = None
