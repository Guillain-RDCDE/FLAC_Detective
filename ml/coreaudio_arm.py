#!/usr/bin/env python3
"""Build and measure an Apple CoreAudio AAC arm — the one encoder we cannot run locally.

Why this file exists
--------------------
Rule 13 reads the alignment fingerprint left by MDCT quantisation, and it is
excellent on ffmpeg-family AAC (AUC 0.99) and merely good on Microsoft's
MediaFoundation encoder (0.791). Jamie Dodd of Provir measured it against
**Apple CoreAudio** and reported that it contributes *nothing at all* — a clean
zero, not a degradation. That was the sharpest open hole in the rule, and it sat
open because "we have no Mac" was treated as the end of the sentence.

It is not. FLAC Detective's repository is public, and GitHub gives public
repositories free unlimited standard macOS runners. ``afconvert`` ships with
macOS and drives the *same* CoreAudio encoder that ``qaac`` wraps on Windows. So
the arm we could not build is a CI job.

What it measures
----------------
Paired, not pooled: each source is measured as-is *and* after a CoreAudio
round-trip, so the genuine baseline and the transcode come from the same music.
That removes the "different material" confound that an unpaired arm carries, and
it is a stricter test than the audit corpus does for the other encoders.

Deliberately no ffmpeg anywhere in the chain — it is not guaranteed on the runner
image, and more importantly a measurement of Apple's encoder should not route
through the encoder family it is being compared against. ``soundfile`` reads the
source excerpt, ``afconvert`` does both the encode and the decode.

Usage::

    python ml/coreaudio_arm.py --src wild_authentic --out ml/coreaudio_arm.csv
"""

from __future__ import annotations

import argparse
import csv
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.new_scoring.mdct import best_alignment_stat  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lattice_residual_probe import lattice_stat  # noqa: E402

from flac_detective.analysis.new_scoring.stereo_image import (  # noqa: E402
    side_dead_run,
)
from flac_detective.analysis.new_scoring.temporal import temporal_seam  # noqa: E402

# Bitrates worth testing. 256k is the arm Jamie measured and the one that matters:
# below ~192k the spectral rules convict on their own, so a transform statistic
# that only worked there would be redundant.
DEFAULT_BITRATES = (128_000, 256_000, 320_000)

EXCERPT_SEC = 30.0

# afconvert bitrate strategy: 0 = CBR. Constant rate keeps the quantiser step
# stable across the excerpt, which is the condition the statistic is happiest
# under — and it is the strategy a transcoder-for-distribution would pick.
STRATEGY_CBR = "0"


def require_macos() -> str:
    """Return the afconvert path, or explain precisely why this cannot run here."""
    exe = shutil.which("afconvert")
    if exe:
        return exe
    raise SystemExit(
        f"afconvert not found (platform={platform.system()}). This arm exists to test "
        "Apple's CoreAudio encoder and can only be built on macOS. Run it on the "
        "macos-latest job in .github/workflows/coreaudio-arm.yml, which is free for "
        "this repository."
    )


def read_excerpt(path: Path, seconds: float = EXCERPT_SEC) -> Tuple[np.ndarray, int]:
    """Read the first ``seconds`` of ``path`` as float32."""
    info = sf.info(str(path))
    frames = int(seconds * info.samplerate)
    data, rate = sf.read(str(path), dtype="float32", frames=frames)
    return data, int(rate)


def _run(cmd: List[str]) -> None:
    """Run ``cmd``, raising with afconvert's own message on failure."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}): {proc.stderr.strip()[:300]}")


def coreaudio_roundtrip(src_wav: Path, work: Path, bitrate: int, afconvert: str) -> Path:
    """Encode ``src_wav`` to CoreAudio AAC and decode it straight back to WAV."""
    encoded = work / f"enc_{bitrate}.m4a"
    decoded = work / f"dec_{bitrate}.wav"
    _run([afconvert, "-f", "m4af", "-d", "aac", "-b", str(bitrate),
          "-s", STRATEGY_CBR, str(src_wav), str(encoded)])
    _run([afconvert, "-f", "WAVE", "-d", "LEI16", str(encoded), str(decoded)])
    return decoded


def statistic(path: Path) -> Tuple[float, int, str]:
    """Rule 13's peak-ratio statistic on ``path``, with no early stop.

    ``stop_at`` is disabled on purpose: the pipeline short-circuits once a reading
    is good enough to act on, but a calibration measurement wants the true value.
    """
    data, rate = read_excerpt(path)
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    return best_alignment_stat(
        np.ascontiguousarray(mono, dtype=np.float32), rate, stop_at=float("inf")
    )


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC: P(a random fake scores above a random genuine)."""
    if not len(fake) or not len(genuine):
        return float("nan")
    order = np.argsort(np.concatenate([fake, genuine]), kind="mergesort")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    # Average ranks over ties, or a codec that sits exactly on the null reads high.
    values = np.concatenate([fake, genuine])
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    rank_sum = ranks[: len(fake)].sum()
    return float((rank_sum - len(fake) * (len(fake) + 1) / 2) / (len(fake) * len(genuine)))


