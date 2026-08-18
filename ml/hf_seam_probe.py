#!/usr/bin/env python3
"""A spectral-envelope seam: the observable that survives resampling.

Why
---
Rule 13 reads MDCT frame alignment, which dies whenever anything resamples — that
is why Opus is out of reach for it (CELT works at 48 kHz whatever it is fed) and
why the MP3 geometry probe found a dead end. Both were measured, not assumed.

Provir's blind return pointed at a different observable entirely. Its `HF_SEAM`
flag fires on **100 % of the Opus arm and 97 % of mp3_320, against 8 % of genuine
files** — exactly the two arms where this engine is weakest (49 % and 75 %). And a
spectral *shape* statistic does not care about sample-exact alignment, so it keeps
working where the alignment family cannot.

What a seam is
--------------
Lossy encoders allocate bits per band. Above some frequency a band is either cut
(the cliff Rule 2 already reads) or **kept and quantised far more coarsely**, and
the second case leaves a step in the time-averaged spectral envelope at a fixed
frequency: a discontinuity where natural audio rolls off smoothly.

So the statistic is the largest *normalised step* in the log-magnitude envelope,
measured strictly BELOW the detected cutoff. That restriction is the whole design:
without it this would rediscover the cliff and duplicate Rule 2 rather than add a
family. Normalising by a robust local scale (MAD of the steps) makes it free of
overall spectral tilt, so quiet or dark material does not read as seamed.

Validation, in the order the project now requires
-------------------------------------------------
1. Synthetic control — impose a seam of known depth at a known frequency and check
   it is found there; check a smooth envelope reads near the null.
2. Independence control — the statistic must NOT track the cutoff. A seam reader
   that correlates with cutoff frequency is Rule 2 wearing a different hat, which
   is the exact failure the corroboration work spent a week removing.

Usage::

    python ml/hf_seam_probe.py --control
    python ml/hf_seam_probe.py --corpus C:/Users/loutr/audit_corpus --limit 40
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

EXCERPT_SEC = 30.0
FFT_SIZE = 4096

# Search band. Below 3 kHz the envelope is dominated by musical content rather than
# by allocation decisions; the upper edge is set per file from the cutoff.
SEAM_LO_HZ = 3000.0

# Keep clear of the cliff itself — this must measure steps INSIDE the retained
# band, not the band edge that Rule 2 already owns.
CUTOFF_MARGIN_HZ = 1500.0

# Envelope smoothing, in bins. Wide enough to erase harmonic structure, narrow
# enough to leave a genuine allocation step intact.
SMOOTH_BINS = 9

# A step is measured over this gap, so a seam spread across a few bins by the
# encoder's own smoothing still reads as one step rather than several small ones.
STEP_GAP = 3


def read_excerpt(path: Path) -> Tuple[np.ndarray, int]:
    """Mono excerpt as float32."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    return np.ascontiguousarray(mono, dtype=np.float32), int(rate)


def envelope(x: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """Time-averaged log-magnitude spectrum, and its frequency axis.

    Averaged over frames before the log, and only over frames with energy: a seam
    is a persistent property of the encoder's allocation, not a transient, and
    silent passages would otherwise dominate the mean.
    """
    window = np.hanning(FFT_SIZE).astype(np.float32)
    hop = FFT_SIZE // 2
    frames = []
    for start in range(0, len(x) - FFT_SIZE, hop):
        block = x[start : start + FFT_SIZE] * window
        if float(np.abs(block).mean()) < 1e-6:
            continue
        frames.append(np.abs(np.fft.rfft(block)))
    if not frames:
        return np.empty(0), np.empty(0)
    mean = np.mean(np.asarray(frames), axis=0)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / sample_rate)
    with np.errstate(divide="ignore"):
        return 20 * np.log10(np.maximum(mean, 1e-12)), freqs


def detect_cutoff(env_db: np.ndarray, freqs: np.ndarray) -> float:
    """Highest frequency still within 40 dB of the in-band reference level.

    Local to this probe on purpose: the shipped cutoff detector is tuned for the
    scoring rules, and borrowing it would couple a candidate statistic to the very
    family it has to prove itself independent of.
    """
    band = (freqs >= 1000) & (freqs <= 6000)
    if not band.any():
        return float(freqs[-1])
    reference = float(np.median(env_db[band]))
    alive = np.where(env_db >= reference - 40.0)[0]
    return float(freqs[alive[-1]]) if alive.size else float(freqs[-1])


