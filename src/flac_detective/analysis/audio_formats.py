"""Format detection and decoding for analysable lossless inputs.

FLAC, WAV and AIFF are read natively by libsndfile (soundfile). Other lossless
containers — ALAC (in .m4a), APE, and the archival video containers — need
ffmpeg, which is a hard runtime requirement for *those* formats (FLAC/WAV/AIFF
never touch ffmpeg).

The tricky case is a container that can hold either: ``.m4a`` holds ALAC
(lossless → analyse) or AAC (lossy → reject); a Matroska, QuickTime or MXF
file holds LPCM, FLAC or TrueHD (analyse) as readily as AC-3, AAC or a DTS core
(reject). We probe the actual codec — and for DTS its profile — with ffprobe
rather than trust the extension. The container says nothing about the audio's
history; only the detector does, once the audio is demuxed.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lossless audio codecs we analyse on their own merits (ffprobe codec_name values).
LOSSLESS_CODECS = {
    "flac",
    "alac",
    "ape",
    "wavpack",
    "tta",
    # LPCM in every byte order and width a broadcast or preservation master uses
    # (MXF and QuickTime carry big-endian PCM; Matroska little-endian).
    "pcm_s16le",
    "pcm_s24le",
    "pcm_s32le",
    "pcm_f32le",
    "pcm_f64le",
    "pcm_u8",
    "pcm_s16be",
    "pcm_s24be",
    "pcm_s32be",
    "pcm_f32be",
    "pcm_f64be",
    # Dolby's lossless pair: TrueHD and its ancestor MLP (DVD-Audio).
    "truehd",
    "mlp",
}

# DTS is one codec_name for a lossy core and a lossless extension. Only the
# Master Audio profile decodes to the original PCM; DTS, DTS-HD HRA, DTS
# Express and DTS:X's lossy layers do not. ffprobe reports it as ``profile``.
LOSSLESS_DTS_PROFILES = {"DTS-HD MA"}

# Extensions libsndfile reads directly — no ffmpeg, no probe needed.
NATIVE_SUFFIXES = {".flac", ".wav", ".aiff", ".aif"}

# Extensions whose container may hold either lossless or lossy audio — probe to decide.
# The video containers are the archival kind: LPCM or FLAC in Matroska (FFV1
# preservation masters), LPCM in MXF (broadcast) and QuickTime, TrueHD or
# DTS-HD MA alongside a Blu-ray remux. Their first audio stream is what is
# probed and, if lossless, demuxed and analysed like any other file.
PROBE_SUFFIXES = {".m4a", ".mp4", ".ape", ".tta", ".wv", ".mkv", ".mka", ".mov", ".mxf"}

# Extensions that never hold lossless audio: a file with one of these is a
# reject ("replace with a real FLAC"), never a candidate for analysis.
LOSSY_SUFFIXES = {".mp3", ".aac", ".ogg", ".wma", ".opus"}


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


def probe_stream(path: Path) -> Optional[Dict[str, str]]:
    """Return the first audio stream's codec_name, profile, sample_fmt and bit depth.

    A dict of the ffprobe fields (``codec_name``, ``profile``, ``sample_fmt``,
    ``bits_per_raw_sample``, ``bits_per_sample``), values as ffprobe prints
    them, or None on failure. ``probe_codec`` stays the single-field reader the
    routing relies on; this one is consulted where the codec alone does not
    settle it (a DTS stream's profile) and to size the decode (bit depth).
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name,profile,sample_fmt,bits_per_raw_sample,bits_per_sample",
                "-of",
                "default=noprint_wrappers=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        fields: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            key, sep, value = line.partition("=")
            if sep:
                fields[key.strip().lower()] = value.strip()
        return fields or None
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.debug(f"ffprobe failed for {path}: {e}")
        return None


def is_analysable_lossless(path: Path) -> bool:
    """True if the file is a lossless audio source worth analysing.

    FLAC/WAV/AIFF by extension; everything else by probing the container's real
    codec. Lossy containers (an AAC .m4a, an AC-3 .mkv, a DTS core) return
    False — they belong in the reject list. A DTS stream is lossless only in
    its Master Audio profile, so that one is decided on the profile.
    """
    suffix = path.suffix.lower()
    if suffix in NATIVE_SUFFIXES:
        return True
    if suffix in PROBE_SUFFIXES:
        codec = probe_codec(path)
        if not codec:
            return False
        if codec == "dts":
            info = probe_stream(path) or {}
            return info.get("profile", "") in LOSSLESS_DTS_PROFILES
        return codec in LOSSLESS_CODECS
    return False


def discover_audio_files(root_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Every audio file under ``root_dir``, sorted into (analysable, rejects).

    Analysable: the native formats by extension, and every probe-able container
    whose first audio stream is lossless. Rejects: the lossy-only extensions,
    and a probe-able container that holds lossy audio. One walk of the tree,
    one decision per file, the same decision ``scan_files`` makes for a file
    passed directly — a directory scan used to pick up ``.flac`` and ``.wav``
    only, so an ``.aiff`` in a folder was never analysed while the same file
    passed on the command line was (found 2026-09-15 on a Beatport A/B).
    """
    analysable: List[Path] = []
    rejects: List[Path] = []
    for candidate in sorted(root_dir.rglob("*")):
        if not candidate.is_file():
            continue
        suffix = candidate.suffix.lower()
        if suffix in NATIVE_SUFFIXES:
            analysable.append(candidate)
        elif suffix in PROBE_SUFFIXES:
            (analysable if is_analysable_lossless(candidate) else rejects).append(candidate)
        elif suffix in LOSSY_SUFFIXES:
            rejects.append(candidate)
    logger.info(f"Scanning folder: {root_dir} — {len(analysable)} analysable, {len(rejects)} lossy")
    return analysable, rejects


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
    setting, whatever it arrived in — **including when it arrived as a FLAC**.
    Exempting FLAC looks free (a FLAC is already a compressed size) and is not: a
    stored FLAC was encoded at whatever level its ripper chose, which is not this
    function's level, and the engine then holds two rulers that disagree. Measured
    on 120 corpus files: mean 0.63 %, p95 1.46 %, max 4.17 %. Rule 1's cell edges
    are 50 kbps apart, so that spread straddles an edge on 7.5 % of them. See the
    comment in analyzer.py for the file that reads AUTHENTIC as FLAC and
    FAKE_CERTAIN as WAV on exactly that 0.4 % difference.

    Sizing every container the same way makes the number exactly reproducible, so
    Rule 1's sharp edges become legitimate again rather than an accident of
    packaging. The cost is a re-encode per file, paid on every analysis.
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


def flac_segment_bitrates(path: Path, n_segments: int = 10) -> Optional[list]:
    """Bitrate in kbps of each of ``n_segments`` slices, each compressed on its own.

    The statistic Rules 5 and 6 were written to read: a lossless encoder spends
    more bits on dense passages than on sparse ones, so genuine music varies
    across a track while a decoded constant-bitrate transcode does not.

    ``calculate_bitrate_variance`` claimed to measure it and did not — it divided
    the file size by ten, ten times, and took the standard deviation of ten
    identical numbers, returning 0.0 for every file ever analysed. This is the
    measurement it was describing.

    Costs one encode of the whole file, split into slices: ~1 s for a 60-second
    track of real music. Returns None when the file cannot be read or the slices
    would be shorter than a second, where the statistic means nothing.
    """
    try:
        import soundfile as sf
    except ImportError:  # pragma: no cover - soundfile is a hard dependency
        return None

    try:
        info = sf.info(str(path))
        frames_per = info.frames // n_segments
        if frames_per < info.samplerate:
            return None
        sixteen = info.subtype in _FLAC_16_BIT
        subtype = "PCM_16" if sixteen else "PCM_24"
        dtype = "int16" if sixteen else "int32"

        out = []
        with sf.SoundFile(str(path)) as src, tempfile.TemporaryDirectory() as td:
            for k in range(n_segments):
                src.seek(k * frames_per)
                block = src.read(frames_per, dtype=dtype, always_2d=True)
                if len(block) == 0:
                    break
                slice_path = Path(td) / f"seg{k}.flac"
                sf.write(str(slice_path), block, info.samplerate, subtype=subtype, format="FLAC")
                seconds = len(block) / info.samplerate
                out.append(slice_path.stat().st_size * 8 / (seconds * 1000))
        return out or None
    except Exception as e:  # noqa: BLE001 - never let a statistic break an analysis
        logger.warning(f"Could not measure segment bitrates for {path}: {e}")
        return None


def _pcm_codec_for(info: Optional[Dict[str, str]]) -> str:
    """The WAV sample format that keeps every bit of the probed stream.

    ffmpeg's WAV muxer defaults to 16-bit; a 24-bit ALAC or TrueHD stream
    decoded through that default was truncated before analysis, and the
    bit-depth rules then read a 16-bit file. Anything wider than 16 bits, or
    carried as 32-bit / float samples, is written as 24-bit PCM.
    """
    if not info:
        return "pcm_s16le"
    for key in ("bits_per_raw_sample", "bits_per_sample"):
        try:
            if int(info.get(key, "0")) > 16:
                return "pcm_s24le"
        except ValueError:
            continue
    if info.get("sample_fmt", "") in {"s32", "s32p", "flt", "fltp", "dbl", "dblp"}:
        return "pcm_s24le"
    return "pcm_s16le"


def decode_to_wav(path: Path) -> Optional[Path]:
    """Decode a non-native lossless source to a temp WAV (PCM) via ffmpeg.

    Returns the temp WAV path (caller deletes it), or None if ffmpeg is missing or
    the decode fails. Lets the rest of the pipeline treat ALAC/APE/TrueHD, or the
    audio of a Matroska/MXF/QuickTime file, as a plain WAV. The FIRST audio
    stream is taken — the one ``probe_codec`` judged — and video is dropped.
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
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-vn",
                "-c:a",
                _pcm_codec_for(probe_stream(path)),
                str(tmp),
            ],
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
