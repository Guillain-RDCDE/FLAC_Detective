#!/usr/bin/env python3
"""Rule 13 recertification, restated on the population the rule can actually read.

The debt this pays
------------------
``ml/admission_audit.md`` (2026-08-20): the 877-file recertification behind
``CERTIFIED_GENUINE_P999 = 1.614`` measured every certified file with no cutoff
filter, while ``should_run_rule_13`` refuses anything under 18 kHz — and 17 of
258 genuine files in the audit+wild corpora sit under that floor. The species is
the week's: *a statistic computed across a population the rule cannot read.*

This pass does NOT re-measure the MDCT statistic — ``ml/recert_880.csv`` already
carries both hypotheses per file. It measures the one thing that CSV lacks, the
per-file cutoff, joins on the recert's own key (sha1(normpath)[:16], recovered by
matching all 80 audit paths and all 797 library paths exactly), and publishes the
tail quantiles twice: all-certified, and admitted-only. The standing rule from
the audit: calibrate on the admitted population, or state why the superset is
safe — this measures which.

Output CSV carries path_hash, cutoff and admission only — no paths, no titles.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import (  # noqa: E402
    _welch_magnitude_db,
    detect_cutoff,
)
from flac_detective.analysis.new_scoring.rules.mdct_alignment import (  # noqa: E402
    MIN_CUTOFF_HZ,
    RATIO_HARD,
    RATIO_REVIEW,
)
from flac_detective.analysis.new_scoring.mdct import (  # noqa: E402
    CERTIFIED_GENUINE_P999,
)

EXCERPT_SEC = 30.0


def path_hash(p: str) -> str:
    return hashlib.sha1(os.path.normpath(p).encode()).hexdigest()[:16]


def build_hash_map() -> Dict[str, str]:
    """path_hash -> path, for the audit corpus and the certified library."""
    mapping: Dict[str, str] = {}
    for p in glob.glob("C:/Users/loutr/audit_corpus/authentic/*.flac"):
        mapping[path_hash(p)] = p
    lib = json.load(open("ml/authentic_files.json", encoding="utf-8"))
    for entry in lib["files"]:
        p = entry["path"]
        mapping[path_hash(p)] = p
    return mapping


def measure_cutoff(path: str) -> Optional[float]:
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0:
        return None
    mono = np.asarray(data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float64)
    try:
        freq, mag = _welch_magnitude_db(mono, rate)
        if freq is None:
            return None
        return float(detect_cutoff(freq, mag, rate))
    except Exception:
        return None


def collect(out_path: Path) -> List[dict]:
    recert = list(csv.DictReader(open("ml/recert_880.csv", newline="", encoding="utf-8")))
    mapping = build_hash_map()

    done: Dict[str, dict] = {}
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done[row["path_hash"]] = row
        print(f"reprise: {len(done)} deja mesures", flush=True)

    fieldnames = ["path_hash", "source", "ratio_max", "cutoff", "admitted"]
    rows: List[dict] = list(done.values())
    missing = 0
    with open(out_path, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for index, r in enumerate(recert, 1):
            key = r["path_hash"]
            if key in done:
                continue
            path = mapping.get(key)
            if path is None:
                missing += 1
                continue
            cutoff = measure_cutoff(path)
            if cutoff is None:
                missing += 1
                continue
            row = {
                "path_hash": key,
                "source": r["source"],
                "ratio_max": r["ratio_max"],
                "cutoff": f"{cutoff:.1f}",
                "admitted": int(cutoff >= MIN_CUTOFF_HZ),
            }
            writer.writerow(row)
            fh.flush()
            rows.append(row)
            if index % 50 == 0:
                print(f"  {index}/{len(recert)}", flush=True)
    if missing:
        print(f"{missing} fichiers introuvables/illisibles (retires, pas moyennes)", flush=True)
    return rows


def quantiles(values: np.ndarray) -> str:
    return (
        f"n={values.size}  median {np.median(values):.3f}  "
        f"p99 {np.percentile(values, 99):.3f}  "
        f"p99.9 {np.percentile(values, 99.9):.3f}  max {values.max():.3f}"
    )


def report(rows: List[dict]) -> None:
    ratio = np.array([float(r["ratio_max"]) for r in rows])
    admitted = np.array([int(r["admitted"]) for r in rows], dtype=bool)
    print("\n" + "=" * 74)
    print("RULE 13 TAIL, twice: all-certified vs the population the rule reads")
    print("=" * 74)
    print(f"\nall certified   {quantiles(ratio)}")
    print(f"admitted only   {quantiles(ratio[admitted])}")
    print(f"\nadmission floor {MIN_CUTOFF_HZ:.0f} Hz: "
          f"{int((~admitted).sum())}/{len(rows)} certified files "
          f"({100 * (~admitted).mean():.1f} %) are ones the rule never reads")
    print(f"\npublished CERTIFIED_GENUINE_P999 = {CERTIFIED_GENUINE_P999}")
    for name, bar in (("review", RATIO_REVIEW), ("hard", RATIO_HARD)):
        for label, vals in (("all", ratio), ("admitted", ratio[admitted])):
            k = int((vals >= bar).sum())
            print(f"  exceedance of {name} bar ({bar}) on {label:9}: "
                  f"{k}/{vals.size} = {100 * k / vals.size:.2f} %")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("ml/recert_admission.csv"))
    args = parser.parse_args(argv)
    rows = collect(args.out)
    print(f"\n{len(rows)} lignes -> {args.out}", flush=True)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