def seam_stat(x: np.ndarray, sample_rate: int) -> Tuple[float, float, float]:
    """Return ``(seam_score, seam_hz, cutoff_hz)``.

    ``seam_score`` is the largest downward step in the smoothed envelope over a
    ``STEP_GAP`` window, divided by the median absolute step across the search
    band. ~1 means the biggest step is unremarkable against the file's own
    roughness; a real allocation seam stands well clear of it.
    """
    env_db, freqs = envelope(x, sample_rate)
    if env_db.size == 0:
        return float("nan"), float("nan"), float("nan")

    cutoff = detect_cutoff(env_db, freqs)
    hi = cutoff - CUTOFF_MARGIN_HZ
    if hi <= SEAM_LO_HZ + 1000:
        # Too little retained band to look inside; abstaining beats guessing.
        return float("nan"), float("nan"), cutoff

    kernel = np.ones(SMOOTH_BINS) / SMOOTH_BINS
    smooth = np.convolve(env_db, kernel, mode="same")

    band = np.where((freqs >= SEAM_LO_HZ) & (freqs <= hi))[0]
    if band.size < 4 * STEP_GAP:
        return float("nan"), float("nan"), cutoff

    lo_idx, hi_idx = band[0], band[-1] - STEP_GAP
    if hi_idx <= lo_idx:
        return float("nan"), float("nan"), cutoff

    steps = smooth[lo_idx + STEP_GAP : hi_idx + STEP_GAP] - smooth[lo_idx:hi_idx]
    drops = -steps  # a seam is a DROP with rising frequency
    scale = float(np.median(np.abs(steps)))
    if scale < 1e-6:
        return float("nan"), float("nan"), cutoff

    best = int(np.argmax(drops))
    return float(drops[best] / scale), float(freqs[lo_idx + best]), cutoff


# ===================== the real HF_SEAM, per Provir's spec ====================

# Jamie Dodd gave the algorithm after both guesses below failed, and the reason
# they failed is instructive: the seam is not in the LEVEL, it is in the temporal
# VARIABILITY of each bin.
#
#     v[i] = std over time of log1p(magnitude) in bin i
#     drop = (mean(v[i-4:i]) - mean(v[i:i+4])) / mean(v[i-4:i])   for i above 12 kHz
#     score = the largest drop
#
# The physical idea is the good part. Genuine high frequencies are RESTLESS —
# cymbals, sibilants, bow noise, room. A regenerated or noise-filled band is
# stationary: it sits at a level and stays there. The seam is the frequency where
# restlessness stops. A time-averaged envelope integrates exactly that away, which
# is why hypothesis 1 read the null, and the collapse happens across a band rather
# than at a boundary, which is why watching the edge position missed it too.
#
# Bounded 0..1 by construction, which matches the 0.74 / 0.80 values in his return.
#
# THREE WARNINGS, in his words and worth repeating because the number flatters:
#   * It is MEASUREMENT-ONLY in Provir and has been since 2026-07-21 — no penalty,
#     no verdict — retired in the same sweep as their brickwall rule.
#   * It has a named false-positive mode: PRODUCTION. Heavy HF limiting, dense
#     synthetic pads and some mastering chains flatten temporal variance with no
#     codec involved. An early attempt to let it corroborate sent a verified
#     genuine 2006 record to UPSCALE at HF_SEAM_0.81.
#   * So "100 % on Opus" is recall on a MEASUREMENT, not on a detector. It says
#     where to look. It cannot convict, and it is not shipped as a rule here.
SEAM_LO_ANALYSIS_HZ = 10000.0
SEAM_SEARCH_FROM_HZ = 12000.0
SEAM_HALF_WIDTH = 4


