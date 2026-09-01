#!/usr/bin/env python3
"""Probe: does MDCT quantisation leave a readable trace at high bitrate?

Motivation. Every detector FLAC Detective currently ships looks ABOVE the
encoder's cutoff — pre-echo, HF aliasing, the noise-pattern test, the spectral
cliff, and the CNN's effective attention all live in the 10–20 kHz band. At
256–320 kbps AAC there is nothing up there to find: the encoder keeps the band.
Measured consequence (ml/README.md): mp3_320 detectability AUC 0.53, i.e. none.

The idea being tested here is different in kind. It does not look for missing
energy; it looks for the *shape the encoder's arithmetic left behind*. An MDCT
codec quantises transform coefficients, and quantising sends a large fraction of
them to exactly zero. Those zeros survive decoding: re-analyse the decoded signal
with the SAME transform (same frame length, same window, same sample alignment)
and the zeroed bins reappear as deep holes. Analyse it at any other alignment and
the holes smear away.

So the statistic is not "are there holes" — genuine music has holes too — it is
"is there ONE frame alignment at which holes are dramatically more common than at
every other alignment". Genuine lossless audio has no preferred alignment: the
curve is flat. That is the analytic null, and it is what makes the test work
where cutoff-gated heuristics stop.

Two implementation details decide whether this reads anything at all:

  * The window must match the encoder's. ffmpeg-family AAC uses a KBD window with
    alpha=4 for long blocks, NOT the sine window. With a sine analysis window the
    statistic sits at the floor and the test looks dead. (Credit: Jamie Dodd
    flagged this trap, and it is real — ``--window sine`` reproduces the floor.)
  * The alignment scan must be sample-exact. The encoder's priming delay is
    arbitrary, so the correct offset is unknown a priori and must be searched over
    the whole hop.

This file is a MEASUREMENT, not a rule. It prints AUC per codec. Only if the
numbers hold does any of it belong in the scoring pipeline.

Usage::

    python ml/mdct_probe.py curve  --file <one.flac>          # inspect the scan
    python ml/mdct_probe.py sweep  --corpus <dir> --out ml/mdct_probe.csv
    python ml/mdct_probe.py report --csv ml/mdct_probe.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import multiprocessing as mp
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import soundfile as sf

# The algorithm itself lives in the package, not here: this file is a measurement
# harness on top of the shipped implementation. Two copies would drift, and the
# whole point of the exercise is that what gets measured is what gets shipped.
from flac_detective.analysis.new_scoring.mdct import (
    WINDOW_LEN,
)
from flac_detective.analysis.new_scoring.mdct import alignment_curve as _alignment_curve  # noqa: E402
from flac_detective.analysis.new_scoring.mdct import alignment_stat, kbd_window, sine_window

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def alignment_curve(x, sample_rate, window_kind="kbd", n_frames=24, offsets=None, ref_size=33):
    """Thin wrapper: pick the window by name, then defer to the shipped code."""
    window = kbd_window() if window_kind == "kbd" else sine_window()
    return _alignment_curve(
        x, sample_rate, window, n_frames=n_frames, offsets=offsets, ref_size=ref_size
    )


def load_mono(path: str, seconds: float = 30.0) -> Tuple[np.ndarray, int]:
    """Load a mono float32 excerpt from the middle of ``path``."""
    info = sf.info(path)
    start = max(0, int((info.duration - seconds) / 2 * info.samplerate))
    data, sr = sf.read(path, start=start, frames=int(seconds * info.samplerate), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    return np.ascontiguousarray(data), sr


def peak_ratio(curve: np.ndarray) -> float:
    """Peak-to-median of the alignment curve — the actual test statistic.

    1.0 means "no alignment is special", which is what genuine lossless audio
    should give. The ratio, not the peak height, is the point: it is normalised
    against the file's own baseline, so quiet or dense material does not shift it.
    """
    finite = curve[np.isfinite(curve)]
    if finite.size == 0:
        return float("nan")
    med = float(np.median(finite))
    if med <= 0:
        # No holes anywhere except at one alignment is the strongest possible
        # evidence, but it is also what an all-zero curve looks like; separate them.
        return float(finite.max() / 1e-6) if finite.max() > 0 else 1.0
    return float(finite.max() / med)


def _probe_one(job: Tuple[str, int, str, str, str]) -> Optional[Dict[str, object]]:
    """Compute the statistic for one file."""
    path, label, codec, slug, window_kind = job
    try:
        x, sr = load_mono(path)
        if len(x) < WINDOW_LEN * 8:
            return None
        ratio, offset = alignment_stat(x, sr, window_kind=window_kind)
    except Exception as exc:
        log.warning("probe failed on %s: %s", path, exc)
        return None
    # No absolute path: this CSV is committed as evidence for ml/README.md.
    return {
        "slug": slug,
        "label": label,
        "codec": codec,
        "window": window_kind,
        "peak_ratio": round(ratio, 4),
        "best_offset": offset,
    }


def auc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Mann-Whitney AUC (ties 0.5)."""
    pos = [v for v in pos if v == v]
    neg = [v for v in neg if v == v]
    if not pos or not neg:
        return float("nan")
    total = 0.0
    for a in pos:
        for b in neg:
            total += 1.0 if a > b else (0.5 if a == b else 0.0)
    return total / (len(pos) * len(neg))


