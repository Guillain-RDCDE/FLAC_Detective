"""Audio loading utilities with retry mechanism for handling temporary FLAC decoder errors."""

import logging
import time
from typing import Tuple, Optional, Dict, List, Any, Generator
import numpy as np
from numpy.typing import NDArray
import soundfile as sf
import tempfile
import shutil
import subprocess
import os

from ..diagnostic_tracker import get_tracker, IssueType

# Type variable for mutagen availability
MUTAGEN_AVAILABLE: bool

try:
    from mutagen.flac import FLAC, Picture

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

logger: logging.Logger = logging.getLogger(__name__)


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
        "unknown error",  # NEW: Can occur on valid files, worth retrying
    ]

    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in temporary_error_patterns)


def load_audio_with_retry(
    file_path: str,
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
    original_filepath: Optional[str] = None,
    **kwargs: Any,
) -> Tuple[Optional[NDArray[np.float64]], Optional[int]]:
    """Load audio file with retry mechanism for temporary decoder errors.

    This function attempts to load a FLAC file using soundfile.read() with
    automatic retry on temporary decoder errors (e.g., "lost sync").

    Args:
        file_path: Path to the FLAC file
        max_attempts: Maximum number of attempts (default: 5)
        initial_delay: Initial delay between retries in seconds (default: 0.2)
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0)
        original_filepath: Original file path for diagnostic reporting (default: None)
        **kwargs: Additional keyword arguments to pass to soundfile.read()

    Returns:
        Tuple of (audio_data, sample_rate) on success, or (None, None) on failure
    """
    # Use original filepath for diagnostic tracking, or file_path if not provided
    tracking_path: str = original_filepath or file_path

    delay: float = initial_delay
    last_error: Optional[Exception] = None

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
                    logger.warning(f"Failed after {max_attempts} attempts: {error_msg}")
                    # Track this issue
                    get_tracker().record_issue(
                        filepath=tracking_path,
                        issue_type=(
                            IssueType.DECODER_SYNC_LOST
                            if "lost sync" in error_msg.lower()
                            else IssueType.READ_FAILED
                        ),
                        message=error_msg,
                        retry_count=max_attempts,
                    )
            else:
                # Not a temporary error, don't retry
                logger.warning(f"Non-temporary error, not retrying: {error_msg}")
                get_tracker().record_issue(
                    filepath=tracking_path,
                    issue_type=IssueType.READ_FAILED,
                    message=f"Non-temporary error: {error_msg}",
                    retry_count=attempt,
                )
                break

    # All attempts failed, try to repair and load again
    logger.debug(f"All attempts to load {file_path} failed. Attempting repair...")
    get_tracker().record_issue(
        filepath=tracking_path,
        issue_type=IssueType.REPAIR_ATTEMPTED,
        message="Attempting FLAC repair after read failures",
    )
    # Repair the corrupted file and replace the original source if successful
    repaired_path = repair_flac_file(
        corrupted_path=file_path,
        source_path=original_filepath,
        replace_source=True,  # Replace source file on successful repair
    )

    if repaired_path:
        try:
            audio_data, sample_rate = sf.read(repaired_path, **kwargs)
            logger.info(f"✅ Successfully loaded repaired file: {repaired_path}")
            os.remove(repaired_path)
            return audio_data, sample_rate
        except Exception as e:
            logger.warning(f"Failed to load repaired file {repaired_path}: {e}")
            get_tracker().record_issue(
                filepath=tracking_path,
                issue_type=IssueType.REPAIR_FAILED,
                message=f"Repair failed: {str(e)}",
            )
            os.remove(repaired_path)
    else:
        get_tracker().record_issue(
            filepath=tracking_path,
            issue_type=IssueType.REPAIR_FAILED,
            message="FLAC repair process returned no file",
        )

    return None, None


