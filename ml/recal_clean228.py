#!/usr/bin/env python3
"""RUN_BAR and SEAM_BAR re-verified on the genuine corpus PURGED of the 32.

The debt, declared before the run
----------------------------------
Every "258 genuine" calibration in this project included the 32 files the
2026-08-21 lineage audit exposed as taper-documented lossy (30 MiniDisc/ATRAC
Calexico + 2 internet-radio glenhansard), now adjudicated and quarantined. The
constants at risk are the two witness bars calibrated as genuine quantiles:
``RUN_BAR = 2.0`` (Rule 15, sat above the p95 of the mono-gate-admitted
genuine) and ``SEAM_BAR = 0.60`` (Rule 14, between p90 and p95 of 258).

Rule, registered before measurement: a constant changes ONLY if its bar falls
BELOW the clean population's p95 — i.e. only if the purge made the bar
under-protective. If the quarantined files were pulling the quantiles UP, the
shipped bars are more conservative than published (stated, not changed); if
they pulled them down materially, the bars must rise and that is a release.

Populations: clean = 80 audit-certified + the 148 remaining wild genuine
(= 228); quarantined = the 32, measured separately so the delta is explicit.

Results are appended below after the run.
--------------------------------------------------------------------------------
(not yet run)
"""

from __future__ import annotations

import argparse
import csv
import sys
from glob import glob
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.new_scoring.stereo_image import side_dead_run  # noqa: E402
from flac_detective.analysis.new_scoring.temporal import temporal_seam  # noqa: E402
from flac_detective.analysis.new_scoring.rules.stereo_seam import RUN_BAR  # noqa: E402
from flac_detective.analysis.new_scoring.rules.temporal_seam import SEAM_BAR  # noqa: E402

POPULATIONS = {
    "clean": [
        r"C:\Users\loutr\audit_corpus\authentic\*.flac",
        r"C:\Users\loutr\wild_authentic\*.flac",
    ],
    "quarantined": [r"C:\Users\loutr\wild_authentic_quarantine_md\*.flac"],
}
EXCERPT_SEC = 30.0


def measure(path: Path) -> Optional[dict]:
    try:
        info = sf.info(str(path))
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
    return {
        "track": path.name,
        "stereo_run": f"{run:.2f}" if np.isfinite(run) else "nan",
        "seam": f"{seam:.3f}" if np.isfinite(seam) else "nan",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("ml/recal_clean228.csv"))
    args = parser.parse_args(argv)

    rows: List[dict] = []
    for population, patterns in POPULATIONS.items():
        n = 0
        for pattern in patterns:
            for raw in sorted(glob(pattern)):
                row = measure(Path(raw))
                if row:
                    row["population"] = population
                    rows.append(row)
                    n += 1
        print(f"{population}: {n} mesures", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["population", "track", "stereo_run", "seam"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} lignes -> {args.out}\n")

    def vals(population: str, key: str) -> np.ndarray:
        out = np.array(
            [float(r[key]) for r in rows if r["population"] == population and r[key] != "nan"]
        )
        return out

    for key, bar, name in (("stereo_run", RUN_BAR, "RUN_BAR"), ("seam", SEAM_BAR, "SEAM_BAR")):
        clean = vals("clean", key)
        quar = vals("quarantined", key)
        both = np.concatenate([clean, quar])
        p95_clean = float(np.percentile(clean, 95))
        p95_both = float(np.percentile(both, 95))
        verdict = "BAR HOLDS" if bar >= p95_clean else "BAR UNDER-PROTECTIVE -> RAISE"
        print(f"{name} = {bar}")
        print(
            f"  clean n={clean.size}: p90 {np.percentile(clean, 90):.2f} "
            f"p95 {p95_clean:.2f} p99 {np.percentile(clean, 99):.2f}"
        )
        print(
            f"  with quarantined (old 'genuine'): p95 {p95_both:.2f}"
            f"   quarantined median {np.median(quar):.2f}"
            if quar.size
            else ""
        )
        print(f"  -> {verdict}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