def cmd_curve(args: argparse.Namespace) -> int:
    """Print the alignment curve for one file — the diagnostic view."""
    x, sr = load_mono(str(args.file))
    print(f"file        : {args.file}")
    print(f"window      : {args.window}")
    if args.full:
        curve = alignment_curve(x, sr, window_kind=args.window, n_frames=args.frames)
        finite = curve[np.isfinite(curve)]
        print(f"median hole : {np.median(finite):.5f}")
        print(f"max hole    : {finite.max():.5f} at offset {int(np.nanargmax(curve))}")
        print(f"PEAK RATIO  : {peak_ratio(curve):.3f}  (exhaustive scan)")
        top = np.argsort(curve)[::-1][:8]
        print("top offsets :", ", ".join(f"{int(o)}({curve[o]:.4f})" for o in top))
    else:
        ratio, offset = alignment_stat(x, sr, window_kind=args.window, fine_frames=args.frames)
        print(f"PEAK RATIO  : {ratio:.3f} at offset {offset}  (two-stage)")
    return 0


def _jobs(corpus: Path, window_kind: str) -> List[Tuple[str, int, str, str, str]]:
    """Enumerate corpus files."""
    jobs = [
        (str(f), 0, "authentic", f.stem, window_kind)
        for f in sorted((corpus / "authentic").glob("*.flac"))
    ]
    for codec_dir in sorted((corpus / "fake").glob("*")):
        if codec_dir.is_dir():
            jobs += [
                (str(f), 1, codec_dir.name, f.stem, window_kind)
                for f in sorted(codec_dir.glob("*.flac"))
            ]
    return jobs


def cmd_sweep(args: argparse.Namespace) -> int:
    """Run the probe over a whole corpus."""
    jobs = _jobs(args.corpus, args.window)
    log.info("Probing %d files (window=%s) with %d workers…", len(jobs), args.window, args.workers)
    rows: List[Dict[str, object]] = []
    with mp.Pool(args.workers) as pool:
        for n, row in enumerate(pool.imap_unordered(_probe_one, jobs, chunksize=1), 1):
            if row:
                rows.append(row)
            if n % 20 == 0:
                log.info("  %d/%d", n, len(jobs))
    fields = ["slug", "label", "codec", "window", "peak_ratio", "best_offset"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), args.out)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Per-codec AUC of the statistic."""
    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    gen = [float(r["peak_ratio"]) for r in rows if r["label"] == "0"]
    print(
        f"\nGenuine n={len(gen)}  median peak_ratio={np.median(gen):.3f}  "
        f"p95={np.percentile(gen, 95):.3f}\n"
    )
    print(f"{'codec':<14} {'n':>4} {'median':>8} {'AUC':>7}")
    print("-" * 36)
    fakes = [r for r in rows if r["label"] == "1"]
    for codec in sorted(set(r["codec"] for r in fakes)):
        vals = [float(r["peak_ratio"]) for r in fakes if r["codec"] == codec]
        print(f"{codec:<14} {len(vals):>4} {np.median(vals):>8.3f} {auc(vals, gen):>7.3f}")
    allv = [float(r["peak_ratio"]) for r in fakes]
    print("-" * 36)
    print(f"{'ALL':<14} {len(allv):>4} {np.median(allv):>8.3f} {auc(allv, gen):>7.3f}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("curve")
    c.add_argument("--file", required=True, type=Path)
    c.add_argument("--window", default="kbd", choices=["kbd", "sine"])
    c.add_argument("--frames", type=int, default=24)
    c.add_argument("--full", action="store_true", help="exhaustive scan of all 1024 offsets")
    c.set_defaults(func=cmd_curve)

    s = sub.add_parser("sweep")
    s.add_argument("--corpus", required=True, type=Path)
    s.add_argument("--out", type=Path, default=Path("ml/mdct_probe.csv"))
    s.add_argument("--window", default="kbd", choices=["kbd", "sine"])
    s.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 1))
    s.set_defaults(func=cmd_sweep)

    r = sub.add_parser("report")
    r.add_argument("--csv", type=Path, default=Path("ml/mdct_probe.csv"))
    r.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
