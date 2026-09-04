"""Format detection and decoding for analysable lossless inputs.

FLAC and WAV are read natively by libsndfile (soundfile). Other lossless
containers — notably ALAC (in .m4a) and APE — need ffmpeg, which is a hard
runtime requirement for *those* formats (FLAC/WAV never touch ffmpeg).

The tricky case is ``.m4a``: it can hold ALAC (lossless → analyse) or AAC
(lossy → reject). We probe the actual codec with ffprobe rather than trust the
extension.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lossless audio codecs we analyse on their own merits (ffprobe codec_name values).
LOSSLESS_CODECS = {
    "flac",
    "alac",
    "ape",
    "wavpack",
    "tta",
    "pcm_s16le",
    "pcm_s24le",
    "pcm_s32le",
    "pcm_f32le",
    "pcm_u8",
}

# Extensions libsndfile reads directly — no ffmpeg, no probe needed.
NATIVE_SUFFIXES = {".flac", ".wav", ".aiff", ".aif"}

# Extensions whose container may hold either lossless or lossy audio — probe to decide.
PROBE_SUFFIXES = {".m4a", ".mp4", ".ape", ".tta", ".wv"}


def ffmpeg_available() -> bool:
    """True if both ffmpeg and ffprobe are on PATH."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe_codec(path: Path) -> Optional[str]:
    """Return the first audio stream's codec_name via ffprobe, or None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw = result.stdout.strip()
        if not raw:
            return None
        # ffprobe's csv output can carry a trailing empty field and a Windows CR
        # (e.g. "alac,\r" was observed on real ALAC files that embed cover art).
        # Take the first comma-separated token of the first line, normalised.
        codec = raw.splitlines()[0].split(",")[0].strip().lower()
        return codec or None
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.debug(f"ffprobe failed for {path}: {e}")
        return None


def is_analysable_lossless(path: Path) -> bool:
    """True if the file is a lossless audio source worth analysing.

    FLAC/WAV by extension; ALAC/APE/etc. by probing the container's real codec.
    Lossy containers (an AAC .m4a) return False — they belong in the reject list.
    """
    suffix = path.suffix.lower()
    if suffix in NATIVE_SUFFIXES:
        return True
    if suffix in PROBE_SUFFIXES:
        codec = probe_codec(path)
        return codec in LOSSLESS_CODECS if codec else False
    return False


def needs_ffmpeg_decode(path: Path) -> bool:
    """True if libsndfile can't read it directly, so it must be decoded via ffmpeg."""
    return path.suffix.lower() not in NATIVE_SUFFIXES


# libsndfile's FLAC writer accepts PCM_S8 / PCM_16 / PCM_24. A source at or below
# 16 bits is written as PCM_16 (lossless, and FLAC compresses an 8-bit source's
# constant high byte away anyway); everything else, float included, is normalised
# to PCM_24. The point is a comparable size, not an archival copy.
_FLAC_16_BIT = {"PCM_S8", "PCM_U8", "PCM_16"}

# Frames per streaming block when re-encoding. 1 Mi frames of stereo 24-bit is
# ~8 MB in flight, so a two-hour file costs no more memory than a two-minute one.
_ENCODE_BLOCK = 1 << 20


def flac_equivalent_size(path: Path) -> Optional[int]:
    """Size in bytes of ``path``'s audio re-encoded as FLAC, or None on failure.

    Rule 1 reads a compression ratio as evidence: audio that squeezes down to
    ~800 kbps has thrown information away somewhere. That is a property of the
    SAMPLES. Sizing the container instead made it a property of the FILE, and the
    same audio then answered differently depending on how it had been packaged —
    a WAV or an AIFF reads at PCM level (~1411 kbps at 44.1/16/2) however
    compressible its samples are. Issue #7: identical PCM_16 samples in four
    containers, two of them judged and two of them waved through.

    So the ratio is measured by actually compressing the audio, at one fixed
    setting, whatever it arrived in. Called only for non-FLAC sources: a FLAC is
    already its own answer, and re-encoding every FLAC in a library sweep would
    cost more than the rule is worth. The residual that leaves is small and worth
    stating: a level-8 FLAC is ~1-2 % smaller than this reference encode, so a
    FLAC sitting within ~1.5 % of one of Rule 1's window edges can still land on
    the other side from its WAV twin. The windows are ~250 kbps wide.
    """
    try:
        import soundfile as sf  # local: keeps the cold-start import cost off this module
    except ImportError:  # pragma: no cover - soundfile is a hard dependency
        return None

    tmp: Optional[Path] = None
    try:
        with sf.SoundFile(str(path)) as src:
            sixteen = src.subtype in _FLAC_16_BIT
            subtype = "PCM_16" if sixteen else "PCM_24"
            dtype = "int16" if sixteen else "int32"

            fd, tmp_name = tempfile.mkstemp(suffix=".flac")
            import os

            os.close(fd)
            tmp = Path(tmp_name)

            with sf.SoundFile(
                str(tmp),
                mode="w",
                samplerate=src.samplerate,
                channels=src.channels,
                format="FLAC",
                subtype=subtype,
            ) as dst:
                while True:
                    block = src.read(_ENCODE_BLOCK, dtype=dtype, always_2d=True)
                    if len(block) == 0:
                        break
                    dst.write(block)

        size = tmp.stat().st_size
        return size if size > 0 else None
    except Exception as e:  # noqa: BLE001 - never let sizing break an analysis
        logger.warning(f"Could not measure FLAC-equivalent size for {path}: {e}")
        return None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def decode_to_wav(path: Path) -> Optional[Path]:
    """Decode a non-native lossless source to a temp WAV (PCM) via ffmpeg.

    Returns the temp WAV path (caller deletes it), or None if ffmpeg is missing or
    the decode fails. Lets the rest of the pipeline treat ALAC/APE as a plain WAV.
    """
    if shutil.which("ffmpeg") is None:
        logger.error(
            f"ffmpeg not found on PATH — required to analyse {path.suffix} files. "
            "Install ffmpeg, or this file is skipped."
        )
        return None
    fd, tmp_name = tempfile.mkstemp(suffix=".wav")
    import os

    os.close(fd)
    tmp = Path(tmp_name)
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vn", str(tmp)],
            capture_output=True,
            timeout=300,
        )
        if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
            logger.warning(f"ffmpeg decode failed for {path}")
            tmp.unlink(missing_ok=True)
            return None
        return tmp
    except subprocess.SubprocessError as e:
        logger.warning(f"ffmpeg decode error for {path}: {e}")
        tmp.unlink(missing_ok=True)
        return None
