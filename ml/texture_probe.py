#!/usr/bin/env python3
"""Probe for transcode fingerprints that survive in BAND-LIMITED material —
the regime where the spectral cliff, compression ratio, the CNN, AND Rule 9
all fail (Rule 9's three tests all operate in the 10-20 kHz band, which is
empty for band-limited sources).

The bet: when there's nothing to cut above the rolloff, the MP3 encoder still
leaves fingerprints (a) in the STEREO side channel (joint-stereo quantises L-R
aggressively) and (b) WITHIN the occupied band (zeroed MDCT coefficients ->
spectral holes; quantisation terracing). The CNN never sees either — it runs on
a mono mel-spectrogram.

Method that matters: PAIRED analysis. For each band-limited source we score the
authentic AND its transcodes, so each feature is compared within-pair (transcode
vs its own original), controlling for the source. A feature whose direction is
consistent across pairs is usable even if population distributions overlap.

Feature battery per file (20 s middle segment, stereo kept):
  STEREO          side_mid_ratio, lr_corr, side_rolloff, side_to_mid_rolloff
  IN-BAND TEXTURE flatness_inband, holes_inband (frac bins < peak-40dB),
                  terrace_peakfrac (clustering of log-mag), side_flatness_inband
  RULE-9 CONTROLS preecho_pct, aliasing_corr, mp3_pattern (expected ~0 -> proves
                  the existing arsenal is blind here)

Output ml/texture_probe.csv. Run with the [ml] venv:
    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/texture_probe.py --n 120
"""

from __future__ import annotations

import argparse
import csv
import gc
import logging
import multiprocessing as mp
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SR = 44100
SEG = 20.0
N_FFT, HOP = 2048, 512
TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_texture_tmp"

CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
    {"name": "mp3_v0", "codec": "libmp3lame", "ext": "mp3", "args": ["-q:a", "0"]},
]


def _rolloff95(mag_mean: np.ndarray, freqs: np.ndarray) -> float:
    c = np.cumsum(mag_mean)
    if c[-1] <= 0:
        return 0.0
    return float(freqs[np.searchsorted(c, 0.95 * c[-1])])


def _features(path: str) -> dict | None:
    import librosa

    try:
        y, sr = librosa.load(path, sr=SR, mono=False, offset=0.0, duration=SEG)
    except Exception as e:  # noqa: BLE001
        log.debug(f"load fail {path}: {e}")
        return None
    if y.ndim == 1:
        L = R = y
        is_stereo = 0
    else:
        L, R = y[0], y[1]
        is_stereo = int(np.std(L - R) > 1e-5)
    n = min(len(L), len(R))
    if n < SR * 5:
        return None
    L, R = L[:n], R[:n]
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)

    # Stereo features.
    e_mid = float(np.sum(mid**2)) + 1e-12
    e_side = float(np.sum(side**2))
    side_mid_ratio = e_side / e_mid
    try:
        lr_corr = float(np.corrcoef(L, R)[0, 1]) if np.std(L) > 1e-9 and np.std(R) > 1e-9 else 1.0
    except Exception:  # noqa: BLE001
        lr_corr = 1.0

    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    mag_mid = np.abs(librosa.stft(mid, n_fft=N_FFT, hop_length=HOP)).mean(axis=1)
    mag_side = np.abs(librosa.stft(side, n_fft=N_FFT, hop_length=HOP)).mean(axis=1)
    ro_mid = _rolloff95(mag_mid, freqs)
    ro_side = _rolloff95(mag_side, freqs)

    # In-band texture (occupied band: 50 Hz .. mid rolloff).
    band = (freqs >= 50) & (freqs <= max(ro_mid, 1000))
    mb = mag_mid[band]
    sb = mag_side[band]
    if mb.size < 8:
        return None
    peak = mb.max() + 1e-12
    holes_inband = float(np.mean(mb < peak * 10 ** (-40 / 20)))  # frac of deep bins
    # Spectral flatness (geometric/arithmetic mean of power).
    pw = mb**2 + 1e-12
    flatness_inband = float(np.exp(np.mean(np.log(pw))) / np.mean(pw))
    pws = sb**2 + 1e-12
    side_flatness_inband = float(np.exp(np.mean(np.log(pws))) / np.mean(pws))
    # Terracing: clustering of log-magnitude into a histogram (quantised spectra
    # pile into fewer levels -> higher peak fraction).
    logm = 20 * np.log10(mb / peak + 1e-12)
    hist, _ = np.histogram(logm, bins=40, range=(-120, 0))
    terrace_peakfrac = float(hist.max() / max(hist.sum(), 1))

    # Rule-9 controls (operate at 10-20 kHz -> expected ~0 for band-limited).
    from flac_detective.analysis.new_scoring.artifacts import (
        detect_hf_aliasing,
        detect_mp3_noise_pattern,
        detect_preecho_artifacts,
    )

    try:
        preecho_pct, _, _ = detect_preecho_artifacts(mid, sr)
    except Exception:  # noqa: BLE001
        preecho_pct = -1.0
    try:
        aliasing = detect_hf_aliasing(mid, sr)
    except Exception:  # noqa: BLE001
        aliasing = -1.0
    try:
        mp3_pat = int(detect_mp3_noise_pattern(mid, sr))
    except Exception:  # noqa: BLE001
        mp3_pat = -1

    return {
        "is_stereo": is_stereo,
        "side_mid_ratio": round(side_mid_ratio, 6),
        "lr_corr": round(lr_corr, 4),
        "ro_mid": round(ro_mid, 1),
        "ro_side": round(ro_side, 1),
        "side_to_mid_rolloff": round(ro_side / ro_mid, 4) if ro_mid > 0 else 0.0,
        "holes_inband": round(holes_inband, 5),
        "flatness_inband": round(flatness_inband, 6),
        "side_flatness_inband": round(side_flatness_inband, 6),
        "terrace_peakfrac": round(terrace_peakfrac, 5),
        "preecho_pct": round(preecho_pct, 2),
        "aliasing_corr": round(aliasing, 4),
        "mp3_pattern": mp3_pat,
    }


