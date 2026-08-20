#!/usr/bin/env python3
"""MP3_IDEM — distance to the codec's fixed point, the alignment-free candidate.

Where this comes from
---------------------
Full specification given by Jamie Dodd (Provir) on 2026-08-19, after we asked.
His measurement: **67 % fire on Opus transcodes at 0 % on genuine** — on the one
arm where every alignment-based family of ours is structurally blind, because
CELT transcodes through a 48 kHz resample that destroys sample-exact alignment.
This is the only known family with NO alignment dependence at all: we re-encode
from PCM, so the encoder picks its own grid every time.

The idea is a fixed point. Encode-decode is a map on audio; lossy-processed audio
is close to that map's fixed point already. So:

    a = 60 s of PCM
    b = decode(encode(a))     first pass
    c = decode(encode(b))     second pass
    d1 = dist(a, b)           damage of the first pass
    d2 = dist(b, c)           damage of the second pass
    R  = 20 * log10(d1 / d2)  dB

A lossless source is FAR from the fixed point: the first pass does real damage
and the second much less, so R is large (his sources: 3.00-3.76 dB). A transcode
is already near it: both passes move it about equally, R collapses toward zero
(his fakes: 0.18-1.46 dB).

The trap he warned about, verified here before this file existed
-----------------------------------------------------------------
**Every encode goes to a SEEKABLE FILE, never a pipe.** Without the finalized
Xing/LAME header the decoder loses the encoder delay, the second pass lands on a
different MDCT grid, and R does not weaken — it DISAPPEARS and looks exactly like
a dead idea (his 2.56 -> 0.04; reproduced here 0.65 -> -0.33 on 2026-08-19).

Our instrument, named (his standing rule)
-----------------------------------------
Encoder: ffmpeg libmp3lame at 320 kb/s CBR, to .mp3 files on disk. dist(x, y):
mono mixes aligned by full cross-correlation within +-16384 samples, |STFT| with
2048-point Hann and hop 1024, cells restricted to 0.3-16 kHz with BOTH sides
above -80 dBFS; abstain unless more than 200 cells survive; dist = mean absolute
dB difference over surviving cells. His THETA = 2.0 is frozen on HIS computation
and is not imported: any bar here is calibrated on our own genuine corpus or not
at all. Where his four-line spec was silent (the survival floor, stereo handling
— we encode the original channel count and measure the mono mix), the choices
are stated here rather than hidden.

Predictions, registered before the corpus run, in the exchange's convention
---------------------------------------------------------------------------
    P1  ORDERING: genuine median R exceeds every transcode arm's median R.
    P2  OPUS, the reason this family exists: AUC of (-R) vs genuine >= 0.75 on
        opus_256.
    P3  MP3_320 — the fixed point this instrument re-encodes toward — reads at
        least as strongly: AUC >= 0.85.
    P4  Abstention stays below 20 % on every arm (the statistic must not earn
        its numbers by refusing the hard files).

Being wrong on P2 kills the candidate family. Being wrong on P3 while P2 holds
would mean the statistic is NOT reading distance-to-fixed-point but something
Opus-specific, and its docstring would be lying — that outcome matters more
than either number alone.

Also registered: one of our genuine files (Guinean percussion) read R = 0.65 in
the 2026-08-19 spot check. If it reads low again it is not a false positive of
the statistic — it is the statistic being right about a master whose production
chain was already lossy, which nobody asked us to judge. Wild-master provenance
is exactly what the wild ledger's `basis` field exists for.

Results are appended below this line AFTER the corpus run, never above it.
--------------------------------------------------------------------------------
(not yet run)

Usage::

    python ml/mp3_idem_probe.py --selftest    # known answers, incl. the file trap
    python ml/mp3_idem_probe.py               # corpus run (resumable)
"""

from __future__ import annotations

import argparse
import csv
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from edge_width_probe import ARMS, auc  # noqa: E402

