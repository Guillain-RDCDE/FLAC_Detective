#!/usr/bin/env python3
"""The re-mastered arm: price every family against the population the wild sells.

Why this arm exists
-------------------
The W-series (2026-08-21) measured the first lab-to-wild gap: the engine signals
68–100 % per arm on lab-made DIRECT transcodes and 8.8 % on owner-attested wild
320s that passed through a mastering chain (MP3 decode → DJ mix, levels,
crossfades → CD press → rip). MP3_IDEM told us why: the chain pushes the audio
clean off the codec fixed point (wild median R 3.18 vs direct 0.89). The lab
bench had no arm for that population, so every published rate silently described
direct transcodes only. This file builds the missing arm and re-prices the
families on it.

The simulated chain, v1 (registered before any measurement)
-----------------------------------------------------------
ffmpeg, applied to the DECODED direct transcode, back to FLAC s16:

    equalizer f=60  g=+2.0 (q 1.0)   — bass ride, DJ-desk style
    equalizer f=8000 g=+1.5 (q 1.5)  — presence lift
    dynaudnorm f=250:g=15            — program-dependent level rides
    alimiter  limit=0.97             — brickwall limiter into the press
    aresample + s16 dither           — the CD master step

Acceptance, registered BEFORE the simulated arm is measured — the validator is
the wild53 signature, a KNOWN ANSWER measured on real bytes:

    A1  The shipped engine (deep) signals <= 20 % of the re-mastered arm
        (wild reads 8.8 %).
    A2  MP3_IDEM median R on the re-mastered arm lands in [2.3, 3.8]
        (wild reads 3.18; genuine 2.73; direct 0.89).
    A3  The SAME engine run signals >= 60 % of the direct arm — the contrast
        is the measurement; without A3 the arm proves nothing.

If A1/A2 fail on chain v1, ONE strengthened v2 is permitted and must be
described here; if v2 fails too, the honest result is "the simulator cannot
reproduce the wild signature" and the real chain contains something this file
does not model — reported as such, never tuned until it passes.

Results are appended below AFTER the runs; the registrations above stay.
--------------------------------------------------------------------------------
(not yet run)

Usage::

    python ml/remaster_arm.py --build     # construct the re-mastered arm
    python ml/remaster_arm.py --measure   # engine + families on all 3 populations
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mp3_idem_probe import mp3_idem, require_ffmpeg  # noqa: E402
from edge_width_probe import auc  # noqa: E402

AUDIT = Path(r"C:\Users\loutr\audit_corpus")
OUT = Path(r"C:\Users\loutr\remaster_arm")
LIMIT = 40

CHAIN_V1 = (
    "equalizer=f=60:t=q:w=1:g=2,"
    "equalizer=f=8000:t=q:w=1.5:g=1.5,"
    "dynaudnorm=f=250:g=15,"
    "alimiter=limit=0.97"
)

IDEM_BAR = 1.68
SEAM_BAR = 0.60
RUN_BAR = 2.0
RATIO_REVIEW = 2.0

POPULATIONS = {
    "genuine": AUDIT / "authentic",
    "direct": AUDIT / "fake" / "mp3_320",
    "remastered": OUT,
}


def build(ffmpeg: str) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted((AUDIT / "fake" / "mp3_320").glob("*.flac"))[:LIMIT]
    made = 0
    for src in sources:
        dst = OUT / src.name
        if dst.exists():
            made += 1
            continue
        r = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-af",
                CHAIN_V1,
                "-c:a",
                "flac",
                "-sample_fmt",
                "s16",
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            made += 1
        else:
            print(f"  chain failed: {src.name}: {r.stderr.strip()[-200:]}")
    print(f"re-mastered arm: {made}/{len(sources)} files in {OUT}")
    return 0


def measure(out_csv: Path) -> List[dict]:
    from flac_detective import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer
    from flac_detective.analysis.new_scoring.mdct import best_alignment_stat
    from flac_detective.analysis.new_scoring.stereo_image import side_dead_run
    from flac_detective.analysis.new_scoring.temporal import temporal_seam

    ffmpeg = require_ffmpeg()
    done: Dict[str, dict] = {}
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done[(row["population"], row["track"])] = row
        print(f"reprise: {len(done)} deja mesures", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    fieldnames = [
        "population",
        "track",
        "engine_version",
        "verdict",
        "score",
        "families",
        "idem_R",
        "mdct",
        "stereo_run",
        "seam",
    ]
    rows: List[dict] = list(done.values())
    with open(out_csv, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for population, folder in POPULATIONS.items():
            paths = sorted(folder.glob("*.flac"))[:LIMIT]
            n = 0
            for path in paths:
                if (population, path.name) in done:
                    n += 1
                    continue
                row: dict = {
                    "population": population,
                    "track": path.name,
                    "engine_version": __version__,
                }
                try:
                    result = analyzer.analyze_file(str(path))
                    row["verdict"] = result["verdict"]
                    row["score"] = result["score"]
                    row["families"] = "+".join(sorted(result.get("evidence_families") or []))
                except Exception as exc:
                    print(f"  engine failed {path.name}: {exc}", flush=True)
                    row.update({"verdict": "ERROR", "score": "", "families": ""})
                try:
                    info = sf.info(str(path))
                    data, rate = sf.read(
                        str(path), dtype="float32", frames=int(60 * info.samplerate)
                    )
                    r_db, _, _ = mp3_idem(data, int(rate), ffmpeg)
                    row["idem_R"] = f"{r_db:.3f}" if np.isfinite(r_db) else "nan"
                    mono = np.ascontiguousarray(
                        data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float32
                    )
                    mdct_stat, _, _ = best_alignment_stat(mono, int(rate), stop_at=float("inf"))
                    row["mdct"] = f"{mdct_stat:.3f}"
                    try:
                        run, _ = side_dead_run(data, int(rate))
                        row["stereo_run"] = f"{run:.2f}" if np.isfinite(run) else "nan"
                    except Exception:
                        row["stereo_run"] = "nan"
                    seam, _ = temporal_seam(mono, int(rate))
                    row["seam"] = f"{seam:.3f}" if np.isfinite(seam) else "nan"
                except Exception as exc:
                    print(f"  stats failed {path.name}: {exc}", flush=True)
                    for key in ("idem_R", "mdct", "stereo_run", "seam"):
                        row.setdefault(key, "nan")
                writer.writerow(row)
                fh.flush()
                rows.append(row)
                n += 1
                print(
                    f"  [{population} {n}/{len(paths)}] {path.name}  {row['verdict']}", flush=True
                )
            print(f"{population}: {n} mesures", flush=True)
    return rows


def _vals(rows: List[dict], population: str, key: str) -> np.ndarray:
    out = []
    for r in rows:
        if r["population"] == population:
            try:
                v = float(r[key])
                if np.isfinite(v):
                    out.append(v)
            except (TypeError, ValueError):
                pass
    return np.array(out)


def report(rows: List[dict]) -> None:
    def signaled(population: str) -> int:
        return sum(
            1
            for r in rows
            if r["population"] == population and r["verdict"] not in ("AUTHENTIC", "ERROR")
        )

    def count(population: str) -> int:
        return sum(1 for r in rows if r["population"] == population)

    print("\n" + "=" * 76)
    print("THE TWO-COLUMN TABLE — direct vs re-mastered (wild53 shown as reference)")
    print("=" * 76)

    n_g, n_d, n_r = count("genuine"), count("direct"), count("remastered")
    s_d, s_r = signaled("direct"), signaled("remastered")
    print(
        f"\nengine signaled: direct {s_d}/{n_d} = {100*s_d/max(n_d,1):.0f} %"
        f"   remastered {s_r}/{n_r} = {100*s_r/max(n_r,1):.0f} %"
        f"   (wild53 owner tier: 8.8 %)"
    )

    print(f"\n{'family':12}{'direct AUC':>12}{'fire':>7}{'remast AUC':>12}{'fire':>7}")
    bars = {
        "idem_R": ("low", IDEM_BAR),
        "mdct": ("high", RATIO_REVIEW),
        "stereo_run": ("high", RUN_BAR),
        "seam": ("high", SEAM_BAR),
    }
    for key, (direction, bar) in bars.items():
        gen = _vals(rows, "genuine", key)
        line = f"{key:12}"
        for population in ("direct", "remastered"):
            vals = _vals(rows, population, key)
            if not vals.size or not gen.size:
                line += f"{'—':>12}{'—':>7}"
                continue
            if direction == "low":
                a = auc(-vals, -gen)
                fire = int((vals <= bar).sum())
            else:
                a = auc(vals, gen)
                fire = int((vals >= bar).sum())
            line += f"{a:>12.2f}{100*fire/vals.size:>6.0f}%"
        print(line)

    idem_r = _vals(rows, "remastered", "idem_R")
    a1 = s_r <= 0.20 * max(n_r, 1)
    a2 = idem_r.size and 2.3 <= float(np.median(idem_r)) <= 3.8
    a3 = s_d >= 0.60 * max(n_d, 1)
    print(
        f"\nA1 engine <=20 % on remastered: {'HELD' if a1 else 'FAILED'}"
        f" ({100*s_r/max(n_r,1):.0f} %)"
    )
    print(
        f"A2 idem median in [2.3, 3.8]:   {'HELD' if a2 else 'FAILED'}"
        f" (median {np.median(idem_r):.2f})"
        if idem_r.size
        else "A2 no idem readings"
    )
    print(
        f"A3 engine >=60 % on direct:     {'HELD' if a3 else 'FAILED'}"
        f" ({100*s_d/max(n_d,1):.0f} %)"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("ml/remaster_arm.csv"))
    args = parser.parse_args(argv)

    if args.build:
        return build(require_ffmpeg())
    if args.measure:
        rows = measure(args.out)
        report(rows)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