def _transcode(src: str, dst: Path, codec: dict) -> bool:
    tmp = dst.with_suffix(f".tmp.{codec['ext']}")
    enc = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        src,
        "-c:a",
        codec["codec"],
        *codec["args"],
        str(tmp),
    ]
    if subprocess.run(enc, capture_output=True).returncode != 0:
        tmp.unlink(missing_ok=True)
        return False
    # Keep stereo (no -ac), 16-bit FLAC.
    dec = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(tmp),
        "-c:a",
        "flac",
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    ok = subprocess.run(dec, capture_output=True).returncode == 0
    tmp.unlink(missing_ok=True)
    return ok


def _process(job: tuple[int, dict]) -> list[dict]:
    idx, entry = job
    src = entry["path"]
    out = []

    def emit(kind: str, is_t: int, path: str):
        f = _features(path)
        if f is None:
            return
        f.update(
            orig_idx=idx,
            kind=kind,
            is_transcode=is_t,
            src_rolloff=float(entry["rolloff_95_hz"]),
            model_fp=int(entry["is_fp"]),
        )
        out.append(f)

    emit("authentic", 0, src)
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(src, dst, codec):
                emit(codec["name"], 1, str(dst))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass
    return out


def main(csv_path: Path, out_csv: Path, n: int, workers: int) -> int:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    # Band-limited sources (<7k) where everything else fails; prefer model-flagged.
    band = [r for r in rows if float(r["rolloff_95_hz"]) < 7000]
    fp = [r for r in band if r["is_fp"] == "1"]
    rng = random.Random(42)
    rng.shuffle(fp)
    chosen = fp[:n]
    jobs = list(enumerate(chosen))
    log.info(
        f"{len(band)} band-limited (<7k) sources, {len(fp)} model-flagged. "
        f"Probing {len(jobs)} (×{len(CODECS)} transcodes). {workers} workers."
    )
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm

        prog = tqdm(total=len(jobs), unit="src")
    except ImportError:
        prog = None
    results: list[dict] = []
    with mp.Pool(workers) as pool:
        for res in pool.imap_unordered(_process, jobs, chunksize=2):
            results.extend(res)
            if prog:
                prog.update(1)
    if prog:
        prog.close()

    if not results:
        log.error("No results.")
        return 2
    cols = [
        "orig_idx",
        "kind",
        "is_transcode",
        "src_rolloff",
        "model_fp",
        "is_stereo",
        "side_mid_ratio",
        "lr_corr",
        "ro_mid",
        "ro_side",
        "side_to_mid_rolloff",
        "holes_inband",
        "flatness_inband",
        "side_flatness_inband",
        "terrace_peakfrac",
        "preecho_pct",
        "aliasing_corr",
        "mp3_pattern",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)
    log.info(f"Wrote {out_csv}: {len(results)} rows")
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/texture_probe.csv")
    p.add_argument("--n", type=int, default=120)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.n, args.workers))
