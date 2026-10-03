"""Main FLAC file analyzer: one file in, one result dict out.

The file is copied (or decoded) to a local temp file once, read once into an
``AudioCache``, and every stage — metadata, spectrum, quality, scoring — works
from that copy. See ``analyze_file`` for the order of the stages.
"""

import logging
import shutil
import tempfile
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from .assessability import unassessable_reason
from .audio_cache import AudioCache
from .audio_formats import (
    decode_to_wav,
    flac_equivalent_size,
    needs_ffmpeg_decode,
    probe_codec,
)
from .diagnostic_tracker import get_tracker
from .hires import classify_hires
from .metadata import check_duration_consistency, read_metadata
from .new_scoring import estimate_mp3_bitrate, new_calculate_score
from .new_scoring.evidence import collapse_dependent_families, evidence_families
from .progress import ProgressCallback, emit, scan_reporter, substage_reporter
from .quality import analyze_audio_quality
from .spectrum import analyze_spectrum

logger = logging.getLogger(__name__)

# Frames of the segment whose RMS decides "there is signal here" for the
# assessability check — 30 s at CD rate, whatever the file's own rate.
_RMS_PROBE_FRAMES = int(30 * 44100)


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


def _optional_float(value: object) -> Optional[float]:
    """A float, or None when the value is absent or unreadable — never 0.0."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _sampled_rms(cache: AudioCache) -> Optional[float]:
    """RMS of a short segment, or None if it could not be measured.

    A segment rather than the whole file: this only has to separate "there is
    signal here" from "there is not", and loading the full audio to answer that
    would be the most expensive step in the pipeline run for the cheapest
    question. None on any failure — an unmeasurable level must not read as
    silence, which would abstain on a file the engine could have assessed.
    """
    try:
        data, _rate = cache.get_segment(0, _RMS_PROBE_FRAMES)
        if data is None or getattr(data, "size", 0) == 0:
            return None
        return float(np.sqrt(np.mean(np.asarray(data, dtype=np.float64) ** 2)))
    except Exception:
        return None


def _stage_local_copy(filepath: Path) -> Tuple[Path, bool]:
    """Copy or decode the source to a local temp file; return it and whether it was decoded.

    I/O STABILITY STRATEGY: "Copy-to-Temp". Every later read hits a local file
    instead of a USB or network drive, and non-native containers are normalised.
    libsndfile reads FLAC/WAV natively, so those are copied as-is; ALAC (.m4a)
    and APE cannot be read by soundfile, so they are decoded to a temp WAV via
    ffmpeg and the rest of the pipeline treats that WAV like any lossless source.

    Raises:
        RuntimeError: when a non-native container could not be decoded.
    """
    if needs_ffmpeg_decode(filepath):
        logger.debug(f"Decoding {filepath.name} ({filepath.suffix}) to temp WAV via ffmpeg")
        decoded = decode_to_wav(filepath)
        if decoded is None:
            raise RuntimeError(
                f"Could not decode {filepath.suffix} file "
                f"(ffmpeg missing or decode failed): {filepath.name}"
            )
        return decoded, True
    # Create a named temp file, close it, and overwrite it with a copy.
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
        temp_path = Path(tmp.name)
    # copy2 preserves timestamps (not critical for content, but cheap).
    logger.debug(f"I/O STABILITY: Copying {filepath.name} to local temp {temp_path}")
    try:
        shutil.copy2(filepath, temp_path)
    except BaseException:
        # The caller never sees this path, so it could not delete it.
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path, False


def _read_source_metadata(filepath: Path, temp_path: Path, decoded_from_source: bool) -> Dict:
    """Read the tags and stream properties of the file under analysis.

    For a decoded source the original is not soundfile-readable, so the audio
    properties (rate, depth, channels, duration) come from the decoded WAV —
    ffmpeg preserves them — and the real source codec is probed and labelled.
    """
    if not decoded_from_source:
        return read_metadata(filepath)
    metadata = read_metadata(temp_path)
    codec = probe_codec(filepath)
    if codec:
        metadata["encoder"] = codec.upper()
    return metadata


def _apply_assessability(
    verdict: str,
    confidence: str,
    reason: str,
    metadata: Dict,
    cutoff_freq: float,
    cache: AudioCache,
    filepath: Path,
) -> Tuple[str, str, str]:
    """Downgrade an AUTHENTIC the engine had no standing to issue to NOT_ASSESSED.

    Only AUTHENTIC is ever downgraded: a conviction, or anything signalled, is
    proof the instruments ran, so this can never withdraw an accusation. See
    analysis/assessability.py.
    """
    if verdict != "AUTHENTIC":
        return verdict, confidence, reason
    not_assessed = unassessable_reason(
        _optional_int(metadata.get("sample_rate")),
        _optional_float(metadata.get("duration")),
        cutoff_freq,
        _sampled_rms(cache),
    )
    if not not_assessed:
        return verdict, confidence, reason
    logger.info("NOT ASSESSED %s: %s", filepath.name, not_assessed)
    return (
        "NOT_ASSESSED",
        "🔍 Not assessed — the rules could not run on this file",
        f"Not assessed: {not_assessed}",
    )


def _hires_axis(metadata: Dict, quality_analysis: Dict) -> Tuple[str, List[str]]:
    """The fake hi-res verdict (#1): a SEPARATE axis from the transcode verdict.

    Combines the upsampling (spectral cliff + silent floor) and bit-depth (padded
    24-bit) signals into one label (GENUINE_HIRES / UPSAMPLED / PADDED_DEPTH / …).
    NOT_HIRES for ordinary ≤48 kHz / ≤16-bit files.

    The rate and depth are None, not 0, when the header could not be read:
    read_metadata returns {} on any exception, so an unreadable file used to
    arrive here as 0 Hz, and classify_hires then returned NOT_HIRES with no
    reason — telling a file whose header failed that the hi-res axis confidently
    does not apply to it (shape D, Provir 2026-08-30).
    """
    bd = quality_analysis["bit_depth"]
    up = quality_analysis["upsampling"]
    sr_int = _optional_int(metadata.get("sample_rate"))
    depth_int = _optional_int(metadata.get("bit_depth"))
    return classify_hires(
        sample_rate=sr_int,
        bit_depth=depth_int,
        is_upsampled=up.get("is_upsampled", False),
        suspected_original_rate=up.get("suspected_original_rate") or sr_int or 0,
        is_fake_high_res=bd.get("is_fake_high_res", False),
        estimated_depth=bd.get("estimated_depth") or depth_int or 0,
        floor_above_db=up.get("floor_above_db", float("nan")),
    )


def _error_result(filepath: Path, error: Exception) -> Dict:
    """The result row for a file whose analysis raised."""
    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "score": 0,
        "verdict": "ERROR",
        "confidence": "N/A",
        "reason": f"Error: {str(error)}",
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
        "corruption_error": str(error),
        "has_silence_issue": False,
        "silence_issue_type": "error",
        "is_fake_high_res": False,
        "estimated_bit_depth": 0,
        "is_upsampled": False,
        "suspected_original_rate": 0,
        "hires_verdict": "UNKNOWN",
        "hires_reason": "",
    }


def _cleanup(cache: Optional[AudioCache], temp_path: Optional[Path], filepath: Path) -> None:
    """Release the decoded audio and delete the temp copy."""
    if cache is not None:
        cache.clear()
        logger.debug(f"⚡ OPTIMIZATION: Cleared AudioCache for {filepath.name}")
    if temp_path and temp_path.exists():
        try:
            temp_path.unlink()
            logger.debug(f"I/O STABILITY: Deleted temp file {temp_path}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {temp_path}: {e}")


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

    def analyze_file(
        self,
        filepath: Union[str, Path],
        on_progress: Optional[ProgressCallback] = None,
    ) -> Dict:
        """Analyzes a lossless audio file and determines if it is authentic.

        Stages, each announced to ``on_progress``: prepare (local copy), metadata,
        spectrum, quality, scoring, done. One ``AudioCache`` on the local copy
        serves every stage so the audio is read from disk once.

        Args:
            filepath: Path to the file to analyze (FLAC/WAV/ALAC/APE). Accepts a
                ``str`` or a ``pathlib.Path`` — a string is coerced to ``Path``.
            on_progress: Called as each stage of THIS file starts, with a
                :class:`~flac_detective.analysis.progress.ProgressEvent`. For an
                application that has to show something during an hour-long track,
                where a per-file counter cannot help (issue #11). It observes and
                never participates: anything it raises is swallowed, and the
                result is the same whether it is given or not.

        Returns:
            Dict with: filepath, filename, score, reason, cutoff_freq, metadata,
            duration_mismatch, quality issues (clipping, dc_offset, corruption).
        """
        # Accept str for ergonomics; the pipeline relies on Path methods (.suffix, …).
        filepath = Path(filepath)
        # Before the copy, not after: on an external drive that copy is itself a
        # slow stage, and a caller that hears nothing until it ends learns the
        # least exactly when it needs to know the most.
        emit("prepare", filepath, on_progress)
        temp_path: Optional[Path] = None
        cache: Optional[AudioCache] = None

        try:
            temp_path, decoded_from_source = _stage_local_copy(filepath)

            # Every subsequent read hits the LOCAL copy. The original path travels
            # along for diagnostic reporting only.
            cache = AudioCache(temp_path, original_filepath=filepath)
            logger.debug(f"⚡ OPTIMIZATION: Created AudioCache for {filepath.name}")
            is_partial_analysis = cache.is_partial()

            emit("metadata", filepath, on_progress)
            metadata = _read_source_metadata(filepath, temp_path, decoded_from_source)
            # Duration consistency check (FTF criterion), read from the local copy.
            duration_check = check_duration_consistency(temp_path, metadata)

            emit("spectrum", filepath, on_progress)
            (
                cutoff_freq,
                energy_ratio,
                cutoff_std,
                residual_floor_db,
                edge_step_db,
                floor_above_db,
            ) = analyze_spectrum(temp_path, self.sample_duration, cache=cache)

            emit("quality", filepath, on_progress)
            # The substage reporter carries the ORIGINAL filepath, not the temp
            # copy this call works on: the caller must never be shown a name it
            # cannot recognise. Measured on a 20-minute track, this stage is 87%
            # of the analysis, so one event at its start left a long file sitting
            # on a single label.
            quality_analysis = analyze_audio_quality(
                temp_path,
                metadata,
                cutoff_freq,
                cache=cache,
                on_substage=substage_reporter("quality", filepath, on_progress),
                on_scan=scan_reporter("quality", filepath, on_progress),
            )

            # The long stage, and the one a caller most needs named: the
            # FLAC-equivalent re-encode alone measures 6 s to 14 s per file, and
            # Rules 11-15 and the CNN decode on top of it.
            emit("scoring", filepath, on_progress)
            logger.debug(f"Analyzing file: {filepath.name} | Cutoff: {cutoff_freq:.0f} Hz")

            score_breakdown: Dict[str, int] = {}
            # Families that testify without scoring cannot appear in a points
            # breakdown, so they travel on their own channel.
            witness_families: Set[str] = set()
            # source_path=filepath (the ORIGINAL): the real bitrate is sized from
            # the on-disk file. measure_compressed_size: ONE RULER FOR EVERY
            # CONTAINER, FLAC included — the compression ratio Rule 1 reads is
            # evidence about the audio, so it is measured by re-encoding the audio
            # at one fixed setting (issue #7; the reasoning and the figures are in
            # ``flac_equivalent_size``). Handed over as a callable, not a number:
            # the scorer decides whether to spend the re-encode from the values it
            # parses itself. ``partial`` rather than a lambda with a default
            # argument because mypy cannot type the latter.
            score, verdict, confidence, reason = new_calculate_score(
                cutoff_freq,
                metadata,
                duration_check,
                temp_path,
                cutoff_std,
                energy_ratio,
                cache=cache,
                source_path=filepath,
                measure_compressed_size=partial(flac_equivalent_size, temp_path),
                deep=self.deep,
                residual_floor_db=residual_floor_db,
                edge_step_db=edge_step_db,
                floor_above_db=floor_above_db,
                breakdown_out=score_breakdown,
                witnesses_out=witness_families,
            )

            if is_partial_analysis:
                reason += " (analysed from a partial read of the file)"

            verdict, confidence, reason = _apply_assessability(
                verdict, confidence, reason, metadata, cutoff_freq, cache, filepath
            )
            hires_verdict, hires_reasons = _hires_axis(metadata, quality_analysis)

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
                # Quality fields
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
            return _error_result(filepath, e)
        finally:
            _cleanup(cache, temp_path, filepath)
            # In `finally`, so it is emitted exactly once per file whether the
            # analysis returned a verdict or an ERROR result. A caller waiting on
            # a file that failed must be released by the same signal as one that
            # succeeded, or a UI hangs on precisely the files that went wrong.
            emit("done", filepath, on_progress)
