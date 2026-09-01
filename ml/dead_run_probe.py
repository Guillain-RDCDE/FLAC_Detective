#!/usr/bin/env python3
"""Not how many bins are dead — how many die CONSECUTIVELY.

Where this came from
--------------------
Not from Provir's prose but from the guard file Jamie Dodd sent, whose flags carry
their own values: ``DEAD_STRUCTURE_MAXRUN_233``, ``DEAD_STRUCTURE_MEANRUN_10.49``.
He never explained the mechanism, but the names and the numbers do. He is not
counting dead bins, he is measuring the length of their *runs*. Cross-referenced
against his blind return, `DEAD_STRUCTURE_MAXRUN` fires on:

    genuine  2 %   |   mp3_V0 70 %   aacmf_256 69 %   mp3_320 65 %

which is precisely the three arms where this engine is weakest (78 %, 74 %, 75 %
not-cleared) at a 2 % cost on real recordings.

Why it is a different observable from Rule 13
---------------------------------------------
Rule 13 counts hole *density* at the encoder's frame alignment, and it needs that
alignment because it recovers coefficient values. A run of dead bins is not a
value — it is a band the encoder gave up on entirely, and a band that is empty
stays empty however you analyse it. So this should be **alignment-free**, which
matters: it is the one property that might survive resampling, where both the hole
family and the lattice family were measured dead.

Natural audio has spectral dips too, but they are short and irregular — a notch
from room modes or a gap between partials. An encoder that abandons a scalefactor
band leaves a long, clean, contiguous stretch.

Statistics reported, per file, over the analysis band:

    max_run    longest consecutive stretch of dead bins, median over frames
    mean_run   mean stretch length, median over frames
    dead_frac  plain density, kept only as the control that this adds something

Usage::

    python ml/dead_run_probe.py --control
    python ml/dead_run_probe.py --corpus C:/Users/loutr/audit_corpus --limit 40
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf
from scipy.ndimage import percentile_filter

EXCERPT_SEC = 30.0
FFT_SIZE = 2048
HOP = FFT_SIZE // 2

# Analysis band. Below 2 kHz an encoder never abandons a band; above 16 kHz a
# band-limited file is legitimately empty and every bin would read as dead.
BAND_HZ: Tuple[float, float] = (2000.0, 16000.0)

# A bin is dead this far below its neighbourhood reference. Local rather than
# absolute, so the measure is free of how loud the track is — Rule 13's reasoning.
DEAD_DEPTH_DB = 40.0

# But the reference must be WIDE, and that is the whole point of this file.
#
# Rule 13 uses a 33-bin median. A dead band wider than that window contains the
# window, so the "local median" collapses to the dead level and every bin inside
# reads as alive: the statistic is structurally blind to exactly the artefact
# being looked for here. The control caught it — a 60-bin dead band read 0.0
# while 240 scattered 2-bin notches read 3.0.
#
# So: a wide window, and a high percentile rather than a median, so a dead band
# occupying a third of the window still leaves the reference on live bins. This is
# also why run length is a genuinely different observable rather than density
# repackaged — the two need incompatible references.
REF_BINS = 201
REF_PERCENTILE = 75

MAX_FRAMES = 120


def read_excerpt(path: Path) -> Tuple[np.ndarray, int]:
    """Mono excerpt as float32."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    return np.ascontiguousarray(mono, dtype=np.float32), int(rate)


def _runs(mask: np.ndarray) -> np.ndarray:
    """Lengths of the True runs in a 1-D boolean array."""
    if not mask.any():
        return np.zeros(0, dtype=np.int64)
    padded = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    return edges[1::2] - edges[::2]


