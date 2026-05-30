#!/usr/bin/env python3
"""Temporal-texture probe: does the signal averaging destroyed live in the
TIME dynamics? texture_probe.py used time-averaged spectra and reached only
AUC 0.68 (mp3_128) / 0.53 (mp3_320) on band-limited material. The strongest
theoretical MP3 fingerprint is temporal and periodic: the encoder re-quantises
every 1152-sample frame (38.28 Hz) and 576-sample granule (76.56 Hz), stamping
a periodic modulation onto the energy envelope that an averaged spectrum cannot
see — and that the mono CNN, working on a coarse mel, likely smears too.

Features (same 120 band-limited <7k model-flagged sources as texture_probe, so
results are directly comparable):
  MODULATION (the headline) — energy of the envelope's modulation spectrum near
    the MP3 frame rate (38.28 Hz) and granule rate (76.56 Hz), as a fraction of
    total modulation energy. Computed on full signal, side channel, and an HF
    sub-band. A periodic re-quantisation pulse shows here.
  TEMPORAL VARIANCE — per-frame side flatness std, in-band flatness std,
    side-energy coefficient of variation, spectral flux mean/std. Quantisation
    that's invisible on average can still change frame-to-frame dynamics.

Envelope is framed short (n_fft=512, hop=128 -> 344 Hz frame rate, envelope
Nyquist 172 Hz) so both 38.28 and 76.56 Hz are resolved cleanly.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/texture_temporal_probe.py --n 120
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
MP3_FRAME_HZ = SR / 1152.0  # 38.28 Hz
MP3_GRANULE_HZ = SR / 576.0  # 76.56 Hz
TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_temporal_tmp"

CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
    {"name": "mp3_v0", "codec": "libmp3lame", "ext": "mp3", "args": ["-q:a", "0"]},
]


def _modulation_peak(
    env: np.ndarray, frame_rate: float, target_hz: float, half_bw: float = 1.5
) -> float:
    """Fraction of the (detrended) envelope's modulation energy within
    [target-half_bw, target+half_bw] Hz. Captures periodic re-quantisation."""
    env = env - env.mean()
    if env.std() < 1e-12 or len(env) < 64:
        return 0.0
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env)))) ** 2
    f = np.fft.rfftfreq(len(env), d=1.0 / frame_rate)
    total = spec[1:].sum() + 1e-20  # drop DC
    band = (f >= target_hz - half_bw) & (f <= target_hz + half_bw)
    return float(spec[band].sum() / total)


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
    (
        L,
        R,
    ) = (
        L[:n],
        R[:n],
    )
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)

    # Short-window STFTs for fine temporal resolution.
    n_fft, hop = 512, 128
    frame_rate = sr / hop  # 344.5 Hz
    S_mid = np.abs(librosa.stft(mid, n_fft=n_fft, hop_length=hop))  # (freq, time)
    S_side = np.abs(librosa.stft(side, n_fft=n_fft, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Energy envelopes (per frame).
    env_full = (S_mid**2).sum(axis=0)
    env_side = (S_side**2).sum(axis=0)
    hf = freqs >= 4000  # noise-tail / upper region
    env_hf = (S_mid[hf, :] ** 2).sum(axis=0)

    feats = {
        "is_stereo": is_stereo,
        "mod38_full": round(_modulation_peak(env_full, frame_rate, MP3_FRAME_HZ), 6),
        "mod38_side": round(_modulation_peak(env_side, frame_rate, MP3_FRAME_HZ), 6),
        "mod38_hf": round(_modulation_peak(env_hf, frame_rate, MP3_FRAME_HZ), 6),
        "mod76_full": round(_modulation_peak(env_full, frame_rate, MP3_GRANULE_HZ), 6),
        "mod76_hf": round(_modulation_peak(env_hf, frame_rate, MP3_GRANULE_HZ), 6),
    }

    # Per-frame spectral flatness (geo/arith mean of power), temporal std.
    def frame_flatness(S):
        p = S**2 + 1e-12
        gm = np.exp(np.mean(np.log(p), axis=0))
        am = np.mean(p, axis=0)
        return gm / am

    ff_mid = frame_flatness(S_mid)
    ff_side = frame_flatness(S_side)
    feats["inband_flat_tstd"] = round(float(np.std(ff_mid)), 6)
    feats["side_flat_tstd"] = round(float(np.std(ff_side)), 6)
    feats["side_energy_cv"] = round(float(np.std(env_side) / (np.mean(env_side) + 1e-12)), 4)
    # Spectral flux: frame-to-frame magnitude change.
    flux = np.sqrt(((np.diff(S_mid, axis=1)) ** 2).sum(axis=0))
    feats["flux_mean"] = round(float(np.mean(flux)), 4)
    feats["flux_std"] = round(float(np.std(flux)), 4)
    return feats


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
    out = []

    def emit(kind, is_t, path):
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

    emit("authentic", 0, entry["path"])
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(entry["path"], dst, codec):
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
    band = [r for r in rows if float(r["rolloff_95_hz"]) < 7000 and r["is_fp"] == "1"]
    rng = random.Random(42)
    rng.shuffle(band)
    jobs = list(enumerate(band[:n]))
    log.info(
        f"Probing {len(jobs)} band-limited model-flagged sources ×{len(CODECS)}. "
        f"frame={MP3_FRAME_HZ:.2f}Hz granule={MP3_GRANULE_HZ:.2f}Hz. {workers} workers."
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
        "mod38_full",
        "mod38_side",
        "mod38_hf",
        "mod76_full",
        "mod76_hf",
        "inband_flat_tstd",
        "side_flat_tstd",
        "side_energy_cv",
        "flux_mean",
        "flux_std",
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
    p.add_argument("--out", default="ml/texture_temporal.csv")
    p.add_argument("--n", type=int, default=120)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.n, args.workers))
