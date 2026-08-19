#!/usr/bin/env python3
"""Dead runs in the SIDE channel — the stereo-image family.

Where this came from, and why the first attempt found nothing
--------------------------------------------------------------
`ml/dead_run_probe.py` looked for long runs of dead bins and measured a clean null
in two domains. Jamie Dodd of Provir then gave the mechanism, and the reason for
the null was that the whole search was in the wrong channel:

    mid  = STFT(|L+R| / 2), bins from 10 kHz up
    side = STFT(|L-R|),     bins from 10 kHz up
    max_run  : per FRAME, the longest run of consecutive bins in SIDE below 1e-3
    mean_run : same, over the union mask (mid < 3e-4) OR (side < 3e-4)
    INTERIOR ONLY — a run touching the top bin is discarded

The mechanism is **joint/intensity stereo**. Above the coupling frequency the
encoder quantises the side channel toward zero and leaves long contiguous holes
there, while the mid stays perfectly alive. So it is a stereo-image statistic under
a spectral-looking name, and a mono-sum search — which is what the first probe did,
and what every other family in this engine does — cannot see it by construction.

That also settles the remaining hypothesis without spending a day on it: his corpus
is not reaching lower in bitrate than ours. The bands are not dying in the mid at
any bitrate. They die in a channel we were not forming.

``interior`` is the same exclusion this project made deliberately elsewhere: a run
reaching Nyquist is a lowpass edge, and that belongs to the cutoff rule.

The two failure modes, both his, both measured before use
----------------------------------------------------------
**Mono material manufactures the statistic out of nothing.** No stereo image means
no side channel means every HF bin is trivially below any threshold. On his own
mono CDs: L-R correlation 1.000000, side/mid energy 3e-8, and a dead-run of 151-182
against a solo conviction floor of 170 — a few units from convicting a legitimate
master for the absence of a stereo image. The gate is not optional. His threshold,
from n=360: side/mid energy < 1e-5, where mono maxes at 2.9e-8 and real stereo
bottoms at 2.1e-4. A 7000x gap, so the placement is not delicate; its existence is.

**The thresholds are absolute, so the statistic is level-dependent.** He measured
identical audio at 0 / -12 / -24 / -36 dB reading 16 / 54 / 137 / 283, with six
files out of six changing verdict on gain alone. Plain peak normalisation re-scores
everything the constants were fitted on and cost him 68.9 % -> 59.4 % for no
false-positive benefit; what works is a floor-guarded restore, rescaling only files
below 0.75 of full scale.

Both his absolute form and a scale-free variant are measured here, because his
thresholds were fitted against his own STFT normalisation and there is no reason
ours matches. Reusing a constant across instruments is the fold-over mistake this
project has already made once.

Usage::

    python ml/side_dead_run_probe.py --control
    python ml/side_dead_run_probe.py --corpus C:/Users/loutr/audit_corpus --limit 40
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
FFT_SIZE = 2048
HOP = FFT_SIZE // 2

BAND_LO_HZ = 10000.0

# Provir's absolute thresholds, on his STFT normalisation.
SIDE_DEAD = 1e-3
UNION_DEAD = 3e-4

# Mono gate: below this ratio of side to mid energy there is no stereo image, so
# the statistic would be measuring its own absence.
MONO_GATE = 1e-5

# Floor-guarded restore: only quiet files are rescaled, so the constants keep
# meaning what they meant when they were fitted.
RESTORE_BELOW_PEAK = 0.75

MAX_FRAMES = 200


def read_stereo(path: Path) -> Tuple[np.ndarray, int]:
    """Stereo excerpt as float32 (frames, 2), or a (frames, 1) array if mono."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    if data.ndim == 1:
        data = data[:, None]
    return np.ascontiguousarray(data, dtype=np.float32), int(rate)


