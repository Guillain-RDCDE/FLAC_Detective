#!/usr/bin/env python3
"""Widen the transcode zoo with EXTERNAL (non-ffmpeg) encoders.

``generate_transcodes.py`` builds the training/test fakes with ffmpeg's built-in
encoders (libmp3lame, aac, libopus, libvorbis). But the model can learn an
*encoder* fingerprint that way and then mis-handle the same codec produced by a
*different* encoder — which is exactly what real-world fakes are. This script
produces fakes with standalone, widely-used encoders so you can (a) build an
out-of-distribution test set for ``measure_auc_drop.py`` and (b) optionally fold
them into training to harden generalisation.

Each fake is built as: FLAC --(ffmpeg)--> WAV --(external encoder)--> lossy
--(ffmpeg)--> FLAC. ffmpeg is used only as neutral glue for the FLAC<->WAV
container steps; the *lossy* step — the part that leaves the fingerprint — is the
external encoder. Only encoders found on PATH are run; the rest are skipped with a
note, so this is useful on any box without installing everything.

Supported encoders (auto-detected): lame (LAME), qaac/qaac64 (Apple AAC),
fdkaac (Fraunhofer AAC), oggenc (Vorbis), opusenc (Opus), afconvert (macOS AAC).

Usage::

    python ml/generate_transcodes_external.py \
        --input dataset/authentic --output dataset/transcoded_external --workers 8
"""

from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtCodec:
    name: str  # output subdir, e.g. "lame_v0"
    binary: str  # external executable name on PATH
    ext: str  # intermediate lossy extension
    # arg template: a tuple where "{in}" / "{out}" are substituted with the WAV / lossy paths.
    args: Tuple[str, ...] = field(default_factory=tuple)


# Each entry is a distinct encoder/preset NOT covered by ffmpeg's built-ins. The
# point is encoder diversity for the same codec family, so the model can't key on
# one encoder's quirks. Bitrates chosen to overlap the ffmpeg zoo for comparability.
EXT_CODECS = (
    # Standalone LAME — the reference MP3 encoder; CBR 320 and VBR V0/V2.
    ExtCodec("lame_320", "lame", "mp3", ("-b", "320", "--quiet", "{in}", "{out}")),
    ExtCodec("lame_v0", "lame", "mp3", ("-V", "0", "--quiet", "{in}", "{out}")),
    ExtCodec("lame_v2", "lame", "mp3", ("-V", "2", "--quiet", "{in}", "{out}")),
    # Apple AAC via qaac (Windows; needs Apple Application Support). TVBR ~256k.
    ExtCodec("qaac_256", "qaac", "m4a", ("--tvbr", "91", "-o", "{out}", "{in}")),
    ExtCodec("qaac64_256", "qaac64", "m4a", ("--tvbr", "91", "-o", "{out}", "{in}")),
    # Fraunhofer FDK AAC — a different AAC encoder again.
    ExtCodec("fdkaac_256", "fdkaac", "m4a", ("-b", "256", "-o", "{out}", "{in}")),
    # Vorbis via vorbis-tools oggenc (vs ffmpeg's libvorbis).
    ExtCodec("oggenc_q5", "oggenc", "ogg", ("-q", "5", "-o", "{out}", "{in}")),
    # Opus via opus-tools opusenc (vs ffmpeg's libopus).
    ExtCodec("opusenc_128", "opusenc", "opus", ("--bitrate", "128", "{in}", "{out}")),
    # macOS AAC via afconvert.
    ExtCodec(
        "afconvert_256",
        "afconvert",
        "m4a",
        ("-f", "m4af", "-d", "aac", "-b", "256000", "{in}", "{out}"),
    ),
)


def _available_codecs() -> List[ExtCodec]:
    """Filter the zoo to encoders actually present on PATH."""
    avail = [c for c in EXT_CODECS if shutil.which(c.binary)]
    missing = sorted({c.binary for c in EXT_CODECS} - {c.binary for c in avail})
    if missing:
        log.info("Skipping unavailable encoders: %s", ", ".join(missing))
    return avail


def transcode_one(job: Tuple[Path, Path, Path, ExtCodec]) -> Tuple[str, bool, str]:
    """Worker: FLAC -> WAV -> external lossy -> FLAC. Non-fatal on error."""
    src, output_root, input_root, codec = job
    try:
        rel = src.relative_to(input_root)
    except ValueError:
        return (str(src), False, "src not under input_root")
    dst = output_root / codec.name / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file() and dst.stat().st_size > 1024:
        return (f"{codec.name}/{rel}", True, "skipped (exists)")

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        lossy = Path(td) / f"a.{codec.ext}"
        # FLAC -> WAV (ffmpeg, neutral).
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", str(wav)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return (f"{codec.name}/{rel}", False, f"flac->wav: {r.stderr.strip()[:160]}")
        # WAV -> lossy (the external encoder — the fingerprint step).
        cmd = [codec.binary] + [
            str(wav) if a == "{in}" else str(lossy) if a == "{out}" else a for a in codec.args
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not lossy.is_file():
            return (f"{codec.name}/{rel}", False, f"{codec.binary}: {r.stderr.strip()[:160]}")
        # lossy -> FLAC (ffmpeg).
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(lossy), "-c:a", "flac", str(dst)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            dst.unlink(missing_ok=True)
            return (f"{codec.name}/{rel}", False, f"lossy->flac: {r.stderr.strip()[:160]}")
    return (f"{codec.name}/{rel}", True, "ok")


def main(input_root: Path, output_root: Path, workers: int) -> int:
    """Plan and run external-encoder transcodes over every FLAC under input_root."""
    if shutil.which("ffmpeg") is None:
        log.error("ffmpeg not found on PATH (needed as FLAC<->WAV glue).")
        return 1
    if not input_root.is_dir():
        log.error("Input directory not found: %s", input_root)
        return 1
    codecs = _available_codecs()
    if not codecs:
        log.error(
            "No external encoders found on PATH. Install e.g. lame, opus-tools, vorbis-tools."
        )
        return 1
    output_root.mkdir(parents=True, exist_ok=True)

    flacs = sorted(input_root.rglob("*.flac"))
    jobs = [(src, output_root, input_root, c) for src in flacs for c in codecs]
    log.info(
        "Planned %d jobs (%d files × %d external codecs: %s)",
        len(jobs),
        len(flacs),
        len(codecs),
        ", ".join(c.name for c in codecs),
    )

    ok = fail = skipped = 0
    try:
        from tqdm import tqdm

        progress = tqdm(total=len(jobs), unit="file")
    except ImportError:
        progress = None
    with mp.Pool(processes=workers) as pool:
        for key, success, msg in pool.imap_unordered(transcode_one, jobs, chunksize=4):
            if success:
                skipped += msg == "skipped (exists)"
                ok += msg == "ok"
            else:
                fail += 1
                log.warning("FAIL %s: %s", key, msg)
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=ok, skip=skipped, fail=fail)
    if progress is not None:
        progress.close()
    log.info("Done. ok=%d skipped=%d fail=%d total=%d", ok, skipped, fail, len(jobs))
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", default="dataset/authentic")
    p.add_argument("--output", default="dataset/transcoded_external")
    p.add_argument("--workers", type=int, default=min(8, mp.cpu_count()))
    args = p.parse_args()
    sys.exit(main(Path(args.input), Path(args.output), args.workers))
