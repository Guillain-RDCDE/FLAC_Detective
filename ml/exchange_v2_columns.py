#!/usr/bin/env python3
"""Our evidence columns on fd-exchange-v2 — the half of the format we owe.

The evidence-column exchange (proposed 2026-08-22, accepted by Provir the
same day): alongside verdicts, each side returns the measurements its verdict
rests on, per file, so a disagreement is adjudicable at the mechanism. His
list is in his 08-22 message (rolloff, brickwall grade and detail, stereo
correlations and mid/side HF ratio, M/S conditional, bit depth and LSB
entropy, lattice probe with licence and idem at best phase, deep-ceiling /
seam, coverage, rate, byte size, full flag list). Ours, computed here on the
590 opaque files — the key never enters this file and never leaves the
machine:

    engine      score, verdict, evidence families, per-rule breakdown,
                hi-res axis (v1.13.0 engine, deep=True, CNN on)
    spectral    cutoff_hz, cutoff_std_hz (the 250 Hz grid's wander),
                energy_ratio above the cutoff, residual_floor_db (the
                near-Nyquist depth reading, NaN where not computed)
    container   container_kbps (bytes * 8 / seconds), sample_rate, bit_depth
    witnesses   stereo_run (R15's side-channel dead-run median),
                seam (R14's temporal-seam drop)
    idem        --idem pass: R at the canonical phases {0, 529, 47} under the
                shipped libmp3lame-320 probe, min and phase-0 reported both
                (the grid-lock rule: no phase-0-only number leaves this file)

Two passes because the idem read costs as much as everything else together:
    python ml/exchange_v2_columns.py --out ml/exchange/fd-exchange-v2_columns_flacdetective.csv
    python ml/exchange_v2_columns.py --idem --out ml/exchange/fd-exchange-v2_idem_flacdetective.csv
Both resumable. Sent together with the answer key once his verdicts arrive —
never before (the exchange protocol: columns travel with verdicts, not ahead
of them).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# The frozen set OFF Dropbox. The Dropbox transport copy (Temp/) is "files on
# demand": every file there became a reparse-point placeholder after upload,
# and reads through placeholders returned wrong bytes on two files (0119,
# 0557 — same size, reference decoder aborts, hash off the manifest) while
# the server-side copy Provir downloaded verified 590/590. Measurements read
# the original; the transport copy is for transport.
AUDIO = Path(r"C:\Users\loutr\fd-exchange-v2-2026-08\audio")
EXCERPT_SEC = 60.0


def engine_and_measurements(path: Path, analyzer) -> Optional[dict]:
    from flac_detective.__version__ import __version__
    from flac_detective.analysis.new_scoring.stereo_image import side_dead_run
    from flac_detective.analysis.new_scoring.temporal import temporal_seam
    from flac_detective.analysis.spectrum import analyze_spectrum

    try:
        result = analyzer.analyze_file(str(path))
    except Exception as exc:
        print(f"  engine failed on {path.name}: {exc}", flush=True)
        return None
    if result.get("verdict") == "ERROR":
        return None
    try:
        cutoff, energy, std, resid = analyze_spectrum(path)
    except Exception:
        cutoff, energy, std, resid = float("nan"), float("nan"), float("nan"), float("nan")
    try:
        info = sf.info(str(path))
        seconds = info.frames / info.samplerate
        kbps = path.stat().st_size * 8.0 / seconds / 1000.0
        data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    try:
        run, _ = side_dead_run(data, int(rate))
    except Exception:
        run = float("nan")
    mono = np.ascontiguousarray(data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float32)
    try:
        seam, _ = temporal_seam(mono, int(rate))
    except Exception:
        seam = float("nan")

    def f(x, nd=2):
        return f"{x:.{nd}f}" if isinstance(x, (int, float)) and np.isfinite(x) else "nan"

    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "engine_version": __version__,
        "score": result["score"],
        "verdict": result["verdict"],
        "evidence_families": "+".join(result.get("evidence_families", [])),
        "score_breakdown": json.dumps(result.get("score_breakdown", {}), separators=(",", ":")),
        "hires_verdict": result.get("hires_verdict", ""),
        "sample_rate": result.get("sample_rate", ""),
        "bit_depth": result.get("bit_depth", ""),
        "cutoff_hz": f(cutoff, 1),
        "cutoff_std_hz": f(std, 1),
        "energy_ratio": f"{energy:.3e}" if np.isfinite(energy) else "nan",
        "residual_floor_db": f(resid, 1),
        "container_kbps": f(kbps, 0),
        "stereo_run": f(run, 2),
        "seam": f(seam, 3),
    }


def idem_columns(path: Path, ffmpeg: str) -> Optional[dict]:
    from idem_phase_probe import CANONICAL, crop
    from mp3_idem_probe import mp3_idem

    try:
        info = sf.info(str(path))
        data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if rate not in (44100, 48000):
        return {
            "file": path.name,
            "idem_R_phase0": "nan",
            "idem_R_best_canonical": "nan",
            "idem_best_phase": "",
        }
    reads = {}
    for k in CANONICAL:
        try:
            r, _, _ = mp3_idem(crop(data, k), int(rate), ffmpeg)
        except Exception:
            r = float("nan")
        reads[k] = r
    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
    best = min(finite, key=lambda k: finite[k]) if finite else None
    return {
        "file": path.name,
        "idem_R_phase0": f"{reads[0]:.2f}" if np.isfinite(reads[0]) else "nan",
        "idem_R_best_canonical": f"{finite[best]:.2f}" if best is not None else "nan",
        "idem_best_phase": best if best is not None else "",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--idem", action="store_true", help="the idem pass instead of the engine pass"
    )
    parser.add_argument("--limit", type=int, default=0, help="smoke test on the first N files")
    args = parser.parse_args(argv)
    out = Path(args.out)
    files = sorted(AUDIO.glob("*.flac"))
    if len(files) != 590:
        raise SystemExit(f"expected 590 files, found {len(files)}")
    if args.limit:
        files = files[: args.limit]

    done = set()
    if out.exists():
        with open(out, newline="", encoding="utf-8") as fh:
            done = {r["file"] for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    if args.idem:
        from mp3_idem_probe import require_ffmpeg

        ffmpeg = require_ffmpeg()
        fields = ["file", "idem_R_phase0", "idem_R_best_canonical", "idem_best_phase"]
        analyzer = None
    else:
        from flac_detective.analysis.analyzer import FLACAnalyzer

        analyzer = FLACAnalyzer(deep=True)
        fields = [
            "file",
            "bytes",
            "engine_version",
            "score",
            "verdict",
            "evidence_families",
            "score_breakdown",
            "hires_verdict",
            "sample_rate",
            "bit_depth",
            "cutoff_hz",
            "cutoff_std_hz",
            "energy_ratio",
            "residual_floor_db",
            "container_kbps",
            "stereo_run",
            "seam",
        ]

    with open(out, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not done:
            writer.writeheader()
        for i, path in enumerate(files, 1):
            if path.name in done:
                continue
            row = (
                idem_columns(path, ffmpeg) if args.idem else engine_and_measurements(path, analyzer)
            )
            if row is None:
                continue
            writer.writerow(row)
            fh.flush()
            if i % 10 == 0 or i == 590:
                print(f"  {i}/590", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