def load_audio_segment(
    file_path: str,
    start_sec: float,
    duration_sec: float,
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Tuple[Optional[NDArray[np.float64]], Optional[int]]:
    """Load a specific segment of an audio file with retry logic."""
    delay: float = initial_delay
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
    # Note: load_audio_segment doesn't have original_filepath, so no source replacement here
    repaired_path = repair_flac_file(corrupted_path=file_path)

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


def _extract_metadata(flac_path: str) -> Optional[Dict[str, Any]]:
    """Extract all metadata from a FLAC file including tags and embedded pictures.

    This function uses the Mutagen library to read all Vorbis comment tags and
    embedded pictures (album art) from a FLAC file. The extracted metadata can
    be used to preserve this information when repairing corrupted FLAC files.

    Args:
        flac_path: Absolute or relative path to the FLAC file to extract metadata from.

    Returns:
        Dictionary with 'tags' and 'pictures' keys on success:
            - 'tags': Dict[str, List[str]] mapping tag names to their values
            - 'pictures': List[Picture] containing all embedded images
        Returns None if:
            - Mutagen library is not available
            - File cannot be read
            - Metadata extraction fails

    Examples:
        >>> metadata = _extract_metadata("song.flac")
        >>> if metadata:
        ...     print(f"Tags: {len(metadata['tags'])}")
        ...     print(f"Pictures: {len(metadata['pictures'])}")
        ...     # Example tags: {'TITLE': ['My Song'], 'ARTIST': ['Artist Name']}
        Tags: 5
        Pictures: 1

        >>> # Handle missing Mutagen gracefully
        >>> metadata = _extract_metadata("song.flac")
        >>> if metadata is None:
        ...     print("Metadata extraction not available or failed")
        Metadata extraction not available or failed

    Note:
        - Requires the 'mutagen' library to be installed
        - Preserves multi-value tags (e.g., multiple artists)
        - All tag names are case-sensitive as per FLAC/Vorbis specification
        - Common tags include: TITLE, ARTIST, ALBUM, DATE, GENRE, TRACKNUMBER
    """
    if not MUTAGEN_AVAILABLE:
        logger.warning("Mutagen not available - metadata will not be preserved")
        return None

    try:
        audio: FLAC = FLAC(flac_path)

        # Extract all tags
        tags: Dict[str, List[str]] = {}
        if audio.tags:
            for key, value in audio.tags:  # type: ignore[union-attr]
                if key not in tags:
                    tags[key] = []
                tags[key].extend(value if isinstance(value, list) else [value])

        # Extract all pictures (album art)
        pictures: List[Picture] = list(audio.pictures) if audio.pictures else []

        logger.debug(f"  Extracted {len(tags)} tag types and {len(pictures)} picture(s)")

        return {"tags": tags, "pictures": pictures}

    except Exception as e:
        logger.warning(f"Failed to extract metadata: {e}")
        return None


def _restore_metadata(flac_path: str, metadata: Optional[Dict[str, Any]]) -> bool:
    """Restore metadata to a FLAC file from a previously extracted metadata dictionary.

    This function writes Vorbis comment tags and embedded pictures back to a FLAC
    file, typically used after repairing a corrupted file to preserve its original
    metadata. All existing metadata in the target file is cleared before restoration
    to ensure an exact match with the source metadata.

    Args:
        flac_path: Absolute or relative path to the FLAC file to restore metadata to.
                   The file must exist and be a valid FLAC file.
        metadata: Dictionary containing metadata to restore, must have the structure:
                  {
                      'tags': Dict[str, List[str]],  # Tag names to values
                      'pictures': List[Picture]       # Embedded images
                  }
                  Can be None, in which case the function returns False.

    Returns:
        True if metadata was successfully restored and saved.
        False if:
            - Mutagen library is not available
            - metadata parameter is None or empty
            - File cannot be opened or written
            - Metadata restoration fails for any reason

    Examples:
        >>> # Extract and restore metadata during repair
        >>> original_metadata = _extract_metadata("corrupted.flac")
        >>> # ... repair process creates "repaired.flac" ...
        >>> success = _restore_metadata("repaired.flac", original_metadata)
        >>> if success:
        ...     print("Metadata successfully restored")
        Metadata successfully restored

        >>> # Restore specific metadata
        >>> metadata = {
        ...     'tags': {
        ...         'TITLE': ['My Song'],
        ...         'ARTIST': ['Artist Name'],
        ...         'ALBUM': ['Album Title']
        ...     },
        ...     'pictures': []  # No album art
        ... }
        >>> _restore_metadata("new_file.flac", metadata)
        True

        >>> # Handle missing metadata gracefully
        >>> _restore_metadata("file.flac", None)
        False

    Note:
        - Requires the 'mutagen' library to be installed
        - Clears ALL existing metadata before restoring (not a merge operation)
        - Preserves the exact structure of multi-value tags
        - Automatically saves changes to the file
        - Changes are written atomically by the Mutagen library
        - Tag names are case-sensitive per FLAC/Vorbis specification

    See Also:
        _extract_metadata: Extract metadata from a FLAC file
        repair_flac_file: Complete repair workflow using both functions
    """
    if not MUTAGEN_AVAILABLE or not metadata:
        return False

    try:
        audio: FLAC = FLAC(flac_path)

        # Restore tags
        audio.clear()
        tags: Dict[str, List[str]] = metadata.get("tags", {})
        for key, values in tags.items():
            audio[key] = values

        # Restore pictures
        pictures: List[Picture] = metadata.get("pictures", [])
        for picture in pictures:
            audio.add_picture(picture)

        audio.save()

        logger.debug(f"  Restored {len(tags)} tag types and {len(pictures)} picture(s)")
        return True

    except Exception as e:
        logger.error(f"Failed to restore metadata: {e}")
        return False


def repair_flac_file(
    corrupted_path: str, source_path: Optional[str] = None, replace_source: bool = False
) -> Optional[str]:
    """Repair a corrupted FLAC file using decode-through-errors + re-encode.

    This function repairs FLAC files with decoder errors by:
    1. Extracting metadata (tags, album art) from original file
    2. Decoding to WAV with --decode-through-errors (recovers what's possible)
    3. Re-encoding the clean WAV to FLAC
    4. Restoring all metadata to the repaired FLAC
    5. Verifying the repaired FLAC integrity
    6. Optionally replacing the source file with the repaired version

    Args:
        corrupted_path: Path to the corrupted FLAC file to repair.
        source_path: Original source file path (if corrupted_path is a temp copy).
        replace_source: If True and repair succeeds, replace source_path with repaired file.

    Returns:
        Path to the repaired temporary file, or None on failure.
    """
    wav_path: Optional[str] = None
    repaired_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    try:
        temp_dir: str = tempfile.gettempdir()
        base_name: str = os.path.splitext(os.path.basename(corrupted_path))[0]
        wav_path = os.path.join(temp_dir, f"repair_{base_name}.wav")
        repaired_path = os.path.join(temp_dir, f"repaired_{os.path.basename(corrupted_path)}")

        display_name: str = (
            os.path.basename(source_path) if source_path else os.path.basename(corrupted_path)
        )
        logger.info(f"Attempting to repair {display_name}")

        # Step 0: Extract metadata from original file
        logger.debug(f"  Step 0: Extracting metadata")
        metadata = _extract_metadata(corrupted_path)
        if metadata:
            tag_count = len(metadata.get("tags", {}))
            pic_count = len(metadata.get("pictures", []))
            logger.debug(f"  ✅ Extracted {tag_count} tags, {pic_count} picture(s)")
        else:
            logger.warning(f"  ⚠️  Could not extract metadata (will be lost)")

        # Step 1: Decode FLAC to WAV with error recovery
        logger.debug(f"  Step 1: Decoding with error recovery to {os.path.basename(wav_path)}")
        decode_command = [
            "flac",
            "--decode",
            "--decode-through-errors",  # Continue decoding despite errors
            "--silent",  # Reduce noise in logs
            corrupted_path,
            "-o",
            wav_path,
        ]

        decode_result = subprocess.run(
            decode_command, capture_output=True, text=True, check=False, timeout=120
        )

        # Check if WAV was created (even if there were errors during decoding)
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            logger.error(f"  ❌ Failed to decode: no WAV output created")
            return None

        wav_size_mb = os.path.getsize(wav_path) / (1024 * 1024)
        logger.debug(f"  ✅ Decoded to WAV ({wav_size_mb:.1f} MB)")

        # Step 2: Re-encode WAV to FLAC
        logger.debug(f"  Step 2: Re-encoding to FLAC")
        encode_command = [
            "flac",
            "--best",
            "--silent",
            "-f",  # Force overwrite
            wav_path,
            "-o",
            repaired_path,
        ]

        encode_result = subprocess.run(
            encode_command, capture_output=True, text=True, check=False, timeout=120
        )

        if encode_result.returncode != 0:
            logger.error(f"  ❌ Failed to re-encode WAV to FLAC")
            logger.debug(f"     Error: {encode_result.stderr}")
            return None

        # Step 3: Restore metadata to repaired file
        logger.debug(f"  Step 3: Restoring metadata")
        if metadata:
            if _restore_metadata(repaired_path, metadata):
                logger.debug(f"  ✅ Metadata restored successfully")
            else:
                logger.warning(f"  ⚠️  Failed to restore metadata")
        else:
            logger.debug(f"  ⚠️  No metadata to restore")

        # Step 4: Verify repaired FLAC integrity
        logger.debug(f"  Step 4: Verifying repaired FLAC")
        verify_command = ["flac", "--test", "--silent", repaired_path]

        verify_result = subprocess.run(
            verify_command, capture_output=True, text=True, check=False, timeout=60
        )

        if verify_result.returncode != 0:
            logger.warning(f"  ⚠️  Repaired FLAC still has issues")
            logger.debug(f"     Error: {verify_result.stderr}")
            return None

        repaired_size_mb = os.path.getsize(repaired_path) / (1024 * 1024)
        logger.info(f"  ✅ Successfully repaired and verified ({repaired_size_mb:.1f} MB)")

        # Step 5: Replace source file if requested
        if replace_source and source_path and os.path.exists(source_path):
            try:
                # Create backup of original corrupted file
                backup_path = source_path + ".corrupted.bak"
                logger.info(f"  💾 Creating backup: {os.path.basename(backup_path)}")
                shutil.copy2(source_path, backup_path)

                # Replace original with repaired version
                logger.info(f"  🔄 Replacing original file with repaired version")
                shutil.copy2(repaired_path, source_path)

                logger.info(f"  ✅ Original file replaced successfully")
                get_tracker().record_issue(
                    filepath=source_path,
                    issue_type=IssueType.REPAIR_ATTEMPTED,
                    message=f"File successfully repaired and replaced (backup: {os.path.basename(backup_path)})",
                )
            except Exception as replace_error:
                logger.error(f"  ❌ Failed to replace source file: {replace_error}")
                # Don't fail the whole repair - we still have the repaired temp file

        return repaired_path

    except subprocess.TimeoutExpired:
        logger.error(f"  ❌ Repair timeout (>120s)")
        return None

    except Exception as e:
        logger.error(f"  ❌ Repair exception: {e}")
        return None

    finally:
        # Cleanup intermediate WAV file
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass  # Best effort cleanup


def sf_blocks(
    file_path: str,
    blocksize: int = 16384,
    dtype: str = "float32",
    max_attempts: int = 5,
    initial_delay: float = 0.2,
    backoff_multiplier: float = 2.0,
) -> Generator[NDArray[np.float32], None, None]:
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
        Generator yielding audio chunks as numpy arrays.
    """
    current_frame: int = 0
    try:
        total_frames: int = sf.info(file_path).frames
    except Exception as e:
        logger.error(f"Could not open or read info from {file_path}: {e}")
        return

    while current_frame < total_frames:
        delay: float = initial_delay
        read_successful: bool = False
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
    original_filepath: Optional[str] = None,
) -> Tuple[Optional[NDArray[np.float32]], Optional[int], bool]:
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
        original_filepath: Original file path for diagnostic reporting (default: None).

    Returns:
        Tuple of (audio_data, sample_rate, is_complete):
        - audio_data: Concatenated audio chunks (None if no data read)
        - sample_rate: Sample rate of the audio file (None if cannot read info)
        - is_complete: True if entire file was read, False if partial
    """
    # Use original filepath for diagnostic tracking, or file_path if not provided
    tracking_path: str = original_filepath or file_path

    chunks: List[NDArray[np.float32]] = []
    sample_rate: Optional[int] = None
    current_frame: int = 0

    try:
        info = sf.info(file_path)
        sample_rate = info.samplerate
        total_frames: int = info.frames
    except Exception as e:
        logger.error(f"Cannot read file info from {file_path}: {e}")
        return None, None, False

    logger.debug(f"Starting partial block read of {file_path} ({total_frames} frames)")

    # Read chunks until we hit an error or reach end
    while current_frame < total_frames:
        delay: float = initial_delay
        read_successful: bool = False

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
                            logger.debug(
                                f"Returning partial data: {current_frame}/{total_frames} frames ({len(chunks)} chunks)"
                            )
                            get_tracker().record_issue(
                                filepath=tracking_path,
                                issue_type=IssueType.PARTIAL_READ,
                                message=f"Partial read after decoder errors: {error_msg}",
                                frames_read=current_frame,
                                total_frames=total_frames,
                                retry_count=max_attempts,
                            )
                            combined = np.concatenate(chunks)
                            return combined, sample_rate, False  # Not complete
                        else:
                            logger.warning("No data could be read before error")
                            get_tracker().record_issue(
                                filepath=tracking_path,
                                issue_type=IssueType.READ_FAILED,
                                message="No data could be read before error",
                                frames_read=0,
                                total_frames=total_frames,
                                retry_count=max_attempts,
                            )
                            return None, None, False
                else:
                    # Non-temporary error
                    logger.debug(
                        f"Non-temporary error reading from frame {current_frame}: {error_msg}"
                    )
                    if chunks:
                        logger.debug(
                            f"Returning partial data: {current_frame}/{total_frames} frames"
                        )
                        issue_type = (
                            IssueType.SEEK_FAILED
                            if "seek" in error_msg.lower()
                            else IssueType.PARTIAL_READ
                        )
                        get_tracker().record_issue(
                            filepath=tracking_path,
                            issue_type=issue_type,
                            message=f"Non-temporary error: {error_msg}",
                            frames_read=current_frame,
                            total_frames=total_frames,
                            retry_count=attempt,
                        )
                        combined = np.concatenate(chunks)
                        return combined, sample_rate, False  # Not complete
                    else:
                        get_tracker().record_issue(
                            filepath=tracking_path,
                            issue_type=IssueType.READ_FAILED,
                            message=f"Non-temporary error, no data read: {error_msg}",
                            frames_read=0,
                            total_frames=total_frames,
                            retry_count=attempt,
                        )
                        return None, None, False

        if not read_successful:
            # Failed to read this block
            break

    # Successfully read entire file
    if chunks:
        final_combined: NDArray[np.float32] = np.concatenate(chunks)
        is_complete: bool = current_frame >= total_frames
        logger.debug(
            f"Read {current_frame}/{total_frames} frames ({'complete' if is_complete else 'partial'})"
        )
        return final_combined, sample_rate, is_complete
    else:
        logger.error("No data could be read")
        return None, None, False
