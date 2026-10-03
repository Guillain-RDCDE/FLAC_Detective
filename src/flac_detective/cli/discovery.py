"""Turning the user's paths into files to analyse and files to reject."""

import logging
from pathlib import Path

from ..analysis.audio_formats import (
    LOSSY_SUFFIXES,
    PROBE_SUFFIXES,
    discover_audio_files,
    is_analysable_lossless,
)
from ..tracker import ProgressTracker

logger = logging.getLogger(__name__)

# Audio extensions that are lossy, or (the probe-able containers) only conditionally
# lossless: a directly-passed file with one of these that isn't analysable lossless
# is reported as a non-FLAC reject rather than silently ignored.
REJECTABLE_SUFFIXES = LOSSY_SUFFIXES | PROBE_SUFFIXES


def scan_files(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Scan paths for FLAC and non-FLAC audio files.

    Args:
        paths: List of paths to scan.

    Returns:
        Tuple of (all_flac_files, all_non_flac_files).
    """
    all_flac_files = []
    all_non_flac_files = []

    for path in paths:
        if path.is_file():
            # Analyse any lossless source on its own merits: FLAC/WAV natively, plus
            # ALAC (.m4a) / APE etc. detected by probing the real codec. A lossy file
            # (mp3, an AAC .m4a, …) goes to the "replace with a real FLAC" reject list.
            if is_analysable_lossless(path):
                all_flac_files.append(path)
                logger.info(f"File added : {path.name}")
            elif path.suffix.lower() in REJECTABLE_SUFFIXES:
                all_non_flac_files.append(path)
            else:
                logger.warning(f"Ignored (not an analysable audio file or folder) : {path}")
        elif path.is_dir():
            # One walk, the same decision per file as for a file passed directly:
            # native formats by extension, probe-able containers by their real
            # codec, lossy extensions to the reject list. (Until v1.13.16 the
            # directory scan took .flac and .wav by name and probed the lossy
            # extensions only, so an .aiff in a folder was never analysed.)
            analysable, rejects = discover_audio_files(path)
            for candidate in analysable:
                if candidate.suffix.lower() not in (".flac", ".wav"):
                    logger.info(
                        f"Lossless {candidate.suffix} added for analysis : {candidate.name}"
                    )
            all_flac_files.extend(analysable)
            all_non_flac_files.extend(rejects)
        else:
            logger.warning(f"Ignored (not a FLAC/WAV file or folder) : {path}")

    return all_flac_files, all_non_flac_files


def create_non_flac_result(non_flac_file: Path) -> dict:
    """Create a result dictionary for a non-FLAC audio file.

    Args:
        non_flac_file: Path to the non-FLAC file.

    Returns:
        Result dictionary.
    """
    extension = non_flac_file.suffix.upper()[1:]  # Remove the dot and uppercase
    return {
        "filepath": str(non_flac_file),
        "filename": non_flac_file.name,
        "score": 100,  # Maximum fake score for non-FLAC
        "verdict": "NON_FLAC",
        "confidence": "CERTAIN",
        "reason": f"NON-FLAC FILE ({extension}) - Must be replaced with authentic FLAC",
        "cutoff_freq": 0,
        "sample_rate": "N/A",
        "bit_depth": "N/A",
        "encoder": extension,
        "duration_mismatch": None,
        "duration_metadata": "N/A",
        "duration_real": "N/A",
        "duration_diff": "N/A",
        "has_clipping": False,
        "clipping_severity": "n/a",
        "clipping_percentage": 0.0,
        "has_dc_offset": False,
        "dc_offset_severity": "n/a",
        "dc_offset_value": 0.0,
        "is_corrupted": False,
        "corruption_error": None,
        "has_silence_issue": False,
        "silence_issue_type": "n/a",
        "is_fake_high_res": False,
        "estimated_bit_depth": 0,
        "is_upsampled": False,
        "suspected_original_rate": 0,
        "estimated_mp3_bitrate": 0,
        "hires_verdict": "NOT_HIRES",
        "hires_reason": "",
    }


def add_non_flac_results(all_non_flac_files: list[Path], tracker: ProgressTracker):
    """Add non-FLAC audio files to results.

    Args:
        all_non_flac_files: List of non-FLAC files.
        tracker: Progress tracker instance.
    """
    for non_flac_file in all_non_flac_files:
        result = create_non_flac_result(non_flac_file)
        tracker.add_result(result)

    if all_non_flac_files:
        logger.info(f"\n{len(all_non_flac_files)} non-FLAC audio files added to report")