def main(argv: Optional[List[str]] = None) -> int:
    """Build the arm and report what Rule 13 reads on it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True, help="directory of genuine FLACs")
    parser.add_argument("--out", type=Path, default=Path("ml/coreaudio_arm.csv"))
    parser.add_argument("--limit", type=int, default=0, help="cap sources (0 = all)")
    parser.add_argument("--bitrates", type=int, nargs="+", default=list(DEFAULT_BITRATES))
    args = parser.parse_args(argv)

    afconvert = require_macos()
    sources = sorted(args.src.rglob("*.flac"))
    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        raise SystemExit(f"no .flac under {args.src}")
    print(f"{len(sources)} sources, bitrates {args.bitrates}", flush=True)

    rows: List[dict] = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "source", "arm", "ratio", "offset", "hypothesis", "lattice",
                "temporal", "stereo",
            ],
        )
        writer.writeheader()
        for index, src in enumerate(sources, 1):
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                src_wav = work / "src.wav"
                try:
                    data, rate = read_excerpt(src)
                    if data.size == 0:
                        print(f"  [{index}] {src.name}: empty excerpt, skipped", flush=True)
                        continue
                    sf.write(str(src_wav), data, rate, subtype="PCM_16")
                except Exception as exc:  # unreadable source is not evidence of anything
                    print(f"  [{index}] {src.name}: unreadable ({exc}), skipped", flush=True)
                    continue

                measurements = [("genuine", src_wav)]
                for bitrate in args.bitrates:
                    try:
                        measurements.append(
                            (f"coreaudio_{bitrate // 1000}",
                             coreaudio_roundtrip(src_wav, work, bitrate, afconvert))
                        )
                    except RuntimeError as exc:
                        print(f"  [{index}] {src.name}: {bitrate} failed ({exc})", flush=True)

                for arm, path in measurements:
                    ratio, offset, hypothesis = statistic(path)
                    # The lattice is read at the alignment the scan just found, so
                    # the second observable costs no second search. It is the one
                    # that might reach CoreAudio, where holes measure ~nothing.
                    try:
                        data, rate = read_excerpt(path)
                        mono = data if data.ndim == 1 else np.mean(data, axis=1)
                        lattice = lattice_stat(
                            np.ascontiguousarray(mono, dtype=np.float32), rate,
                            offset=max(0, offset),
                        )
                    except Exception:
                        lattice = float("nan")
                    # The two families added in v1.11. CoreAudio is the arm every
                    # alignment-dependent observable failed on, so the question this
                    # answers is whether either of the new ones reaches it.
                    try:
                        data, rate = read_excerpt(path)
                        mono = data if data.ndim == 1 else np.mean(data, axis=1)
                        temporal, _hz = temporal_seam(
                            np.ascontiguousarray(mono, dtype=np.float32), rate
                        )
                        stereo, _ratio = side_dead_run(
                            data if data.ndim > 1 else data[:, None], rate
                        )
                    except Exception:
                        temporal = stereo = float("nan")
                    row = {"source": src.name, "arm": arm, "ratio": f"{ratio:.4f}",
                           "offset": offset, "hypothesis": hypothesis,
                           "lattice": f"{lattice:.4f}", "temporal": f"{temporal:.4f}",
                           "stereo": f"{stereo:.4f}"}
                    writer.writerow(row)
                    rows.append({**row, "ratio": ratio, "lattice": lattice,
                                 "temporal": temporal, "stereo": stereo})
                fh.flush()
            print(f"  [{index}/{len(sources)}] {src.name}", flush=True)

    report(rows)
    return 0


def report(rows: List[dict]) -> None:
    """Print the comparison this arm exists to settle."""
    arms = sorted({r["arm"] for r in rows})
    genuine = np.array([r["ratio"] for r in rows if r["arm"] == "genuine"], dtype=np.float64)
    genuine = genuine[np.isfinite(genuine)]

    print("\n" + "=" * 64)
    print("Apple CoreAudio AAC — what Rule 13 reads")
    print("=" * 64)
    lat_gen_all = np.array([r["lattice"] for r in rows if r["arm"] == "genuine"],
                           dtype=np.float64)
    lat_gen_all = lat_gen_all[np.isfinite(lat_gen_all)]
    if genuine.size:
        extra = (f"  |  lattice median={np.median(lat_gen_all):5.3f}"
                 if lat_gen_all.size else "")
        print(f"genuine baseline  n={genuine.size:3d}  holes median="
              f"{np.median(genuine):6.3f}  max={genuine.max():6.3f}{extra}")
    for arm in arms:
        if arm == "genuine":
            continue
        values = np.array([r["ratio"] for r in rows if r["arm"] == arm], dtype=np.float64)
        values = values[np.isfinite(values)]
        if not values.size:
            continue
        # Paired: the same music with and without the round-trip.
        lat = np.array([r["lattice"] for r in rows if r["arm"] == arm], dtype=np.float64)
        lat = lat[np.isfinite(lat)]
        lat_gen = np.array([r["lattice"] for r in rows if r["arm"] == "genuine"],
                           dtype=np.float64)
        lat_gen = lat_gen[np.isfinite(lat_gen)]
        lat_txt = (f"  lattice={auc(lat, lat_gen):.2f}") if lat.size and lat_gen.size else ""

        def _auc_of(field: str, arm: str = arm) -> str:
            fake = np.array([r[field] for r in rows if r["arm"] == arm], dtype=np.float64)
            gen = np.array([r[field] for r in rows if r["arm"] == "genuine"], dtype=np.float64)
            fake, gen = fake[np.isfinite(fake)], gen[np.isfinite(gen)]
            return f"  {field[:4]}={auc(fake, gen):.2f}" if fake.size and gen.size else ""

        print(f"{arm:17} n={values.size:3d}  holes={auc(values, genuine):.2f}"
              f"{lat_txt}{_auc_of('temporal')}{_auc_of('stereo')}")
    print(
        "\nReference points from the audit corpus, same statistic:\n"
        "  ffmpeg AAC      median 13.6-21.5   AUC 0.99\n"
        "  MediaFoundation median  2.66       AUC 0.791\n"
        "  genuine         median  1.28       max 1.427   (review bar 2.0)\n"
        "An AUC near 0.5 with a median near the genuine one reproduces Provir's\n"
        "finding: CoreAudio leaves no holes for this statistic to count."
    )


if __name__ == "__main__":
    raise SystemExit(main())
