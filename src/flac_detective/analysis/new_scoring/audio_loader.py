"""Audio loading utilities with retry mechanism for handling temporary FLAC decoder errors."""

import logging
import time
from typing import Tuple, Optional
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def is_temporary_decoder_error(error_message: str) -> bool:
    """Check if an error is a temporary decoder error that should be retried.
    
    Args:
        error_message: The error message string
        
    Returns:
        True if the error is temporary and should be retried
    """
    temporary_error_patterns = [
        "lost sync",
        "decoder error",
        "sync error",
        "invalid frame",
        "unexpected end"
    ]
    
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in temporary_error_patterns)


def load_audio_with_retry(
    file_path: str,
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
    **kwargs
) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Load audio file with retry mechanism for temporary decoder errors.

    This function attempts to load a FLAC file using soundfile.read() with
    automatic retry on temporary decoder errors (e.g., "lost sync").

    Args:
        file_path: Path to the FLAC file
        max_attempts: Maximum number of attempts (default: 5)
        initial_delay: Initial delay between retries in seconds (default: 0.2)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        **kwargs: Additional keyword arguments to pass to soundfile.read()

    Returns:
        Tuple of (audio_data, sample_rate) on success, or (None, None) on failure
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Loading audio (attempt {attempt}/{max_attempts}): {file_path}")
            audio_data, sample_rate = sf.read(file_path, **kwargs)
            
            if attempt > 1:
                logger.info(f"✅ Audio loaded successfully on attempt {attempt}")
            
            return audio_data, sample_rate
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            # Check if this is a temporary error
            if is_temporary_decoder_error(error_msg):
                if attempt < max_attempts:
                    logger.warning(f"⚠️  Temporary error on attempt {attempt}: {error_msg}")
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(f"❌ Failed after {max_attempts} attempts: {error_msg}")
            else:
                # Not a temporary error, don't retry
                logger.error(f"Non-temporary error, not retrying: {error_msg}")
                break
    
    # All attempts failed
    return None, None


def sf_blocks(
    file_path: str,
    blocksize: int = 16384,
    dtype: str = "float32",
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Read audio in chunks with a retry mechanism for temporary errors.

    This function reads audio in chunks to avoid loading the entire file into
    memory at once. It includes a retry mechanism to handle temporary I/O
    issues during chunk-based reads. It reopens the file and seeks to the last
    known position on retries to ensure the file handle is not in a corrupted
    state.

    Args:
        file_path: Path to the audio file.
        blocksize: The size of each chunk to read.
        dtype: The data type to read.
        max_attempts: Maximum number of retry attempts.
        initial_delay: Initial delay between retries.
        backoff_multiplier: Multiplier for exponential backoff.

    Returns:
        A tuple containing the audio data and sample rate, or (None, None) if
        reading fails.
    """
    current_frame = 0
    try:
        total_frames = sf.info(file_path).frames
    except Exception as e:
        logger.error(f"Could not open or read info from {file_path}: {e}")
        return

    while current_frame < total_frames:
        delay = initial_delay
        read_successful = False
        for attempt in range(1, max_attempts + 1):
            try:
                with sf.SoundFile(file_path, "r") as f:
                    f.seek(current_frame)
                    chunk = f.read(blocksize, dtype=dtype)

                    if len(chunk) == 0:
                        current_frame = total_frames
                        read_successful = True
                        break

                    yield chunk
                    current_frame = f.tell()
                    read_successful = True
                    break

            except Exception as e:
                error_msg = str(e)
                if is_temporary_decoder_error(error_msg):
                    if attempt < max_attempts:
                        logger.warning(
                            f"⚠️  Temporary error on attempt {attempt} reading from frame {current_frame}: {error_msg}"
                        )
                        logger.info(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        logger.error(
                            f"❌ Failed to read from frame {current_frame} after {max_attempts} attempts: {error_msg}"
                        )
                else:
                    logger.error(
                        f"Non-temporary error reading from frame {current_frame}, not retrying: {error_msg}"
                    )
                    current_frame = total_frames
                    break

        if not read_successful:
            break


def load_audio_segment(
    file_path: str,
    start_sec: float,
    duration_sec: float,
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Load a specific segment of an audio file with retry logic."""
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            with sf.SoundFile(file_path, "r") as f:
                sr = f.samplerate
                start_frame = int(start_sec * sr)
                frames_to_read = int(duration_sec * sr)
                f.seek(start_frame)
                data = f.read(frames_to_read)
                return data, sr
        except Exception as e:
            error_msg = str(e)
            if is_temporary_decoder_error(error_msg):
                if attempt < max_attempts:
                    logger.warning(
                        f"⚠️  Temporary error loading segment on attempt {attempt}: {error_msg}"
                    )
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(
                        f"❌ Failed to load audio segment after {max_attempts} attempts: {error_msg}"
                    )
            else:
                logger.error(f"Non-temporary error loading audio segment: {error_msg}")
                break
    return None, None