"""Main FLAC file analyzer.

PHASE 1 OPTIMIZATION: Uses AudioCache to avoid multiple file reads.
"""

import logging
from pathlib import Path
from typing import Dict

from .metadata import check_duration_consistency, read_metadata
from .quality import analyze_audio_quality
from .new_scoring import estimate_mp3_bitrate, new_calculate_score
from .spectrum import analyze_spectrum
from .audio_cache import AudioCache

logger = logging.getLogger(__name__)


class FLACAnalyzer:
    """FLAC file analyzer to detect MP3 transcoding."""

    def __init__(self, sample_duration: float = 30.0):
        """Initializes the analyzer.

        Args:
            sample_duration: Duration in seconds to analyze (default 30s).
        """
        self.sample_duration = sample_duration

    def analyze_file(self, filepath: Path) -> Dict:
        """Analyzes a FLAC file and determines if it is authentic.

        PHASE 1 OPTIMIZATION: Creates AudioCache once and reuses it for all analyses.

        Args:
            filepath: Path to FLAC file to analyze.

        Returns:
            Dict with: filepath, filename, score, reason, cutoff_freq, metadata,
            duration_mismatch, quality issues (clipping, dc_offset, corruption).
        """
        # PHASE 1 OPTIMIZATION: Create cache once for this file
        cache = AudioCache(filepath)
        
        try:
            logger.debug(f"⚡ OPTIMIZATION: Created AudioCache for {filepath.name}")
            
            # Read metadata
            metadata = read_metadata(filepath)

            # Duration consistency check (FTF criterion)
            duration_check = check_duration_consistency(filepath, metadata)

            # Spectral analysis (OPTIMIZED: uses cache)
            cutoff_freq, energy_ratio, cutoff_std = analyze_spectrum(filepath, self.sample_duration, cache=cache)

            # Audio quality analysis (OPTIMIZED: uses cache)
            quality_analysis = analyze_audio_quality(filepath, metadata, cutoff_freq, cache=cache)

            # NEW SCORING SYSTEM: 6-rule system (0-100 points, higher = more fake)
            score, verdict, confidence, reason = new_calculate_score(
                cutoff_freq, metadata, duration_check, filepath, cutoff_std, energy_ratio
            )

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
                "partial_analysis": quality_analysis["corruption"].get("partial_analysis", False),
                # Phase 2
                "has_silence_issue": quality_analysis["silence"]["has_silence_issue"],
                "silence_issue_type": quality_analysis["silence"]["issue_type"],
                "is_fake_high_res": quality_analysis["bit_depth"]["is_fake_high_res"],
                "estimated_bit_depth": quality_analysis["bit_depth"]["estimated_depth"],
                "is_upsampled": quality_analysis["upsampling"]["is_upsampled"],
                "suspected_original_rate": quality_analysis["upsampling"]["suspected_original_rate"],
                "estimated_mp3_bitrate": estimate_mp3_bitrate(cutoff_freq),
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
            }
        finally:
            # PHASE 1 OPTIMIZATION: Clear cache after analysis
            cache.clear()
            logger.debug(f"⚡ OPTIMIZATION: Cleared AudioCache for {filepath.name}")