def mid_side(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(mid, side)``; a mono file has an identically zero side."""
    if data.shape[1] < 2:
        return data[:, 0], np.zeros(len(data), dtype=np.float32)
    left, right = data[:, 0], data[:, 1]
    return (left + right) / 2.0, left - right


def stereo_ratio(mid: np.ndarray, side: np.ndarray) -> float:
    """Full-band side/mid energy — the mono gate's input."""
    mid_energy = float(np.mean(mid.astype(np.float64) ** 2))
    if mid_energy <= 0:
        return 0.0
    return float(np.mean(side.astype(np.float64) ** 2) / mid_energy)


def _restore(signal: np.ndarray) -> np.ndarray:
    """Floor-guarded gain restore, so absolute thresholds keep their meaning."""
    peak = float(np.abs(signal).max())
    if 0 < peak < RESTORE_BELOW_PEAK:
        return (signal / peak).astype(np.float32)
    return signal


def _spectra(signal: np.ndarray, rate: int) -> Tuple[np.ndarray, np.ndarray]:
    """|STFT| above the band floor, and the frequency axis for those bins."""
    window = np.hanning(FFT_SIZE).astype(np.float32)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / rate)
    band = np.where(freqs >= BAND_LO_HZ)[0]
    frames = []
    for start in range(0, len(signal) - FFT_SIZE, HOP):
        block = signal[start : start + FFT_SIZE] * window
        frames.append(np.abs(np.fft.rfft(block))[band])
        if len(frames) >= MAX_FRAMES:
            break
    if not frames:
        return np.empty((0, 0)), freqs[band]
    return np.asarray(frames), freqs[band]


def _interior_runs(mask: np.ndarray) -> np.ndarray:
    """True-run lengths, discarding any run that touches the top bin.

    A run reaching Nyquist is a lowpass edge and belongs to the cutoff rule. This
    project excluded exactly that elsewhere for the same reason; Provir excludes it
    for the same reason too.
    """
    if not mask.any():
        return np.zeros(0, dtype=np.int64)
    padded = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[::2], edges[1::2]
    keep = ends < mask.size  # a run ending at the last bin touches the top
    return (ends - starts)[keep]


def side_dead_runs(path: Path) -> dict:
    """Provir's statistic, plus a scale-free variant and the gate's inputs."""
    data, rate = read_stereo(path)
    mid_raw, side_raw = mid_side(data)
    ratio = stereo_ratio(mid_raw, side_raw)

    out: dict = {"stereo_ratio": ratio, "mono_gated": ratio < MONO_GATE,
                 "max_run": float("nan"), "mean_run": float("nan"),
                 "max_run_rel": float("nan")}
    if out["mono_gated"]:
        # No stereo image: the statistic would be measuring its own absence.
        return out

    mid = _restore(mid_raw)
    side = _restore(side_raw)
    side_spec, _freqs = _spectra(side, rate)
    mid_spec, _ = _spectra(mid, rate)
    if side_spec.size == 0 or side_spec.shape != mid_spec.shape:
        return out

    max_runs, mean_runs, rel_runs = [], [], []
    # Scale-free companion: dead relative to the file's own median side level,
    # so a quiet master reads the same as a loud one.
    relative_floor = float(np.median(side_spec)) * 1e-2
    for side_frame, mid_frame in zip(side_spec, mid_spec):
        runs = _interior_runs(side_frame < SIDE_DEAD)
        max_runs.append(float(runs.max()) if runs.size else 0.0)
        union = _interior_runs((mid_frame < UNION_DEAD) | (side_frame < UNION_DEAD))
        mean_runs.append(float(union.mean()) if union.size else 0.0)
        rel = _interior_runs(side_frame < relative_floor)
        rel_runs.append(float(rel.max()) if rel.size else 0.0)

    out["max_run"] = float(np.median(max_runs))
    out["mean_run"] = float(np.median(mean_runs))
    out["max_run_rel"] = float(np.median(rel_runs))
    return out


# ================================ controls ===================================


def _stereo_noise(rate: int, seconds: float, seed: int = 11) -> np.ndarray:
    """Independent left and right: a real stereo image, side channel alive."""
    rng = np.random.default_rng(seed)
    n = int(rate * seconds)
    return np.stack([rng.normal(0, 0.2, n), rng.normal(0, 0.2, n)], axis=1).astype(np.float32)


def _kill_side_band(data: np.ndarray, rate: int, lo_hz: float, hi_hz: float) -> np.ndarray:
    """Zero the side channel between ``lo_hz`` and ``hi_hz`` — joint stereo.

    BOUNDED, and that is not cosmetic. Killing the side all the way to Nyquist
    produces a run that touches the top bin, which the interior rule discards as a
    lowpass edge — correctly, and the first version of this control did exactly
    that and read 1.0. Real transcodes leave dither and noise at the very top, so
    their runs are interior; a synthetic control has to reproduce that or it tests
    the exclusion rather than the statistic.
    """
    mid = (data[:, 0] + data[:, 1]) / 2.0
    side = data[:, 0] - data[:, 1]
    spectrum = np.fft.rfft(side)
    freqs = np.fft.rfftfreq(len(side), 1.0 / rate)
    spectrum[(freqs >= lo_hz) & (freqs < hi_hz)] = 0.0
    side = np.fft.irfft(spectrum, len(side))
    return np.stack([mid + side / 2.0, mid - side / 2.0], axis=1).astype(np.float32)


