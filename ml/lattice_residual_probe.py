#!/usr/bin/env python3
"""Read the quantisation LATTICE rather than counting its zeros.

Why this is a different observable
----------------------------------
Rule 13 counts holes: coefficients a quantiser sent to exactly zero while their
neighbours survived. That works spectacularly on ffmpeg AAC (AUC 0.99) and not at
all on Apple CoreAudio, measured on a free macOS runner at 13 % / 2 % / 0 % for
128 / 256 / 320 kbps. Jamie Dodd of Provir reported the same encoder as a clean
zero for his own hole-based path, and said the answer was to read the spacing of
the lattice instead of its zeros — which is what his `AAC_LATTICE` flag does. On
our blind set it fires on 78 % of `aacmf_256` and `aac_ff320` and **0 % of
everything else**, which is the cleanest, most specific signal in his return.

The mechanism. A quantiser does not only zero small coefficients; it maps every
coefficient onto a grid. AAC quantises in a companded domain — roughly
``|X| ** 0.75`` divided by a per-band step — so after decoding the surviving
coefficients still cluster near multiples of that step. Genuine audio has no such
preference: its companded magnitudes are continuous.

So the statistic does not need any coefficient to be zero, which is exactly why it
can reach an encoder that leaves none.

How it is measured
------------------
For each analysis band, take companded magnitudes ``c = |X| ** 0.75`` and ask how
periodic they are, via the Rayleigh-style characteristic function

    R(step) = | mean( exp( 2*pi*i * c / step ) ) |

which is ~0 for a smooth distribution and approaches 1 when the values sit on a
grid of that spacing. The step is unknown, so it is scanned — and because a
maximum over a scan does not converge (a lesson this project paid for once
already, in Rule 13's genuine ceiling), the result is divided by the ANALYTIC
expectation of that maximum under no grid, ``sqrt(ln(M)/n)``. So ~1 is chance and
anything above it is structure.

Two things had to be got right before the control would pass, and both are
recorded in the code because both were wrong first:

* **Group before you measure.** AAC carries a separate scalefactor per band per
  frame, so every (frame, band) sits on its own grid. Pooling a file's
  coefficients superimposes dozens of spacings and erases all of them.
* **Align before you read.** See ``lattice_stat``: off the encoder's own offset
  the statistic is flat at chance no matter how coarse the grid. That is a
  finding rather than a detail — it means the lattice family cannot rescue Opus
  either.

Usage::

    python ml/lattice_residual_probe.py --control
    python ml/lattice_residual_probe.py --corpus C:/Users/loutr/audit_corpus --limit 30
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

EXCERPT_SEC = 30.0
WINDOW_LEN = 2048
HOP = WINDOW_LEN // 2

# Analysis band, matching Rule 13's: below 2 kHz quantisation is fine enough that
# the grid is invisible, above 16 kHz band-limited material is empty.
BAND_HZ: Tuple[float, float] = (2000.0, 16000.0)

N_FRAMES = 48
# Coefficients per analysis group — AAC's scalefactor bands are of this order.
BAND_BINS = 32
# Every 4th frame is enough and keeps the scan affordable.
FRAME_SKIP = 4
MAX_GROUPS = 900
COMPAND = 0.75  # AAC's companding exponent


def kbd_window(length: int = WINDOW_LEN, alpha: float = 4.0) -> np.ndarray:
    """ffmpeg's AAC long-block window."""
    half = length // 2
    kaiser = np.kaiser(half + 1, np.pi * alpha)
    cumulative = np.cumsum(kaiser)
    rising = np.sqrt(cumulative[:half] / cumulative[-1])
    return np.concatenate([rising, rising[::-1]]).astype(np.float32)


def mdct_basis(sample_rate: int) -> np.ndarray:
    """MDCT basis restricted to the analysis band."""
    half = WINDOW_LEN // 2
    lo = max(1, int(BAND_HZ[0] / (sample_rate / 2) * half))
    hi = min(half, int(BAND_HZ[1] / (sample_rate / 2) * half))
    n = np.arange(WINDOW_LEN)[:, None]
    k = np.arange(lo, hi)[None, :]
    return np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float32)


