#!/usr/bin/env python3
"""The rate an encoder is asked for is not the rate it emits — audited on our arms.

Provir's harness lesson, 2026-08-21, verbatim class: Microsoft's MediaFoundation
AC-3 encoder emits 256 kbps whatever ``-b:a`` says and exits clean; ffmpeg's
wmav2 overshoots the request by 1.1–1.7×. Neither prints a warning. Cells keyed
by a REQUESTED rate silently lie about which quantiser they measured.

Our audit corpus keys nine arms by requested rate — and our ``aacmf_256`` arm is
MediaFoundation, the same vendor as his discovery. The transcode pipeline
discards the lossy intermediate, so nothing ever checked what was actually
emitted. This audit re-encodes a sample per arm, KEEPS the intermediate long
enough to weigh it, and reports emitted kbps (payload bytes × 8 / seconds)
against the requested figure. Quality-mode arms (``mp3_V0``, ``vorbis_q8``)
have no requested rate and are reported as observed-only.

Verdict per cell: OK within ±15 % of the request, RATE_OFF outside it — his
sweep's convention, adopted as-is.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from build_audit_corpus import CODECS  # noqa: E402

AUDIT = Path(r"C:\Users\loutr\audit_corpus\authentic")
SAMPLE = 3
TOLERANCE = 0.15

REQUESTED = {
    "mp3_192": 192,
    "mp3_320": 320,
    "mp3_V0": None,
    "aac_ff128": 128,
    "aac_ff256": 256,
    "aac_ff320": 320,
    "aacmf_256": 256,
    "opus_256": 256,
    "vorbis_q8": None,
}


def emitted_kbps(src: Path, codec, tmp: Path) -> Optional[float]:
    lossy = tmp / f"x.{codec.ext}"
    r = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-c:a",
            codec.encoder,
            *codec.args,
            str(lossy),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not lossy.exists():
        return None
    seconds = sf.info(str(src)).frames / sf.info(str(src)).samplerate
    return lossy.stat().st_size * 8.0 / seconds / 1000.0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=SAMPLE)
    args = parser.parse_args(argv)

    sources = sorted(AUDIT.glob("*.flac"))[: args.sample]
    if not sources:
        raise SystemExit(f"no sources under {AUDIT}")

    print(
        f"{'arm':12}{'requested':>10}{'emitted (median of {n})':>24}{'verdict':>10}".format(
            n=len(sources)
        )
    )
    off = 0
    for codec in CODECS:
        rates: List[float] = []
        with tempfile.TemporaryDirectory() as tmp:
            for src in sources:
                kbps = emitted_kbps(src, codec, Path(tmp))
                if kbps is not None:
                    rates.append(kbps)
        if not rates:
            print(f"{codec.name:12}{'-':>10}{'ENCODE FAILED':>24}{'-':>10}")
            continue
        rates.sort()
        median = rates[len(rates) // 2]
        requested = REQUESTED.get(codec.name)
        if requested is None:
            print(f"{codec.name:12}{'(quality)':>10}{median:>20.0f} kbps{'observed':>10}")
            continue
        ok = abs(median - requested) / requested <= TOLERANCE
        verdict = "OK" if ok else "RATE_OFF"
        if not ok:
            off += 1
        print(f"{codec.name:12}{requested:>10}{median:>20.0f} kbps{verdict:>10}")

    print(
        f"\n{off} arm(s) RATE_OFF. A cell keyed by a requested rate that the "
        "encoder ignores is measuring a different quantiser than its label claims."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