EXCERPT_SEC = 60.0
BITRATE = "320k"
NFFT = 2048
HOP = 1024
BAND_LO_HZ = 300.0
BAND_HI_HZ = 16000.0
FLOOR_DB = -80.0
MIN_CELLS = 200
MAX_LAG = 16384


def require_ffmpeg() -> str:
    """ffmpeg with libmp3lame, or a precise refusal."""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit(
            "ffmpeg not found on PATH; the probe re-encodes through "
            "libmp3lame and cannot run without it."
        )
    probe = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, text=True)
    if "libmp3lame" not in probe.stdout:
        raise SystemExit("this ffmpeg has no libmp3lame encoder.")
    return exe


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{Path(cmd[0]).name} failed ({proc.returncode}): " f"{proc.stderr.strip()[-300:]}"
        )


def roundtrip(audio: np.ndarray, rate: int, work: Path, tag: str, ffmpeg: str) -> np.ndarray:
    """decode(encode(audio)) through libmp3lame 320, via FILES on disk.

    The .mp3 lands on a seekable path so the Xing/LAME header is finalized and
    the decoder recovers the encoder delay — the trap that makes R vanish.
    """
    src = work / f"{tag}_src.wav"
    enc = work / f"{tag}.mp3"
    dec = work / f"{tag}_dec.wav"
    sf.write(str(src), audio, rate, subtype="PCM_16")
    _run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-c:a",
            "libmp3lame",
            "-b:a",
            BITRATE,
            str(enc),
        ]
    )
    _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(enc), str(dec)])
    out, out_rate = sf.read(str(dec), dtype="float32")
    if out_rate != rate:
        raise RuntimeError(f"decoder returned {out_rate} Hz for {rate} Hz input")
    return out


def _mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else np.mean(x, axis=1)


def align(ref: np.ndarray, other: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Trim both mono signals to their best overlap within +-MAX_LAG samples.

    FFT-based correlation (scipy, method="fft"): the direct method is O(n^2) and
    took minutes per file on 10 s windows — caught when the selftest hung.
    """
    from scipy.signal import correlate as _xcorr

    n = min(len(ref), len(other), 10 * 44100)  # correlate on <= 10 s
    a = ref[:n].astype(np.float64)
    b = other[:n].astype(np.float64)
    corr = _xcorr(b, a, mode="full", method="fft")
    center = len(b) - 1
    lo, hi = center - MAX_LAG, center + MAX_LAG + 1
    lag = int(np.argmax(np.abs(corr[lo:hi]))) - MAX_LAG
    if lag >= 0:
        other = other[lag:]
    else:
        ref = ref[-lag:]
    n = min(len(ref), len(other))
    return ref[:n], other[:n]


def _stft_db(x: np.ndarray) -> np.ndarray:
    win = np.hanning(NFFT)
    frames = 1 + (len(x) - NFFT) // HOP
    if frames < 4:
        return np.empty((0, NFFT // 2 + 1))
    strided = np.lib.stride_tricks.sliding_window_view(x, NFFT)[::HOP][:frames]
    spec = np.abs(np.fft.rfft(strided * win, axis=1))
    return 20.0 * np.log10(spec + 1e-12)


def dist(x: np.ndarray, y: np.ndarray, rate: int) -> Tuple[float, int]:
    """Mean |dB| difference over surviving cells, and how many survived."""
    ref, other = align(_mono(x), _mono(y))
    dbx = _stft_db(ref)
    dby = _stft_db(other)
    frames = min(len(dbx), len(dby))
    if frames == 0:
        return float("nan"), 0
    dbx, dby = dbx[:frames], dby[:frames]
    freqs = np.fft.rfftfreq(NFFT, 1.0 / rate)
    band = (freqs >= BAND_LO_HZ) & (freqs <= BAND_HI_HZ)
    dbx, dby = dbx[:, band], dby[:, band]
    alive = (dbx > FLOOR_DB) & (dby > FLOOR_DB)
    survivors = int(alive.sum())
    if survivors <= MIN_CELLS:
        return float("nan"), survivors
    return float(np.mean(np.abs(dbx[alive] - dby[alive]))), survivors


def mp3_idem(audio: np.ndarray, rate: int, ffmpeg: str) -> Tuple[float, float, float]:
    """(R_db, d1, d2) for one excerpt; NaN R is an abstention, never a score."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        b = roundtrip(audio, rate, work, "pass1", ffmpeg)
        c = roundtrip(b, rate, work, "pass2", ffmpeg)
    d1, n1 = dist(audio, b, rate)
    d2, n2 = dist(b, c, rate)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan"), d1, d2
    return 20.0 * np.log10(d1 / d2), d1, d2


# ---------------------------------------------------------------------------
# Self-test on known answers. The control that bites is a REAL pre-transcode:
# a signal we lossy-process ourselves must read closer to the fixed point than
# the same signal fresh. A synthetic that shares the instrument's assumptions
# proves nothing (this project's standing lesson).
# ---------------------------------------------------------------------------

RATE = 44100


def _tonal_mix(seconds: float = 60.0) -> np.ndarray:
    rng = np.random.default_rng(20260820)
    t = np.arange(int(RATE * seconds)) / RATE
    x = np.zeros_like(t)
    for f0, amp in ((220, 0.15), (440, 0.12), (1320, 0.08), (3520, 0.05), (9240, 0.03)):
        x += amp * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 6.28))
    x += 0.02 * rng.standard_normal(len(t))
    env = 0.5 * (1 + np.sin(2 * np.pi * 0.37 * t))
    return (x * env).astype(np.float32)


