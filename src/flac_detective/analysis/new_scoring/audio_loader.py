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
    max_attempts: int = 3,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 1.5
) -> Tuple[Optional[np.ndarray], Optional[int]]:
    """Load audio file with retry mechanism for temporary decoder errors.
    
    This function attempts to load a FLAC file using soundfile.read() with
    automatic retry on temporary decoder errors (e.g., "lost sync").
    
    Args:
        file_path: Path to the FLAC file
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 0.2)
        backoff_multiplier: Multiplier for exponential backoff (default: 1.5)
        
    Returns:
        Tuple of (audio_data, sample_rate) on success, or (None, None) on failure
        
    Example:
        >>> audio, sr = load_audio_with_retry("file.flac")
        >>> if audio is not None:
        ...     # Process audio
        ...     pass
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Loading audio (attempt {attempt}/{max_attempts}): {file_path}")
            audio_data, sample_rate = sf.read(file_path)
            
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