def temporal_seam_stat(x: np.ndarray, sample_rate: int) -> Tuple[float, float]:
    """Return ``(seam_score, seam_hz)`` — the largest collapse in temporal variance."""
    window = np.hanning(FFT_SIZE).astype(np.float32)
    hop = FFT_SIZE // 2
    frames = []
    for start in range(0, len(x) - FFT_SIZE, hop):
        block = x[start : start + FFT_SIZE] * window
        if float(np.abs(block).mean()) < 1e-6:
            continue
        frames.append(np.abs(np.fft.rfft(block)))
    if len(frames) < 32:
        return float("nan"), float("nan")

    spec = np.asarray(frames)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / sample_rate)
    top = min(freqs[-1], 22050.0)
    band = np.where((freqs >= SEAM_LO_ANALYSIS_HZ) & (freqs <= top))[0]
    if band.size < 4 * SEAM_HALF_WIDTH + 2:
        return float("nan"), float("nan")

    # Per-bin temporal variability. log1p, not log: it is defined at zero, so a
    # silent bin contributes a real value rather than -inf.
    variability = np.std(np.log1p(spec[:, band]), axis=0)
    band_freqs = freqs[band]

    search = np.where(band_freqs >= SEAM_SEARCH_FROM_HZ)[0]
    search = search[(search >= SEAM_HALF_WIDTH) &
                    (search + SEAM_HALF_WIDTH <= variability.size)]
    if search.size == 0:
        return float("nan"), float("nan")

    best_drop, best_hz = float("-inf"), float("nan")
    for i in search:
        before = float(variability[i - SEAM_HALF_WIDTH : i].mean())
        after = float(variability[i : i + SEAM_HALF_WIDTH].mean())
        if before <= 0:
            continue
        drop = (before - after) / before
        if drop > best_drop:
            best_drop, best_hz = drop, float(band_freqs[i])
    if not np.isfinite(best_drop):
        return float("nan"), float("nan")
    return max(0.0, best_drop), best_hz


# ================================ controls ==================================


def _synthetic(sample_rate: int, seconds: float, seam_hz: Optional[float],
               depth_db: float, seed: int = 20260818) -> np.ndarray:
    """Broadband noise, optionally with a step of ``depth_db`` above ``seam_hz``."""
    rng = np.random.default_rng(seed)
    n = int(sample_rate * seconds)
    spectrum = np.fft.rfft(rng.normal(0, 1, n))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    # Pink-ish tilt so the envelope resembles music rather than white noise.
    spectrum *= 1.0 / np.maximum(freqs, 20.0) ** 0.5
    if seam_hz is not None:
        spectrum[freqs >= seam_hz] *= 10 ** (-depth_db / 20.0)
    out = np.fft.irfft(spectrum, n).astype(np.float32)
    return out / (np.abs(out).max() + 1e-9)


def run_control(sample_rate: int = 44100) -> int:
    """Prove the statistic finds a known seam, and that it is not the cutoff."""
    print("CONTROL 1 — a seam of known depth, at a known frequency\n")
    print(f"  {'imposed':>12} {'score':>8} {'found at':>11}")
    smooth_score, _, _ = seam_stat(_synthetic(sample_rate, 20.0, None, 0.0), sample_rate)
    print(f"  {'none':>12} {smooth_score:>8.2f} {'—':>11}")

    found_ok = True
    for depth in (6.0, 12.0, 24.0):
        audio = _synthetic(sample_rate, 20.0, 9000.0, depth)
        score, where, _ = seam_stat(audio, sample_rate)
        print(f"  {f'{depth:.0f} dB @ 9k':>12} {score:>8.2f} {where:>10.0f}Hz")
        if not (np.isfinite(score) and score > smooth_score * 2 and abs(where - 9000) < 1500):
            found_ok = False

    print("\nCONTROL 2 — independence: the statistic must not track the cutoff\n")
    # Band-limit smooth noise at several cutoffs. A seam reader that fires here is
    # Rule 2 in disguise: the whole point is to read INSIDE the retained band.
    scores = []
    for cutoff in (12000.0, 15000.0, 18000.0, 20000.0):
        audio = _synthetic(sample_rate, 20.0, cutoff, 90.0)
        score, where, detected = seam_stat(audio, sample_rate)
        scores.append(score)
        print(f"  band-limited at {cutoff:>6.0f}Hz -> score {score:>6.2f} "
              f"(cutoff read {detected:>6.0f}Hz)")
    clean = [s for s in scores if np.isfinite(s)]
    independent = all(s < smooth_score * 2 for s in clean)

    print("\n  VERDICT:")
    print("   ", "finds a real seam ✓" if found_ok else "MISSES a known seam ✗")
    print("   ", "ignores the cliff ✓" if independent
          else "FIRES ON THE CLIFF ✗ — this is Rule 2 wearing a different hat")
    return 0 if (found_ok and independent) else 1


# ============================== measurement ==================================