def run_control(rate: int = 44100) -> int:
    """Three things: it finds a killed side band, ignores live stereo, gates mono."""
    import tempfile

    print("CONTROL — side-channel dead runs\n")
    print(f"  {'condition':>30} {'max_run':>9} {'side/mid':>11} {'gated':>7}")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        def measure(data: np.ndarray, name: str) -> dict:
            path = work / f"{name}.flac"
            sf.write(str(path), data, rate)
            return side_dead_runs(path)

        live = measure(_stereo_noise(rate, 12.0), "live")
        print(f"  {'live stereo, nothing killed':>30} {live['max_run']:>9.1f} "
              f"{live['stereo_ratio']:>11.2e} {str(live['mono_gated']):>7}")

        killed = measure(
            _kill_side_band(_stereo_noise(rate, 12.0), rate, 12000.0, 18000.0), "killed")
        print(f"  {'side killed 12-18 kHz':>30} {killed['max_run']:>9.1f} "
              f"{killed['stereo_ratio']:>11.2e} {str(killed['mono_gated']):>7}")

        mono_data = _stereo_noise(rate, 12.0)
        mono_data[:, 1] = mono_data[:, 0]
        mono = measure(mono_data, "mono")
        print(f"  {'MONO (identical channels)':>30} {mono['max_run']:>9.1f} "
              f"{mono['stereo_ratio']:>11.2e} {str(mono['mono_gated']):>7}")

    finds = np.isfinite(killed["max_run"]) and killed["max_run"] > max(live["max_run"], 1.0) * 2
    gates = bool(mono["mono_gated"])

    print("\n  VERDICT:")
    print("   ", "finds a killed side band OK" if finds else "MISSES the killed side band")
    print("   ", "gates mono OK" if gates
          else "DOES NOT GATE MONO — this convicts masters for having no stereo image")
    return 0 if (finds and gates) else 1


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
    """Measure every arm."""
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
            "arm", "file", "max_run", "mean_run", "max_run_rel", "stereo_ratio", "mono_gated"])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    stats = side_dead_runs(path)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                writer.writerow({"arm": arm, "file": path.name, **{
                    k: (f"{v:.4f}" if isinstance(v, float) else v)
                    for k, v in stats.items()}})
                rows.append({"arm": arm, **stats})
                if index % 10 == 0:
                    print(f"  {arm} [{index}/{len(paths)}]", flush=True)
            fh.flush()
    report(rows)
    return 0


def report(rows: List[dict]) -> None:
    """Per-arm separation for each variant, at a genuine-derived bar."""
    by_arm: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)
    if "genuine" not in by_arm:
        print("no genuine arm")
        return

    gated = sum(1 for r in by_arm["genuine"] if r["mono_gated"])
    print(f"\nmono-gated genuine files: {gated}/{len(by_arm['genuine'])}")

    for field in ("max_run", "mean_run", "max_run_rel"):
        genuine = np.array([r[field] for r in by_arm["genuine"]], dtype=np.float64)
        genuine = genuine[np.isfinite(genuine)]
        if not genuine.size:
            continue
        bar = float(np.quantile(genuine, 0.90))
        print("\n" + "=" * 62)
        print(f"{field.upper()} — bar = 90th percentile of genuine = {bar:.2f}")
        print("=" * 62)
        print(f"{'arm':14}{'n':>5}{'median':>10}{'AUC':>7}{'fires':>9}")
        for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
            values = np.array([r[field] for r in by_arm[arm]], dtype=np.float64)
            values = values[np.isfinite(values)]
            if not values.size:
                continue
            area = "-" if arm == "genuine" else f"{auc(values, genuine):.2f}"
            print(f"{arm:14}{values.size:>5}{np.median(values):>10.2f}{area:>7}"
                  f"{100 * (values >= bar).mean():>8.0f}%")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the controls, then the corpus measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/side_dead_run_probe.csv"))
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--arms", nargs="+", default=[
        "mp3_320", "mp3_V0", "aacmf_256", "opus_256", "aac_ff320", "vorbis_q8"])
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