def dead_run_stats(x: np.ndarray, sample_rate: int) -> Tuple[float, float, float]:
    """Return ``(max_run, mean_run, dead_fraction)``, each a median over frames."""
    window = np.hanning(FFT_SIZE).astype(np.float32)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / sample_rate)
    band = np.where((freqs >= BAND_HZ[0]) & (freqs <= BAND_HZ[1]))[0]
    if band.size < 64:
        return float("nan"), float("nan"), float("nan")

    frames = []
    for start in range(0, len(x) - FFT_SIZE, HOP):
        block = x[start : start + FFT_SIZE] * window
        if float(np.abs(block).mean()) < 1e-6:
            continue
        frames.append(np.abs(np.fft.rfft(block))[band])
        if len(frames) >= MAX_FRAMES:
            break
    if len(frames) < 16:
        return float("nan"), float("nan"), float("nan")

    spec = np.asarray(frames)
    reference = percentile_filter(
        spec, percentile=REF_PERCENTILE, size=(1, REF_BINS), mode="nearest"
    )
    threshold = 10 ** (-DEAD_DEPTH_DB / 20.0)
    dead = spec < reference * threshold

    max_runs, mean_runs = [], []
    for row in dead:
        lengths = _runs(row)
        max_runs.append(float(lengths.max()) if lengths.size else 0.0)
        mean_runs.append(float(lengths.mean()) if lengths.size else 0.0)

    return (
        float(np.median(max_runs)),
        float(np.median(mean_runs)),
        float(dead.mean()),
    )


# ================================ control ===================================


def _synthetic(
    sample_rate: int, seconds: float, kill_bands: int, width_bins: int, seed: int = 20260818
) -> np.ndarray:
    """Broadband noise with ``kill_bands`` stretches zeroed, ``width_bins`` wide.

    Widths are given in ANALYSIS bins and converted to Hz here. The first version
    zeroed bins of the full-length FFT, whose resolution is ~0.05 Hz against the
    analysis STFT's ~21.5 Hz — so a "60-bin" notch was 3 Hz wide and invisible to
    the very statistic under test. The control failed and the statistic was fine.

    The control has to distinguish two things a density measure conflates: the same
    NUMBER of dead bins as a few long runs, or scattered as many short ones. If it
    cannot, this is Rule 13's density under another name and is not worth adding.
    """
    rng = np.random.default_rng(seed)
    n = int(sample_rate * seconds)
    spectrum = np.fft.rfft(rng.normal(0, 1, n))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    spectrum *= 1.0 / np.maximum(freqs, 20.0) ** 0.5

    bin_hz = sample_rate / FFT_SIZE
    width_hz = width_bins * bin_hz
    if kill_bands and width_bins:
        centres = rng.uniform(3000.0, 15000.0 - width_hz, size=kill_bands)
        for centre in centres:
            spectrum[(freqs >= centre) & (freqs < centre + width_hz)] = 0.0
    out = np.fft.irfft(spectrum, n).astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def run_control(sample_rate: int = 44100) -> int:
    """Does it separate long runs from the same number of scattered dead bins?"""
    print("CONTROL — equal dead COUNT, different arrangement\n")
    print(f"  {'condition':>28} {'max_run':>9} {'mean_run':>10} {'dead_frac':>11}")

    clean = dead_run_stats(_synthetic(sample_rate, 20.0, 0, 0), sample_rate)
    print(f"  {'no dead bands':>28} {clean[0]:>9.1f} {clean[1]:>10.2f} {clean[2]:>11.4f}")

    # ~480 dead bins either way: 8 runs of 60, or 240 runs of 2.
    few_long = dead_run_stats(_synthetic(sample_rate, 20.0, 8, 60), sample_rate)
    many_short = dead_run_stats(_synthetic(sample_rate, 20.0, 240, 2), sample_rate)
    print(
        f"  {'8 runs of 60 bins':>28} {few_long[0]:>9.1f} {few_long[1]:>10.2f} "
        f"{few_long[2]:>11.4f}"
    )
    print(
        f"  {'240 runs of 2 bins':>28} {many_short[0]:>9.1f} {many_short[1]:>10.2f} "
        f"{many_short[2]:>11.4f}"
    )

    finds_runs = few_long[0] > clean[0] * 2
    distinguishes = few_long[0] > many_short[0] * 2

    print("\n  VERDICT:")
    print("   ", "finds long dead bands OK" if finds_runs else "MISSES long dead bands")
    print(
        "   ",
        (
            "distinguishes arrangement from count OK"
            if distinguishes
            else "CANNOT distinguish arrangement — this is density under another name"
        ),
    )
    return 0 if (finds_runs and distinguishes) else 1


