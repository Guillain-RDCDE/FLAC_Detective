"""Main FLAC file analyzer.

PHASE 1 OPTIMIZATION: Uses AudioCache to avoid multiple file reads.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Set, Union

from .audio_cache import AudioCache
from .audio_formats import decode_to_wav, needs_ffmpeg_decode, probe_codec
from .diagnostic_tracker import get_tracker
from .hires import classify_hires
from .metadata import check_duration_consistency, read_metadata
from .new_scoring import estimate_mp3_bitrate, new_calculate_score
from .new_scoring.evidence import collapse_dependent_families, evidence_families
from .quality import analyze_audio_quality
from .spectrum import analyze_spectrum

logger = logging.getLogger(__name__)


def _optional_int(value: object) -> Optional[int]:
    """An int, or None when the value is absent or unreadable — never 0.

    0 is a reading ("this file claims 0 Hz"), and no file does. See the shape D
    registration: an absence coerced to a number at the point it is consumed is
    the defect that survives a correct fix upstream.
    """
    if isinstance(value, bool):  # a bool is an int in Python and a lie here
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


class FLACAnalyzer:
    """FLAC file analyzer to detect MP3 transcoding."""

    def __init__(self, sample_duration: float = 30.0, deep: bool = False):
        """Initializes the analyzer.

        Args:
            sample_duration: Duration in seconds to analyze (default 30s).
            deep: If True, run Rule 12 (ML) on every file, bypassing the authentic
                fast path — needed for the high-confidence WARNING floor to catch
                silent-heuristic AAC/Vorbis transcodes. Slower. See the ``--deep`` flag.
        """
        self.sample_duration = sample_duration
        self.deep = deep

    def analyze_file(self, filepath: Union[str, Path]) -> Dict:
        """Analyzes a lossless audio file and determines if it is authentic.

        PHASE 1 OPTIMIZATION: Creates AudioCache once and reuses it for all analyses.

        Args:
            filepath: Path to the file to analyze (FLAC/WAV/ALAC/APE). Accepts a
                ``str`` or a ``pathlib.Path`` — a string is coerced to ``Path``.

        Returns:
            Dict with: filepath, filename, score, reason, cutoff_freq, metadata,
            duration_mismatch, quality issues (clipping, dc_offset, corruption).
        """
        # Accept str for ergonomics; the pipeline relies on Path methods (.suffix, …).
        filepath = Path(filepath)
        # I/O STABILITY STRATEGY: "Copy-to-Temp"
        # Copy (or decode) the source to a local temp file to avoid external-drive
        # I/O errors during analysis and to normalise non-native containers.
        temp_path = None

        try:
            # libsndfile reads FLAC/WAV natively -> copy as-is. Non-native lossless
            # containers (ALAC in .m4a, APE) can't be read by soundfile, so decode
            # them to a temp WAV via ffmpeg; the rest of the pipeline treats that WAV
            # exactly like any other lossless source.
            decoded_from_source = needs_ffmpeg_decode(filepath)
            if decoded_from_source:
                logger.debug(f"Decoding {filepath.name} ({filepath.suffix}) to temp WAV via ffmpeg")
                temp_path = decode_to_wav(filepath)
                if temp_path is None:
                    raise RuntimeError(
                        f"Could not decode {filepath.suffix} file "
                        f"(ffmpeg missing or decode failed): {filepath.name}"
                    )
            else:
                # Create a named temp file, close it, and overwrite it with a copy.
                with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
                    temp_path = Path(tmp.name)
                # copy2 preserves timestamps (not critical for content, but cheap).
                logger.debug(f"I/O STABILITY: Copying {filepath.name} to local temp {temp_path}")
                shutil.copy2(filepath, temp_path)

            # PHASE 1 OPTIMIZATION: Create cache using the LOCAL TEMP copy
            # All subsequent reads will hit this local file (SSD/HDD) instead of USB/Network
            # AudioCache now handles partial loading internally
            # Pass original filepath for diagnostic tracking
            cache = AudioCache(temp_path, original_filepath=filepath)
            logger.debug(f"⚡ OPTIMIZATION: Created AudioCache for {filepath.name}")

            # Check if cache loaded partial data
            is_partial_analysis = cache.is_partial()

            # Read metadata. For a decoded source the original isn't soundfile-readable,
            # so read audio properties (sr / depth / channels / duration) from the
            # decoded WAV — ffmpeg preserves them — and label the real source codec.
            if decoded_from_source:
                metadata = read_metadata(temp_path)
                codec = probe_codec(filepath)
                if codec:
                    metadata["encoder"] = codec.upper()
            else:
                metadata = read_metadata(filepath)

            # Duration consistency check (FTF criterion)
            # Use ORIGINAL filepath for reporting, but TEMP path for reading could be safer?
            # Duration check uses Mutagen/Soundfile. Let's use TEMP path for safety.
            duration_check = check_duration_consistency(temp_path, metadata)

            # Spectral analysis (OPTIMIZED: uses cache -> points to TEMP)
            cutoff_freq, energy_ratio, cutoff_std, residual_floor_db = analyze_spectrum(
                temp_path, self.sample_duration, cache=cache
            )

            # Audio quality analysis (OPTIMIZED: uses cache -> points to TEMP)
            quality_analysis = analyze_audio_quality(temp_path, metadata, cutoff_freq, cache=cache)

            # NEW SCORING SYSTEM: 6-rule system (0-100 points, higher = more fake)
            # We must pass 'filepath' (original) for logging/reporting purposes,
            # but ensure 'context.cache' (temp) is used for heavy lifting.
            logger.debug(f"Analyzing file: {filepath.name} | Cutoff: {cutoff_freq:.0f} Hz")
            # source_path=filepath (the ORIGINAL): the real bitrate must be sized from
            # the on-disk compressed file, not the decoded WAV — otherwise an ALAC/APE
            # source looks uncompressed and Rules 1 & 3 wrongly switch off.
            score_breakdown: Dict[str, int] = {}
            # Families that testify without scoring cannot appear in a points
            # breakdown, so they travel on their own channel.
            witness_families: Set[str] = set()
            score, verdict, confidence, reason = new_calculate_score(
                cutoff_freq,
                metadata,
                duration_check,
                temp_path,
                cutoff_std,
                energy_ratio,
                cache=cache,
                source_path=filepath,
                deep=self.deep,
                residual_floor_db=residual_floor_db,
                breakdown_out=score_breakdown,
                witnesses_out=witness_families,
            )

            # Add note if analysis was partial
            if is_partial_analysis:
                reason += " (analysed from a partial read of the file)"

            # Fake hi-res verdict (#1): a SEPARATE axis from the transcode verdict.
            # Combines the upsampling (spectral cliff + silent floor) and bit-depth
            # (padded 24-bit) signals into one label (GENUINE_HIRES / UPSAMPLED /
            # PADDED_DEPTH / …). NOT_HIRES for ordinary ≤48 kHz / ≤16-bit files.
            bd = quality_analysis["bit_depth"]
            up = quality_analysis["upsampling"]
            # None, not 0, when the header could not be read. read_metadata
            # returns {} on any exception, so an unreadable or corrupt file used
            # to arrive here as a rate of 0 Hz — and classify_hires then read
            # `is_high_rate = False` and returned NOT_HIRES with no reason, which
            # tells a file whose header failed that the hi-res axis confidently
            # does not apply to it. Shape D, from Provir 2026-08-30: the coercion
            # that survives a correct fix, at the site where the absence is
            # CONSUMED rather than created.
            sr_int = _optional_int(metadata.get("sample_rate"))
            depth_int = _optional_int(metadata.get("bit_depth"))
            hires_verdict, hires_reasons = classify_hires(
                sample_rate=sr_int,
                bit_depth=depth_int,
                is_upsampled=up.get("is_upsampled", False),
                suspected_original_rate=up.get("suspected_original_rate") or sr_int or 0,
                is_fake_high_res=bd.get("is_fake_high_res", False),
                estimated_depth=bd.get("estimated_depth") or depth_int or 0,
                floor_above_db=up.get("floor_above_db", float("nan")),
            )

            # Increment files analyzed counter
            get_tracker().increment_files_analyzed()

            return {
                "filepath": str(filepath),
                "filename": filepath.name,
                "score": score,
                "verdict": verdict,
                "confidence": confidence,
                "reason": reason,
                "cutoff_freq": cutoff_freq,
                "sample_rate": metadata.get("sample_rate", "N/A"),
                "bit_depth": metadata.get("bit_depth", "N/A"),
                "encoder": metadata.get("encoder", "N/A"),
                "duration_mismatch": duration_check["mismatch"],
                "duration_metadata": duration_check["metadata_duration"],
                "duration_real": duration_check["real_duration"],
                "duration_diff": duration_check["diff_samples"],
                # New quality fields (Phase 1)
                "has_clipping": quality_analysis["clipping"]["has_clipping"],
                "clipping_severity": quality_analysis["clipping"]["severity"],
                "clipping_percentage": quality_analysis["clipping"]["clipping_percentage"],
                "has_dc_offset": quality_analysis["dc_offset"]["has_dc_offset"],
                "dc_offset_severity": quality_analysis["dc_offset"]["severity"],
                "dc_offset_value": quality_analysis["dc_offset"]["dc_offset_value"],
                "is_corrupted": quality_analysis["corruption"]["is_corrupted"],
                "corruption_error": quality_analysis["corruption"].get("error"),
                "partial_analysis": quality_analysis["corruption"].get("partial_analysis", False)
                or is_partial_analysis,
                "is_partial_analysis": is_partial_analysis,
                # Phase 2
                "has_silence_issue": quality_analysis["silence"]["has_silence_issue"],
                "silence_issue_type": quality_analysis["silence"]["issue_type"],
                "is_fake_high_res": quality_analysis["bit_depth"]["is_fake_high_res"],
                "estimated_bit_depth": quality_analysis["bit_depth"]["estimated_depth"],
                "is_upsampled": quality_analysis["upsampling"]["is_upsampled"],
                "suspected_original_rate": quality_analysis["upsampling"][
                    "suspected_original_rate"
                ],
                "estimated_mp3_bitrate": estimate_mp3_bitrate(cutoff_freq),
                # Fake hi-res axis (#1) — independent of the transcode verdict.
                "hires_verdict": hires_verdict,
                "hires_reason": " | ".join(hires_reasons) if hires_reasons else "",
                # Per-rule score attribution — what each rule actually contributed
                # to this file's score. Feeds ml/rule_audit.py (per-rule AUC).
                "score_breakdown": score_breakdown,
                # Independent evidence families accusing this file. A conviction
                # requires two of them; see analysis/new_scoring/evidence.py.
                # The dependency collapse is applied here as well, or the report
                # would name two witnesses where the verdict counted one.
                "evidence_families": sorted(
                    collapse_dependent_families(
                        evidence_families(score_breakdown, witnesses=witness_families),
                        cutoff_freq,
                    )
                ),
            }

        except Exception as e:
            logger.error(f"Analysis error {filepath.name}: {e}")
            return {
                "filepath": str(filepath),
                "filename": filepath.name,
                "score": 0,
                "verdict": "ERROR",
                "confidence": "N/A",
                "reason": f"Error: {str(e)}",
                "cutoff_freq": 0,
                "sample_rate": "N/A",
                "bit_depth": "N/A",
                "encoder": "N/A",
                "duration_mismatch": "Error",
                "duration_metadata": "N/A",
                "duration_real": "N/A",
                "duration_diff": "N/A",
                "has_clipping": False,
                "clipping_severity": "error",
                "clipping_percentage": 0.0,
                "has_dc_offset": False,
                "dc_offset_severity": "error",
                "dc_offset_value": 0.0,
                "is_corrupted": True,
                "corruption_error": str(e),
                "has_silence_issue": False,
                "silence_issue_type": "error",
                "is_fake_high_res": False,
                "estimated_bit_depth": 0,
                "is_upsampled": False,
                "suspected_original_rate": 0,
                "hires_verdict": "UNKNOWN",
                "hires_reason": "",
            }
        finally:
            # Cleanup resources
            if "cache" in locals():
                cache.clear()
                logger.debug(f"⚡ OPTIMIZATION: Cleared AudioCache for {filepath.name}")

            # Delete temp file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"I/O STABILITY: Deleted temp file {temp_path}")
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_path}: {e}")
