#!/usr/bin/env python3
"""Distance to the codec's fixed point — the one family that discovers nothing.

The idea
--------
Encode the file, decode it, and measure how far it moved: ``d1``. Do it again from
the result and measure ``d2``. A lossless source is far from the codec's fixed
point, so the first pass does real damage and the second much less. Content that
has already been through the codec is already AT the fixed point, so both passes
move it about equally.

    R = 20 * log10(d1 / d2)     fires below THETA

Provir measures their miss-class fakes at 0.18-1.46 dB and their genuine sources at
3.00-3.76 dB.

Why this is a family and not a variant
---------------------------------------
Every other observable this project holds has to *discover* something the encoder
did: where the cliff is, which frame offset it used, what quantiser step, when the
top band stopped moving, which channel it collapsed. Rule 13 and the lattice both
died on Opus for exactly that reason — resampling destroys the alignment they must
recover first.

This discovers nothing. You re-encode from PCM and the encoder picks its own grid
every time, so there is no alignment to lose. That is why it should reach arms where
both alignment-dependent families are dead, and why Jamie Dodd's reading of 67 % on
the Opus arm at 0 % on genuine is worth chasing.

THE DETAIL THAT OTHERWISE MAKES IT LOOK LIKE A DEAD IDEA
---------------------------------------------------------
Every encode must go to a **seekable temp file, never a pipe.** Without the
finalised Xing/LAME info frame the decoder loses the encoder delay, the second pass
lands on a different MDCT grid, and R collapses from 2.56 dB to 0.04 dB. His words:
the tell does not weaken, it vanishes — silently, and it looks exactly like an idea
that was never there.

Everything here therefore writes real files, and ``--pipe`` exists only to
reproduce the failure on demand, because a trap you can demonstrate is one you will
not fall into twice.

Usage::

    python ml/idempotence_probe.py --control
    python ml/idempotence_probe.py --corpus C:/Users/loutr/audit_corpus --limit 12
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

EXCERPT_SEC = 60.0
FFT_SIZE = 2048
HOP = FFT_SIZE // 2

# Provir's band and threshold. THETA was frozen on their exact computation, so it
# travels with the recipe or not at all — a different STFT is a different
# instrument wearing someone else's number.
BAND_HZ: Tuple[float, float] = (300.0, 16000.0)
THETA = 2.0

MAX_LAG = 16384
MIN_SURVIVING_BINS = 200


def _run(cmd: List[str]) -> bool:
    """Run ffmpeg quietly; False on failure rather than an exception."""
    return subprocess.run(cmd, capture_output=True).returncode == 0


def encode_decode(pcm: np.ndarray, rate: int, work: Path, tag: str,
                  bitrate: str, use_pipe: bool = False) -> Optional[np.ndarray]:
    """One LAME round trip. ``use_pipe`` reproduces the failure deliberately."""
    source = work / f"{tag}_in.wav"
    encoded = work / f"{tag}.mp3"
    decoded = work / f"{tag}_out.wav"
    sf.write(str(source), pcm, rate, subtype="PCM_16")

    if use_pipe:
        # The trap, on purpose: no finalised Xing/LAME header, so the decoder
        # cannot recover the encoder delay.
        with open(encoded, "wb") as fh:
            proc = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
                 "-c:a", "libmp3lame", "-b:a", bitrate, "-f", "mp3", "-"],
                stdout=fh, stderr=subprocess.DEVNULL)
        if proc.returncode != 0:
            return None
    else:
        if not _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                     "-i", str(source), "-c:a", "libmp3lame", "-b:a", bitrate,
                     str(encoded)]):
            return None

    if not _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(encoded), "-c:a", "pcm_s16le", str(decoded)]):
        return None
    data, _rate = sf.read(str(decoded), dtype="float32")
    return data


def _align(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Trim both to a common length after cross-correlation alignment."""
    x = a if a.ndim == 1 else a.mean(axis=1)
    y = b if b.ndim == 1 else b.mean(axis=1)
    n = min(len(x), len(y), 20 * 44100)
    x, y = x[:n], y[:n]
    probe = min(n, 8 * 44100)
    correlation = np.correlate(y[:probe], x[:probe], mode="full")
    lag = int(np.argmax(correlation)) - (probe - 1)
    lag = max(-MAX_LAG, min(MAX_LAG, lag))
    if lag > 0:
        y = y[lag:]
    elif lag < 0:
        x = x[-lag:]
    n = min(len(x), len(y))
    return x[:n], y[:n]


def distance(a: np.ndarray, b: np.ndarray, rate: int) -> float:
    """Mean absolute dB difference of |STFT| over the analysis band."""
    x, y = _align(a, b)
    if len(x) < FFT_SIZE * 4:
        return float("nan")
    window = np.hanning(FFT_SIZE).astype(np.float32)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / rate)
    band = np.where((freqs >= BAND_HZ[0]) & (freqs <= BAND_HZ[1]))[0]

    diffs = []
    for start in range(0, len(x) - FFT_SIZE, HOP * 4):
        fx = np.abs(np.fft.rfft(x[start : start + FFT_SIZE] * window))[band]
        fy = np.abs(np.fft.rfft(y[start : start + FFT_SIZE] * window))[band]
        alive = (fx > 1e-6) & (fy > 1e-6)
        if alive.sum() < MIN_SURVIVING_BINS:
            continue
        diffs.append(np.abs(20 * np.log10(fx[alive] / fy[alive])).mean())
    return float(np.mean(diffs)) if diffs else float("nan")


