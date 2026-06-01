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
        codec = result.stdout.strip()
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
