#!/usr/bin/env python3
"""Profile v3's false positives on certified-authentic FLACs.

Goal: before building a v4 dataset, find out *whether* the model's false
positives (real FLACs flagged as transcoded — the 20% that drag specificity
down to 80%) cluster in identifiable, band-limited material. If they do,
diversity / hard-negative sampling on that material will lift specificity.
If they're scattered, the problem is elsewhere and we save a soirée.

For each authentic file we reproduce **exactly** the Rule-12 inference
preprocessing (see src/flac_detective/.../ml_classifier.py): a 10 s mel-spec
of the middle of the track, per-sample normalised to [-1, 1], run through
cnn_v3.ts.pt. A file is a false positive when p_transcoded >= 0.5.

Alongside the prediction we measure two network-free proxies for "how much
this file looks like a transcode":

  * spectral_rolloff_95_hz : mean frequency below which 95% of the spectral
    energy sits. Band-limited material (classical, old recordings) sits low.
  * hf_energy_ratio_16k    : fraction of spectral energy above 16 kHz. A
    real full-range master has a non-trivial ratio; a transcode (and a
    naturally dull recording) sits near zero.

Outputs ml/fp_analysis_v3.csv (one row per file) + a console summary:
overall FP rate (sanity check vs the documented ~20%), FP rate bucketed by
rolloff, and the worst folders/labels. Run with the [ml] venv:

    .venv/Scripts/python.exe ml/analyze_false_positives.py \
        --manifest ml/authentic_files.json [--limit N] [--workers 8]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import multiprocessing as mp
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --- Mel-spec config: MUST match ml/extract_features.py and ml_classifier.py ---
SAMPLE_RATE = 44100
SEGMENT_SEC = 10.0
N_MELS = 128
N_FFT = 2048
HOP = 512

THRESHOLD = 0.5  # Rule-12 decision threshold; p>=THRESHOLD => "transcoded"
HF_CUTOFF_HZ = 16000.0

MODEL_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "flac_detective" / "models" / "cnn_v3.ts.pt"
)

# Worker-global model handle (loaded lazily, once per process).
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        import torch

        torch.set_num_threads(1)  # avoid thread oversubscription across workers
        _MODEL = torch.jit.load(str(MODEL_PATH), map_location="cpu")
        _MODEL.eval()
    return _MODEL


def _analyze_one(entry: dict) -> dict | None:
    """Load one authentic FLAC, predict, and measure spectral profile."""
    import librosa
    import torch

    path = entry["path"]
    try:
        duration = librosa.get_duration(path=path)
        offset = max(0.0, (duration - SEGMENT_SEC) / 2)
        y, sr = librosa.load(path, sr=SAMPLE_RATE, offset=offset, duration=SEGMENT_SEC, mono=True)
        if len(y) < SAMPLE_RATE * SEGMENT_SEC * 0.5:
            return None
        target_len = int(SAMPLE_RATE * SEGMENT_SEC)
        y = np.pad(y, (0, target_len - len(y))) if len(y) < target_len else y[:target_len]

        # One STFT, shared by the model mel-spec and the spectral profile.
        mag = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=HOP))
        power = mag.astype(np.float32) ** 2  # |stft|^2 == melspectrogram(power=2.0)

        # --- Model mel-spec, normalised EXACTLY like ml_classifier._compute_mel ---
        # melspectrogram(S=power) is identical to melspectrogram(y=y) with default
        # power=2.0 — same mel filterbank applied to the same power spectrogram.
        mel = librosa.feature.melspectrogram(
            S=power,
            sr=sr,
            n_mels=N_MELS,
            fmax=sr // 2,
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mn, mx = mel_db.min(), mel_db.max()
        rng = max(mx - mn, 1e-6)
        mel_db = 2 * (mel_db - mn) / rng - 1.0
        x = torch.from_numpy(mel_db[None, None, :, :])

        model = _get_model()
        with torch.no_grad():
            probs = torch.softmax(model(x), dim=1)[0]
        p_transcoded = float(probs[1].item())

        # --- Spectral profile (network-free proxies for "looks band-limited") ---
        rolloff = librosa.feature.spectral_rolloff(S=mag, sr=sr, roll_percent=0.95)
        rolloff_95 = float(np.mean(rolloff))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
        total = float(power.sum()) or 1.0
        hf_ratio = float(power[freqs >= HF_CUTOFF_HZ, :].sum() / total)

        return {
            "path": path,
            "top_label": entry.get("top_label", ""),
            "source": entry.get("source", ""),
            "p_transcoded": round(p_transcoded, 4),
            "is_fp": int(p_transcoded >= THRESHOLD),
            "rolloff_95_hz": round(rolloff_95, 1),
            "hf_ratio_16k": round(hf_ratio, 6),
        }
    except Exception as e:  # noqa: BLE001 — never let one bad file kill the run
        log.debug(f"skip {path}: {e}")
        return None


def _bucket_rolloff(hz: float) -> str:
    for edge, name in [
        (4000, "<4k"),
        (7000, "4-7k"),
        (10000, "7-10k"),
        (14000, "10-14k"),
    ]:
        if hz < edge:
            return name
    return ">=14k"


def _bucket_hf(ratio: float) -> str:
    for edge, name in [
        (1e-5, "<1e-5"),
        (1e-4, "1e-5..1e-4"),
        (1e-3, "1e-4..1e-3"),
    ]:
        if ratio < edge:
            return name
    return ">=1e-3"


def summarize(rows: list[dict]) -> None:
    n = len(rows)
    fp = sum(r["is_fp"] for r in rows)
    log.info("=" * 64)
    log.info(f"Analysed {n} authentic files")
    log.info(f"False positives (p>={THRESHOLD}): {fp}  ->  FP rate {fp / n:.1%}")
    log.info(f"=> implied specificity {1 - fp / n:.1%}  (v3 test set: 80.0%)")

    # FP rate by rolloff bucket — the decisive view.
    log.info("-" * 64)
    log.info("FP rate by spectral rolloff (95%) bucket:")
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_bucket[_bucket_rolloff(r["rolloff_95_hz"])].append(r)
    for b in ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]:
        items = by_bucket.get(b, [])
        if not items:
            continue
        bfp = sum(i["is_fp"] for i in items)
        log.info(f"  {b:>7}: {bfp:5d}/{len(items):5d} = {bfp / len(items):6.1%} FP")

    # FP rate by high-frequency energy ratio (>16 kHz) — the cleanest axis.
    log.info("-" * 64)
    log.info("FP rate by HF energy ratio (>16 kHz) bucket:")
    by_hf: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_hf[_bucket_hf(r["hf_ratio_16k"])].append(r)
    for b in ["<1e-5", "1e-5..1e-4", "1e-4..1e-3", ">=1e-3"]:
        items = by_hf.get(b, [])
        if not items:
            continue
        bfp = sum(i["is_fp"] for i in items)
        log.info(f"  {b:>11}: {bfp:5d}/{len(items):5d} = {bfp / len(items):6.1%} FP")

    # Worst labels/folders by FP rate (min 10 files to be meaningful).
    log.info("-" * 64)
    log.info("Top labels by FP rate (>=10 files):")
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_label[r["top_label"]].append(r)
    ranked = []
    for label, items in by_label.items():
        if len(items) >= 10:
            rate = sum(i["is_fp"] for i in items) / len(items)
            ranked.append((rate, len(items), label))
    ranked.sort(reverse=True)
    for rate, cnt, label in ranked[:20]:
        log.info(f"  {rate:6.1%}  ({cnt:4d} files)  {label}")
    log.info("=" * 64)


def main(manifest_path: Path, out_csv: Path, workers: int, limit: int | None) -> int:
    if not MODEL_PATH.is_file():
        log.error(f"Model not found: {MODEL_PATH}")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    if limit:
        files = files[:limit]
    log.info(
        f"Scoring {len(files)} authentic files with {MODEL_PATH.name} " f"({workers} workers)..."
    )

    try:
        from tqdm import tqdm

        progress = tqdm(total=len(files), unit="file")
    except ImportError:
        progress = None

    rows: list[dict] = []
    skipped = 0
    with mp.Pool(processes=workers) as pool:
        for res in pool.imap_unordered(_analyze_one, files, chunksize=4):
            if res is None:
                skipped += 1
            else:
                rows.append(res)
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=len(rows), skip=skipped, fp=sum(r["is_fp"] for r in rows))
    if progress is not None:
        progress.close()

    if not rows:
        log.error("No files scored.")
        return 2

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info(f"Wrote per-file results to {out_csv}  ({len(rows)} rows, " f"{skipped} skipped)")

    summarize(rows)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--manifest", default="ml/authentic_files.json")
    p.add_argument("--out", default="ml/fp_analysis_v3.csv")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument(
        "--limit", type=int, default=None, help="Score only the first N files (smoke test)."
    )
    args = p.parse_args()
    sys.exit(main(Path(args.manifest), Path(args.out), args.workers, args.limit))