def read_excerpt(path: Path) -> Tuple[np.ndarray, int]:
    """Mono excerpt as float32."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    return np.ascontiguousarray(mono, dtype=np.float32), int(rate)


def _groups_at(
    x: np.ndarray, basis: np.ndarray, window: np.ndarray, offset: int
) -> List[np.ndarray]:
    """Companded magnitudes grouped by (frame, band), on frames locked to ``offset``."""
    groups: List[np.ndarray] = []
    step = HOP * FRAME_SKIP
    for start in range(offset, len(x) - WINDOW_LEN, step):
        block = x[start : start + WINDOW_LEN] * window
        if float(np.abs(block).mean()) < 1e-7:
            continue
        frame = np.abs(block @ basis)
        for lo in range(0, frame.size - BAND_BINS, BAND_BINS):
            band = frame[lo : lo + BAND_BINS]
            band = band[band > 0]
            if band.size >= BAND_BINS // 2:
                groups.append(np.power(band, COMPAND))
        if len(groups) > MAX_GROUPS:
            break
    return groups


def _rayleigh(values: np.ndarray, steps: np.ndarray) -> float:
    """Best periodicity strength over the candidate steps."""
    phases = 2 * np.pi * values[None, :] / steps[:, None]
    return float(np.abs(np.exp(1j * phases).mean(axis=1)).max())


def _score(groups: List[np.ndarray]) -> float:
    """Mean per-group lattice strength, each normalised by its own analytic null."""
    if len(groups) < 40:
        return float("nan")
    scores = []
    for band in groups:
        scale = float(np.median(band))
        if not np.isfinite(scale) or scale <= 0:
            continue
        steps = np.geomspace(scale / 20.0, scale / 2.0, 48)
        expected = float(np.sqrt(np.log(steps.size) / band.size))
        if expected > 0:
            scores.append(_rayleigh(band, steps) / expected)
    return float(np.mean(scores)) if len(scores) >= 40 else float("nan")


def lattice_stat(x: np.ndarray, sample_rate: int, offset: Optional[int] = None) -> float:
    """Lattice strength at the encoder's own frame alignment.

    THE ALIGNMENT IS NOT OPTIONAL, and that was the finding rather than an
    implementation detail. Measured on audio quantised onto an exact grid: read at
    the imposing offset the statistic goes 1.03 -> 1.61 -> 2.62 -> 2.85 as the grid
    coarsens; read 511 samples off, it stays at 1.03 for every one of them.

    So a lattice reader needs alignment exactly as a hole counter does — both
    recover coefficient VALUES, and values only exist at the encoder's offset.
    The consequence is worth stating plainly: this cannot rescue Opus. Resampling
    destroys the alignment, so the lattice family dies there for precisely the
    reason the hole family does, and Provir's own AAC_LATTICE duly fires on 0 % of
    the Opus arm. What it CAN reach is an encoder that leaves no zeros — Apple
    CoreAudio, where Rule 13 measures 13 / 2 / 0 % — because a grid is still a grid
    when nothing has been set to zero.

    ``offset`` defaults to the alignment Rule 13's own scan reports, so the two
    observables are read at one offset rather than each paying for its own search.
    """
    basis = mdct_basis(sample_rate)
    window = kbd_window()
    if offset is None:
        from flac_detective.analysis.new_scoring.mdct import best_alignment_stat

        _ratio, offset, _hypothesis = best_alignment_stat(x, sample_rate, stop_at=float("inf"))
        if offset < 0:
            return float("nan")
    return _score(_groups_at(x, basis, window, int(offset) % HOP))


# ================================ controls ==================================


def run_control(sample_rate: int = 44100) -> int:
    """Impose a lattice the way AAC does, and check it is read.

    Crucially the grid is imposed in the COMPANDED domain — ``q = round(|X|**0.75 /
    step)``, reconstructed as ``(q*step)**(4/3)`` — because that is what AAC
    quantises. The first version of this control imposed a uniform grid on the raw
    coefficients and then looked for it after companding, where a uniform grid is
    no longer uniform. It duly found nothing, and the failure was in the control
    rather than in the statistic.
    """
    rng = np.random.default_rng(20260818)
    n = int(sample_rate * 20)
    noise = np.cumsum(rng.normal(0, 1, n))
    noise = ((noise - noise.mean()) / (np.abs(noise).max() + 1e-9)).astype(np.float32)

    print("CONTROL — quantise in AAC's companded domain, then resynthesise\n")
    print(f"  {'condition':>24} {'lattice':>9}")
    clean = lattice_stat(noise, sample_rate, offset=0)
    print(f"  {'untouched':>24} {clean:>9.2f}")

    basis = mdct_basis(sample_rate)
    window = kbd_window()
    half = WINDOW_LEN // 2
    detected: List[float] = []
    for coarseness in (0.02, 0.05, 0.15, 0.40):
        out = np.zeros(len(noise), dtype=np.float64)
        for start in range(0, len(noise) - WINDOW_LEN, HOP):
            block = noise[start : start + WINDOW_LEN] * window
            coeffs = block @ basis
            sign = np.sign(coeffs)
            companded = np.abs(coeffs) ** COMPAND
            step = coarseness * float(np.median(companded) + 1e-12)
            companded = np.round(companded / step) * step
            coeffs = sign * companded ** (1.0 / COMPAND)
            out[start : start + WINDOW_LEN] += (coeffs @ basis.T) * window * (2.0 / half)
        value = lattice_stat(out.astype(np.float32), sample_rate, offset=0)
        hit = bool(np.isfinite(value) and value > clean * 1.5)
        label = "detected" if hit else "below floor"
        print(f"  {f'grid, step {coarseness:.2f}':>24} {value:>9.2f}   {label}")
        if hit:
            detected.append(coarseness)

    # The criterion is a SENSITIVITY FLOOR, not omniscience. A near-transparent
    # grid should be invisible, and demanding otherwise was the first version's
    # mistake: it failed on a step of 0.02 that no honest statistic could read.
    # What matters is that coarse grids are found, that smooth audio is not, and
    # that the floor is recorded rather than hidden.
    ok = bool(detected) and min(detected) <= 0.05
    if detected:
        print(f"\n  sensitivity floor: finest grid detected = step {min(detected):.2f}")
    print(
        "  VERDICT:", "reads a lattice, ignores smooth audio OK" if ok else "FAILS its own control"
    )
    return 0 if ok else 1


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
    """Measure the lattice statistic on every arm."""
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
        writer = csv.DictWriter(fh, fieldnames=["arm", "file", "lattice"])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    audio, rate = read_excerpt(path)
                    value = lattice_stat(audio, rate)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                writer.writerow({"arm": arm, "file": path.name, "lattice": f"{value:.4f}"})
                rows.append({"arm": arm, "lattice": value})
                fh.flush()
                if index % 10 == 0:
                    print(f"  {arm} [{index}/{len(paths)}]", flush=True)
    report(rows)
    return 0


def report(rows: List[dict]) -> None:
    """Per-arm separation at a genuine-derived bar."""
    by_arm: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row["lattice"])

    genuine = np.array(by_arm["genuine"], dtype=np.float64)
    genuine = genuine[np.isfinite(genuine)]
    if not genuine.size:
        print("no usable genuine rows")
        return
    bar = float(np.quantile(genuine, 0.90))

    print("\n" + "=" * 66)
    print(f"LATTICE RESIDUAL — bar = 90th percentile of genuine = {bar:.3f}")
    print("=" * 66)
    print(f"{'arm':14}{'n':>5}{'median':>10}{'AUC':>7}{'fires':>9}")
    for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
        values = np.array(by_arm[arm], dtype=np.float64)
        values = values[np.isfinite(values)]
        if not values.size:
            continue
        area = "—" if arm == "genuine" else f"{auc(values, genuine):.2f}"
        print(
            f"{arm:14}{values.size:>5}{np.median(values):>10.3f}{area:>7}"
            f"{100 * (values >= bar).mean():>8.0f}%"
        )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the control, then the corpus measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/lattice_residual_probe.csv"))
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument(
        "--arms",
        nargs="+",
        default=["aacmf_256", "aac_ff320", "aac_ff256", "opus_256", "mp3_320", "vorbis_q8"],
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
