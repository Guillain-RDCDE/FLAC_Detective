#!/usr/bin/env python3
"""Build a paired authentic+transcode test set to (a) measure the cost of
raising Rule-12's decision threshold and (b) design/validate an abstention
gate that stops the ML model false-positiving on band-limited authentics.

Why this exists: ml/analyze_false_positives.py proved v3's false positives
cluster on band-limited material, and that the classic pipeline already
disambiguates such files via cutoff variance (`cutoff_std`) and container
bitrate — signals Rule 12 currently ignores. To turn that into a concrete
gate we need, for the SAME files, both the model's p_transcoded AND those
heuristic signals, computed with the *production* code (analyze_spectrum).
And we need real transcodes, not just authentics, so we can check the gate
keeps detecting genuine fakes (and measure threshold recall cost).

Sampling: from fp_analysis_v3.csv, take a stratified set — half model-flagged
(FP), half not — spread across rolloff buckets, so band-limited and
full-range material are both well represented. For each sampled authentic we
transcode to a few representative codecs (FLAC->lossy->FLAC, a "fake FLAC"),
then score authentic + each transcode identically.

Output ml/gate_testset.csv, one row per file:
  orig_idx, kind (authentic|mp3_128|...), is_transcode, src_rolloff_bucket,
  model_fp_orig, p_transcoded, cutoff_freq, cutoff_std, energy_ratio,
  real_bitrate_kbps

Run with the [ml] venv (4 workers on this 4-core box, BLAS threads pinned):
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/Scripts/python.exe \
        ml/build_gate_testset.py --per-group 125 --workers 4
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
from collections import defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Mel-spec config — MUST match ml_classifier.py / extract_features.py.
SAMPLE_RATE = 44100
SEGMENT_SEC = 10.0
N_MELS, N_FFT, HOP = 128, 2048, 512

REPO = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO / "src" / "flac_detective" / "models" / "cnn_v3.ts.pt"
# Outside the Dropbox-synced repo: avoids syncing ~GBs of throwaway transcodes.
TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_gate_tmp"

# Representative codec span: low CBR (cuts ~16k), high CBR (~20.5k), VBR (~19.5k).
CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
    {"name": "mp3_v0", "codec": "libmp3lame", "ext": "mp3", "args": ["-q:a", "0"]},
]

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        import torch

        torch.set_num_threads(1)
        _MODEL = torch.jit.load(str(MODEL_PATH), map_location="cpu")
        _MODEL.eval()
    return _MODEL


def _bucket_rolloff(hz: float) -> str:
    for edge, name in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < edge:
            return name
    return ">=14k"


def _predict(filepath: str) -> float | None:
    """Model p_transcoded for one file, reproducing ml_classifier._compute_mel."""
    import librosa
    import torch

    try:
        duration = librosa.get_duration(path=filepath)
        offset = max(0.0, (duration - SEGMENT_SEC) / 2)
        y, sr = librosa.load(
            filepath, sr=SAMPLE_RATE, offset=offset, duration=SEGMENT_SEC, mono=True
        )
        if len(y) < SAMPLE_RATE * SEGMENT_SEC * 0.5:
            return None
        tgt = int(SAMPLE_RATE * SEGMENT_SEC)
        y = np.pad(y, (0, tgt - len(y))) if len(y) < tgt else y[:tgt]
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_fft=N_FFT, hop_length=HOP, n_mels=N_MELS, fmax=sr // 2
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mn, mx = mel_db.min(), mel_db.max()
        mel_db = 2 * (mel_db - mn) / max(mx - mn, 1e-6) - 1.0
        with torch.no_grad():
            probs = torch.softmax(_get_model()(torch.from_numpy(mel_db[None, None])), dim=1)[0]
        return float(probs[1].item())
    except Exception as e:  # noqa: BLE001
        log.debug(f"predict fail {filepath}: {e}")
        return None


def _heuristics(filepath: str) -> tuple[float, float, float, float, int, float]:
    """Production cutoff/energy/std + container & apparent bitrate + bit depth.

    Returns (cutoff, std, energy, real_br, bit_depth, apparent_br). -1 sentinels
    on failure. The compression ratio real/apparent is derived downstream — it
    is bit-depth-invariant, unlike raw container bitrate.
    """
    from flac_detective.analysis.spectrum import analyze_spectrum

    try:
        cutoff, energy, std = analyze_spectrum(Path(filepath))
    except Exception as e:  # noqa: BLE001
        log.debug(f"spectrum fail {filepath}: {e}")
        cutoff = energy = std = -1.0
    real_br, bit_depth, apparent_br = -1.0, -1, -1.0
    try:
        import soundfile as sf

        from flac_detective.analysis.new_scoring.bitrate import (
            calculate_apparent_bitrate,
            calculate_real_bitrate,
        )

        info = sf.info(filepath)
        real_br = float(calculate_real_bitrate(Path(filepath), info.duration))
        bit_depth = {"PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "PCM_S8": 8}.get(info.subtype, 16)
        apparent_br = float(calculate_apparent_bitrate(info.samplerate, bit_depth, info.channels))
    except Exception as e:  # noqa: BLE001
        log.debug(f"bitrate fail {filepath}: {e}")
    return cutoff, std, energy, real_br, bit_depth, apparent_br


def _transcode(src: str, dst: Path, codec: dict) -> bool:
    """FLAC -> lossy -> FLAC. True on success."""
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
    # Force 16-bit FLAC: ffmpeg widens decoded-MP3 PCM to 24-bit by default, which
    # both misrepresents real-world fakes (usually 16-bit) and confounds the
    # bitrate comparison. s16 matches the authentic sources -> clean comp_ratio.
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


def _process_one(job: tuple[int, dict]) -> list[dict]:
    """Score one authentic + its transcodes; clean up transcodes afterwards."""
    idx, entry = job
    src = entry["path"]
    bucket = _bucket_rolloff(float(entry["rolloff_95_hz"]))
    fp_orig = int(entry["is_fp"])
    out: list[dict] = []

    def row(kind: str, is_trans: int, path: str) -> dict | None:
        p = _predict(path)
        if p is None:
            return None
        cutoff, std, energy, br, bd, app_br = _heuristics(path)
        comp_ratio = round(br / app_br, 4) if app_br > 0 else -1.0
        return {
            "orig_idx": idx,
            "kind": kind,
            "is_transcode": is_trans,
            "src_rolloff_bucket": bucket,
            "model_fp_orig": fp_orig,
            "p_transcoded": round(p, 4),
            "cutoff_freq": round(cutoff, 1),
            "cutoff_std": round(std, 1),
            "energy_ratio": round(energy, 8),
            "real_bitrate_kbps": round(br, 1),
            "bit_depth": bd,
            "apparent_bitrate_kbps": round(app_br, 1),
            "comp_ratio": comp_ratio,
        }

    r = row("authentic", 0, src)
    if r:
        out.append(r)
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(src, dst, codec):
                r = row(codec["name"], 1, str(dst))
                if r:
                    out.append(r)
        finally:
            # librosa/soundfile/AudioCache may still hold a handle; gc releases it
            # (CPython refcount) so Windows lets us delete. Tolerate residual locks —
            # main() rmtree's the whole dir at the end as a backstop.
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass
    return out


def sample_jobs(csv_path: Path, per_group: int) -> list[tuple[int, dict]]:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    fp = [r for r in rows if r["is_fp"] == "1"]
    ok = [r for r in rows if r["is_fp"] == "0"]
    rng = random.Random(42)

    def stratified(pool: list[dict], n: int) -> list[dict]:
        by_b: dict[str, list[dict]] = defaultdict(list)
        for r in pool:
            by_b[_bucket_rolloff(float(r["rolloff_95_hz"]))].append(r)
        buckets = list(by_b.values())
        per = max(1, n // len(buckets))
        picked: list[dict] = []
        for items in buckets:
            rng.shuffle(items)
            picked.extend(items[:per])
        rng.shuffle(picked)
        return picked[:n]

    chosen = stratified(fp, per_group) + stratified(ok, per_group)
    rng.shuffle(chosen)
    return list(enumerate(chosen))


def main(csv_path: Path, out_csv: Path, per_group: int, workers: int) -> int:
    if not MODEL_PATH.is_file():
        log.error(f"Model not found: {MODEL_PATH}")
        return 1
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    jobs = sample_jobs(csv_path, per_group)
    log.info(
        f"Sampled {len(jobs)} authentics ({per_group} FP + {per_group} non-FP, "
        f"stratified by rolloff). Each -> {len(CODECS)} transcodes. "
        f"{workers} workers."
    )

    try:
        from tqdm import tqdm

        progress = tqdm(total=len(jobs), unit="authentic")
    except ImportError:
        progress = None

    rows: list[dict] = []
    with mp.Pool(processes=workers) as pool:
        for res in pool.imap_unordered(_process_one, jobs, chunksize=2):
            rows.extend(res)
            if progress is not None:
                progress.update(1)
                progress.set_postfix(rows=len(rows))
    if progress is not None:
        progress.close()

    if not rows:
        log.error("No rows produced.")
        return 2
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n_auth = sum(1 for r in rows if r["is_transcode"] == 0)
    n_trans = sum(1 for r in rows if r["is_transcode"] == 1)
    log.info(f"Wrote {out_csv}: {len(rows)} rows ({n_auth} authentic, {n_trans} transcode)")
    shutil.rmtree(TMP_DIR, ignore_errors=True)  # backstop for any residual temp files
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/gate_testset.csv")
    p.add_argument(
        "--per-group",
        type=int,
        default=125,
        help="N FP + N non-FP authentics (stratified by rolloff).",
    )
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.per_group, args.workers))
