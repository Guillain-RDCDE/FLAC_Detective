"""Audio loading utilities with retry mechanism for handling temporary FLAC decoder errors."""

import logging
import time
from typing import Tuple, Optional
import numpy as np
import soundfile as sf
import tempfile
import shutil
import subprocess
import os

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
        "unexpected end",
        "unknown error"  # NEW: Can occur on valid files, worth retrying
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
                    logger.debug(f"Temporary error on attempt {attempt}: {error_msg}")
                    logger.debug(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(f"❌ Failed after {max_attempts} attempts: {error_msg}")
            else:
                # Not a temporary error, don't retry
                logger.error(f"Non-temporary error, not retrying: {error_msg}")
                break
    
    # All attempts failed, try to repair and load again
    logger.debug(f"All attempts to load {file_path} failed. Attempting repair...")
    repaired_path = repair_flac_file(file_path)

    if repaired_path:
        try:
            audio_data, sample_rate = sf.read(repaired_path, **kwargs)
            logger.info(f"✅ Successfully loaded repaired file: {repaired_path}")
            os.remove(repaired_path)
            return audio_data, sample_rate
        except Exception as e:
            logger.error(f"❌ Failed to load repaired file {repaired_path}: {e}")
            os.remove(repaired_path)

    return None, None


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
                    logger.debug(
                        f"Temporary error loading segment on attempt {attempt}: {error_msg}"
                    )
                    logger.debug(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(
                        f"❌ Failed to load audio segment after {max_attempts} attempts: {error_msg}"
                    )
            else:
                logger.error(f"Non-temporary error loading audio segment: {error_msg}")
                break

    # All attempts failed, try to repair and load again
    logger.debug(f"All attempts to load segment from {file_path} failed. Attempting repair...")
    repaired_path = repair_flac_file(file_path)

    if repaired_path:
        try:
            with sf.SoundFile(repaired_path, "r") as f:
                sr = f.samplerate
                start_frame = int(start_sec * sr)
                frames_to_read = int(duration_sec * sr)
                f.seek(start_frame)
                data = f.read(frames_to_read)
                logger.info(f"✅ Successfully loaded segment from repaired file: {repaired_path}")
                os.remove(repaired_path)
                return data, sr
        except Exception as e:
            logger.error(f"❌ Failed to load segment from repaired file {repaired_path}: {e}")
            os.remove(repaired_path)

    return None, None


def repair_flac_file(original_path: str) -> Optional[str]:
    """Repair a FLAC file by re-encoding it with the official FLAC tool.

    Args:
        original_path: Path to the possibly corrupted FLAC file.

    Returns:
        Path to the repaired temporary file, or None on failure.
    """
    try:
        # Create a temporary file to store the repaired version
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"repaired_{os.path.basename(original_path)}")

        shutil.copy2(original_path, temp_path)

        logger.info(f"Attempting to repair {original_path} at {temp_path}")

        # Use the FLAC command-line tool to re-encode and fix errors
        command = [
            "flac",
            "--best",
            "--verify",
            "-f",  # Force overwrite of the temporary file
            temp_path
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            logger.info(f"✅ Successfully repaired {original_path}")
            return temp_path
        else:
            logger.error(f"❌ Failed to repair {original_path}. Error: {result.stderr}")
            os.remove(temp_path)
            return None

    except (FileNotFoundError, shutil.Error, subprocess.SubprocessError) as e:
        logger.error(f"❌ An exception occurred during FLAC repair: {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return None


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
                        logger.debug(
                            f"Temporary error on attempt {attempt} reading from frame {current_frame}: {error_msg}"
                        )
                        logger.debug(f"Retrying in {delay:.1f}s...")
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


def sf_blocks_partial(
    file_path: str,
    blocksize: int = 16384,
    dtype: str = "float32",
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Tuple[Optional[np.ndarray], Optional[int], bool]:
    """Read audio in chunks, returning partial data if full read fails.

    This function attempts to read an entire audio file in blocks. If reading
    fails mid-stream due to decoder errors, it returns whatever data was
    successfully read before the error occurred, allowing for partial analysis.

    Args:
        file_path: Path to the audio file.
        blocksize: The size of each chunk to read.
        dtype: The data type to read.
        max_attempts: Maximum number of retry attempts per block.
        initial_delay: Initial delay between retries.
        backoff_multiplier: Multiplier for exponential backoff.

    Returns:
        Tuple of (audio_data, sample_rate, is_complete):
        - audio_data: Concatenated audio chunks (None if no data read)
        - sample_rate: Sample rate of the audio file (None if cannot read info)
        - is_complete: True if entire file was read, False if partial
    """
    chunks = []
    sample_rate = None
    current_frame = 0

    try:
        info = sf.info(file_path)
        sample_rate = info.samplerate
        total_frames = info.frames
    except Exception as e:
        logger.error(f"Cannot read file info from {file_path}: {e}")
        return None, None, False

    logger.debug(f"Starting partial block read of {file_path} ({total_frames} frames)")

    # Read chunks until we hit an error or reach end
    while current_frame < total_frames:
        delay = initial_delay
        read_successful = False

        for attempt in range(1, max_attempts + 1):
            try:
                with sf.SoundFile(file_path, "r") as f:
                    f.seek(current_frame)
                    chunk = f.read(blocksize, dtype=dtype)

                    if len(chunk) == 0:
                        # Reached end of file
                        logger.debug(f"Reached end of file at frame {current_frame}")
                        current_frame = total_frames
                        read_successful = True
                        break

                    chunks.append(chunk)
                    current_frame = f.tell()
                    read_successful = True
                    break

            except Exception as e:
                error_msg = str(e)

                if is_temporary_decoder_error(error_msg):
                    if attempt < max_attempts:
                        logger.debug(
                            f"Temporary error on attempt {attempt} reading from frame {current_frame}: {error_msg}"
                        )
                        logger.debug(f"Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        # Max attempts reached - return what we have
                        logger.debug(
                            f"Failed to read from frame {current_frame} after {max_attempts} attempts"
                        )
                        if chunks:
                            logger.info(f"Returning partial data: {current_frame}/{total_frames} frames ({len(chunks)} chunks)")
                            combined = np.concatenate(chunks)
                            return combined, sample_rate, False  # Not complete
                        else:
                            logger.error("No data could be read before error")
                            return None, None, False
                else:
                    # Non-temporary error
                    logger.error(
                        f"Non-temporary error reading from frame {current_frame}: {error_msg}"
                    )
                    if chunks:
                        logger.info(f"Returning partial data: {current_frame}/{total_frames} frames")
                        combined = np.concatenate(chunks)
                        return combined, sample_rate, False  # Not complete
                    else:
                        return None, None, False

        if not read_successful:
            # Failed to read this block
            break

    # Successfully read entire file
    if chunks:
        combined = np.concatenate(chunks)
        is_complete = (current_frame >= total_frames)
        logger.debug(f"Read {current_frame}/{total_frames} frames ({'complete' if is_complete else 'partial'})")
        return combined, sample_rate, is_complete
    else:
        logger.error("No data could be read")
        return None, None, False