def selftest() -> int:
    ffmpeg = require_ffmpeg()
    failures: List[str] = []

    def check(name: str, cond: bool, detail: str) -> None:
        print(f"  {'PASS' if cond else 'FAIL'}  {name}  ({detail})", flush=True)
        if not cond:
            failures.append(name)

    print("1. fresh signal vs the SAME signal pre-transcoded through mp3_320")
    fresh = _tonal_mix()
    with tempfile.TemporaryDirectory() as tmp:
        pre = roundtrip(fresh, RATE, Path(tmp), "pre", ffmpeg)
    r_fresh, d1f, d2f = mp3_idem(fresh, RATE, ffmpeg)
    r_pre, d1p, d2p = mp3_idem(pre, RATE, ffmpeg)
    check("fresh reads finite", np.isfinite(r_fresh), f"R={r_fresh:.2f} dB")
    check("pre-transcoded reads finite", np.isfinite(r_pre), f"R={r_pre:.2f} dB")
    check(
        "fresh is FARTHER from the fixed point",
        r_fresh > r_pre + 0.5,
        f"{r_fresh:.2f} vs {r_pre:.2f} dB",
    )

    print("2. same, on noise (the hard-to-encode extreme)")
    rng = np.random.default_rng(7)
    noise = (0.1 * rng.standard_normal(int(RATE * 30))).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        noise_pre = roundtrip(noise, RATE, Path(tmp), "npre", ffmpeg)
    r_n, *_ = mp3_idem(noise, RATE, ffmpeg)
    r_np, *_ = mp3_idem(noise_pre, RATE, ffmpeg)
    check(
        "ordering holds on noise",
        np.isfinite(r_n) and np.isfinite(r_np) and r_n > r_np,
        f"{r_n:.2f} vs {r_np:.2f} dB",
    )

    print("3. silence abstains rather than scoring")
    silence = np.zeros(int(RATE * 30), dtype=np.float32)
    r_s, *_ = mp3_idem(silence, RATE, ffmpeg)
    check("silence -> NaN", not np.isfinite(r_s), f"R={r_s}")

    print(f"\nselftest: {'OK' if not failures else 'FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Corpus run — resumable, line-flushed, per this machine's standing lessons.
# ---------------------------------------------------------------------------


def measure(path: str, ffmpeg: str) -> Optional[dict]:
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0 or rate not in (44100, 48000):
        return None
    try:
        r, d1, d2 = mp3_idem(data, rate, ffmpeg)
    except Exception:
        return None
    return {"path": Path(path).name, "rate": rate, "R_db": r, "d1": d1, "d2": d2}


def collect(limit_genuine: int, limit_arm: int, out_path: Path) -> List[dict]:
    ffmpeg = require_ffmpeg()
    done = set()
    rows: List[dict] = []
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            for old in csv.DictReader(fh):
                done.add((old["arm"], old["path"]))
                rows.append(old)
        print(f"reprise: {len(rows)} lignes deja mesurees", flush=True)

    fieldnames = ["arm", "path", "rate", "R_db", "d1", "d2"]
    with open(out_path, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for arm, patterns in ARMS.items():
            limit = limit_genuine if arm == "genuine" else limit_arm
            paths: List[str] = []
            for pattern in patterns:
                found = sorted(glob.glob(pattern, recursive="**" in pattern))
                paths.extend(found[: limit // len(patterns) + 1])
            paths = [str(Path(p)) for p in paths]
            seen = 0
            for path in dict.fromkeys(paths):
                if seen >= limit:
                    break
                if (arm, Path(path).name) in done:
                    seen += 1
                    continue
                row = measure(path, ffmpeg)
                if row is None:
                    continue
                row["arm"] = arm
                writer.writerow(row)
                fh.flush()
                rows.append(row)
                seen += 1
            print(f"{arm}: {seen} mesures", flush=True)
    return rows


def _f(row: dict, key: str) -> float:
    try:
        return float(row[key])
    except (TypeError, ValueError):
        return float("nan")


def report(rows: List[dict]) -> None:
    arms = list(ARMS)
    values = {}
    for arm in arms:
        r = np.array([_f(row, "R_db") for row in rows if row["arm"] == arm])
        values[arm] = r

    print("\n" + "=" * 74)
    print("MP3_IDEM — distance au point fixe (R eleve = loin = source fraiche)")
    print("=" * 74)
    print(f"\n{'arm':12}{'n':>5}{'abst.':>7}{'med R':>8}{'p10':>7}{'p90':>7}{'AUC(-R)':>9}")
    gen = values["genuine"][np.isfinite(values["genuine"])]
    for arm in arms:
        r = values[arm]
        finite = r[np.isfinite(r)]
        abst = int(np.sum(~np.isfinite(r)))
        a = auc(-finite, -gen) if arm != "genuine" and finite.size and gen.size else float("nan")
        med = np.median(finite) if finite.size else float("nan")
        p10 = np.percentile(finite, 10) if finite.size else float("nan")
        p90 = np.percentile(finite, 90) if finite.size else float("nan")
        print(f"{arm:12}{len(r):>5}{abst:>7}{med:>8.2f}{p10:>7.2f}{p90:>7.2f}{a:>9.2f}")

    if gen.size:
        bar = float(np.percentile(gen, 5))
        print(f"\nbarre = p5 des authentiques = {bar:.2f} dB (5 % de cout authentique)")
        for arm in arms:
            if arm == "genuine":
                continue
            r = values[arm]
            finite = r[np.isfinite(r)]
            if not finite.size:
                continue
            fires = int((finite <= bar).sum())
            print(
                f"    {arm:12} {fires:3d}/{len(r):3d} de l'arme entiere"
                f" = {100 * fires / len(r):5.1f} %"
            )

    print("\nP1 ordering / P2 opus AUC>=0.75 / P3 mp3_320 AUC>=0.85 / P4 abst<20% :")
    print("voir la docstring — les predictions y sont gelees, les resultats s'appendent.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MP3_IDEM fixed-point probe")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--genuine", type=int, default=120)
    parser.add_argument("--arm", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/mp3_idem.csv"))
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    rows = collect(args.genuine, args.arm, args.out)
    print(f"\n{len(rows)} lignes -> {args.out}", flush=True)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