def idempotence(path: Path, bitrate: str = "192k", use_pipe: bool = False) -> float:
    """``R = 20*log10(d1/d2)`` in dB; NaN when it cannot be measured."""
    info = sf.info(str(path))
    pcm, rate = sf.read(str(path), dtype="float32",
                        frames=int(EXCERPT_SEC * info.samplerate))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        first = encode_decode(pcm, rate, work, "p1", bitrate, use_pipe)
        if first is None:
            return float("nan")
        second = encode_decode(first, rate, work, "p2", bitrate, use_pipe)
        if second is None:
            return float("nan")
        d1 = distance(pcm, first, rate)
        d2 = distance(first, second, rate)
    if not (np.isfinite(d1) and np.isfinite(d2)) or d2 <= 0:
        return float("nan")
    return float(20 * np.log10(d1 / d2))


# ================================ controls ===================================


def run_control(corpus: Path) -> int:
    """A genuine source must sit far from the fixed point; a transcode at it.

    And the pipe trap is demonstrated rather than described, because the whole
    reason it is worth documenting is that its failure looks like absence.
    """
    genuine = sorted((corpus / "authentic").glob("*.flac"))[:3]
    fakes = sorted((corpus / "fake" / "mp3_192").glob("*.flac"))[:3]
    if not genuine or not fakes:
        raise SystemExit("need both arms for the control")

    print("CONTROL — distance to the codec's fixed point\n")
    print(f"  {'file':34}{'R (dB)':>10}")
    gen_values, fake_values = [], []
    for path in genuine:
        value = idempotence(path)
        gen_values.append(value)
        print(f"  {('genuine ' + path.name[:24]):34}{value:>10.2f}")
    for path in fakes:
        value = idempotence(path)
        fake_values.append(value)
        print(f"  {('mp3_192 ' + path.name[:24]):34}{value:>10.2f}")

    gen_arr = np.array([v for v in gen_values if np.isfinite(v)])
    fake_arr = np.array([v for v in fake_values if np.isfinite(v)])
    separates = bool(gen_arr.size and fake_arr.size and gen_arr.min() > fake_arr.max())

    print("\n  PIPE TRAP — the same file, encoded through a pipe")
    piped = idempotence(genuine[0], use_pipe=True)
    proper = gen_values[0]
    print(f"    seekable file : {proper:.2f} dB")
    print(f"    through a pipe: {piped:.2f} dB")
    collapses = bool(np.isfinite(piped) and np.isfinite(proper) and piped < proper * 0.5)

    print("\n  VERDICT:")
    print("   ", "genuine sits above the fakes OK" if separates
          else "DOES NOT SEPARATE on this material")
    print("   ", "the pipe trap is reproduced OK" if collapses
          else "pipe made no difference here — check the encoder path")
    return 0 if separates else 1


# ============================== measurement ==================================


def run_corpus(corpus: Path, out: Path, limit: int, arms: List[str]) -> int:
    """Measure R on every arm. Slow: two LAME round trips per file."""
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
        writer = csv.DictWriter(fh, fieldnames=["arm", "file", "R"])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    value = idempotence(path)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                writer.writerow({"arm": arm, "file": path.name, "R": f"{value:.4f}"})
                rows.append({"arm": arm, "R": value})
                fh.flush()
                print(f"  {arm} [{index}/{len(paths)}] R={value:.2f}", flush=True)
    report(rows)
    return 0


def report(rows: List[dict]) -> None:
    """Fires BELOW theta, so the direction is inverted from every other probe."""
    by_arm: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row["R"])
    genuine = np.array(by_arm.get("genuine", []), dtype=np.float64)
    genuine = genuine[np.isfinite(genuine)]
    if not genuine.size:
        print("no usable genuine rows")
        return

    print("\n" + "=" * 60)
    print(f"IDEMPOTENCE — fires BELOW theta (Provir's theta = {THETA})")
    print("=" * 60)
    print(f"{'arm':14}{'n':>5}{'median R':>11}{'min':>8}{'fires':>9}")
    for arm in ["genuine"] + sorted(set(by_arm) - {"genuine"}):
        values = np.array(by_arm[arm], dtype=np.float64)
        values = values[np.isfinite(values)]
        if not values.size:
            continue
        print(f"{arm:14}{values.size:>5}{np.median(values):>11.2f}{values.min():>8.2f}"
              f"{100 * (values < THETA).mean():>8.0f}%")
    print(f"\ngenuine floor {genuine.min():.2f} dB — a transcode should sit well below it.")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the control, then the corpus measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true")
    # Each idempotence reading costs two full LAME round trips, so the
    # control is ~10 minutes on its own. Skippable once it has passed.
    parser.add_argument("--skip-control", action="store_true")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/idempotence_probe.csv"))
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--arms", nargs="+",
                        default=["mp3_192", "mp3_320", "opus_256", "aac_ff256"])
    args = parser.parse_args(argv)

    if args.control:
        return run_control(args.corpus)
    status = run_control(args.corpus)
    if status != 0:
        print("\nAborting: the statistic failed its own control.")
        return status
    return run_corpus(args.corpus, args.out, args.limit, args.arms)


if __name__ == "__main__":
    raise SystemExit(main())