def run_corpus(corpus: Path, out: Path, limit: int, arms: List[str]) -> int:
    """Measure the seam statistic on every arm."""
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
        writer = csv.DictWriter(fh, fieldnames=[
            "arm", "file", "seam", "seam_hz", "cutoff_hz", "tseam", "tseam_hz"
        ])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    audio, rate = read_excerpt(path)
                    score, where, cutoff = seam_stat(audio, rate)
                    tscore, twhere = temporal_seam_stat(audio, rate)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                row = {"arm": arm, "file": path.name, "seam": f"{score:.4f}",
                       "seam_hz": f"{where:.0f}", "cutoff_hz": f"{cutoff:.0f}",
                       "tseam": f"{tscore:.4f}", "tseam_hz": f"{twhere:.0f}"}
                writer.writerow(row)
                rows.append({**row, "seam": score, "cutoff_hz": cutoff,
                             "tseam": tscore})
                if index % 10 == 0:
                    print(f"  {arm} [{index}/{len(paths)}]", flush=True)
            fh.flush()
    report(rows)
    return 0


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


def report(rows: List[dict]) -> None:
    """Per-arm separation, and the independence check that matters."""
    by_arm: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)

    genuine = np.array([r["seam"] for r in by_arm["genuine"]], dtype=np.float64)
    genuine = genuine[np.isfinite(genuine)]
    if not genuine.size:
        print("no usable genuine rows")
        return

    # Threshold from the genuine arm alone, never from the fakes: the bar is a
    # false-alarm budget, not a recall target.
    bar = float(np.quantile(genuine, 0.90))

    print("\n" + "=" * 70)
    print("HF SEAM — median score, AUC vs genuine, and fire rate at the 90th")
    print(f"percentile of genuine (bar = {bar:.2f})")
    print("=" * 70)
    print(f"{'arm':14}{'n':>5}{'median':>9}{'AUC':>7}{'fires':>9}")
    for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
        values = np.array([r["seam"] for r in by_arm[arm]], dtype=np.float64)
        values = values[np.isfinite(values)]
        if not values.size:
            continue
        fires = float((values >= bar).mean())
        area = "—" if arm == "genuine" else f"{auc(values, genuine):.2f}"
        print(f"{arm:14}{values.size:>5}{np.median(values):>9.2f}{area:>7}{100 * fires:>8.0f}%")

    # Independence: a seam reader correlating with cutoff is Rule 2 in disguise.
    all_rows = [r for rs in by_arm.values() for r in rs
                if np.isfinite(r["seam"]) and np.isfinite(r["cutoff_hz"])]
    if len(all_rows) > 10:
        seam = np.array([r["seam"] for r in all_rows])
        cutoff = np.array([r["cutoff_hz"] for r in all_rows])
        corr = float(np.corrcoef(seam, cutoff)[0, 1])
        print(f"\nindependence — corr(seam, cutoff) = {corr:+.2f}  "
              f"({'OK' if abs(corr) < 0.4 else 'TOO HIGH: this may be Rule 2 again'})")

    # And the one that matters: Provir's own algorithm, temporal rather than level.
    tgen = np.array([r["tseam"] for r in by_arm["genuine"]], dtype=np.float64)
    tgen = tgen[np.isfinite(tgen)]
    if tgen.size:
        tbar = float(np.quantile(tgen, 0.90))
        print("\n" + "=" * 70)
        print("HF_SEAM (temporal variance, Provir's spec) — bar = genuine p90 "
              f"= {tbar:.3f}")
        print("=" * 70)
        print(f"{'arm':14}{'n':>5}{'median':>9}{'AUC':>7}{'fires':>9}")
        for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
            values = np.array([r["tseam"] for r in by_arm[arm]], dtype=np.float64)
            values = values[np.isfinite(values)]
            if not values.size:
                continue
            area = "-" if arm == "genuine" else f"{auc(values, tgen):.2f}"
            print(f"{arm:14}{values.size:>5}{np.median(values):>9.3f}{area:>7}"
                  f"{100 * (values >= tbar).mean():>8.0f}%")
        print("\nMeasurement only, never a rule. Its named false-positive mode is "
              "production:\nheavy HF limiting and dense synthetic pads flatten "
              "temporal variance with no codec.")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the controls, then the corpus measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/hf_seam_probe.csv"))
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--arms", nargs="+", default=[
        "opus_256", "mp3_320", "mp3_V0", "aacmf_256", "aac_ff320", "vorbis_q8"])
    args = parser.parse_args(argv)

    if args.control:
        return run_control()
    status = run_control()
    if status != 0:
        print("\nAborting: the statistic failed its own controls.")
        return status
    return run_corpus(args.corpus, args.out, args.limit, args.arms)


if __name__ == "__main__":
    raise SystemExit(main())