# ============================== measurement ==================================


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC with tied ranks averaged."""
    fake, genuine = fake[np.isfinite(fake)], genuine[np.isfinite(genuine)]
    if not fake.size or not genuine.size:
        return float("nan")
    values = np.concatenate([fake, genuine])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(1, values.size + 1)
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    return float(
        (ranks[: fake.size].sum() - fake.size * (fake.size + 1) / 2) / (fake.size * genuine.size)
    )


def run_corpus(corpus: Path, out: Path, limit: int, arms: List[str]) -> int:
    """Measure dead-run structure on every arm."""
    groups: Dict[str, List[Path]] = {
        "genuine": sorted((corpus / "authentic").glob("*.flac"))[:limit]
    }
    for arm in arms:
        directory = corpus / "fake" / arm
        if directory.is_dir():
            groups[arm] = sorted(directory.glob("*.flac"))[:limit]

    rows: List[dict] = []
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["arm", "file", "max_run", "mean_run", "dead_frac"])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    audio, rate = read_excerpt(path)
                    mx, mn, frac = dead_run_stats(audio, rate)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                writer.writerow(
                    {
                        "arm": arm,
                        "file": path.name,
                        "max_run": f"{mx:.2f}",
                        "mean_run": f"{mn:.3f}",
                        "dead_frac": f"{frac:.5f}",
                    }
                )
                rows.append({"arm": arm, "max_run": mx, "mean_run": mn, "dead_frac": frac})
                if index % 10 == 0:
                    print(f"  {arm} [{index}/{len(paths)}]", flush=True)
            fh.flush()
    report(rows)
    return 0


def report(rows: List[dict]) -> None:
    """Per-arm separation for each statistic, at a genuine-derived bar."""
    by_arm: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)
    if "genuine" not in by_arm:
        print("no genuine arm")
        return

    for field in ("max_run", "mean_run", "dead_frac"):
        genuine = np.array([r[field] for r in by_arm["genuine"]], dtype=np.float64)
        genuine = genuine[np.isfinite(genuine)]
        if not genuine.size:
            continue
        bar = float(np.quantile(genuine, 0.90))
        print("\n" + "=" * 62)
        print(f"{field.upper()} — bar = 90th percentile of genuine = {bar:.3f}")
        print("=" * 62)
        print(f"{'arm':14}{'n':>5}{'median':>10}{'AUC':>7}{'fires':>9}")
        for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
            values = np.array([r[field] for r in by_arm[arm]], dtype=np.float64)
            values = values[np.isfinite(values)]
            if not values.size:
                continue
            area = "—" if arm == "genuine" else f"{auc(values, genuine):.2f}"
            print(
                f"{arm:14}{values.size:>5}{np.median(values):>10.3f}{area:>7}"
                f"{100 * (values >= bar).mean():>8.0f}%"
            )

    print(
        "\nIf max_run separates where dead_frac does not, the arrangement carries "
        "information\nthat plain density throws away — which is the whole reason "
        "to add it."
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the control, then the corpus measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/dead_run_probe.csv"))
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument(
        "--arms",
        nargs="+",
        default=["mp3_320", "mp3_V0", "aacmf_256", "opus_256", "aac_ff320", "vorbis_q8"],
    )
    args = parser.parse_args(argv)

    if args.control:
        return run_control()
    status = run_control()
    if status != 0:
        print("\nAborting: the statistic failed its own control.")
        return status
    return run_corpus(args.corpus, args.out, args.limit, args.arms)


if __name__ == "__main__":
    raise SystemExit(main())
