#!/usr/bin/env python3
"""Recalibration analysis for the verdict thresholds, focused on the wide WARNING
band. Reads score_distribution.csv (label, codec, src_bucket, score, verdict) and
asks whether the cut points — AUTHENTIC <=30, WARNING 31-60, SUSPICIOUS 61-85,
FAKE_CERTAIN >=86 — sit where the two populations actually separate.

We do NOT change thresholds here — this prints the evidence and a recommendation;
moving user-facing thresholds is a deliberate call.

    .venv/Scripts/python.exe ml/analyze_warning_band.py --csv ml/score_distribution.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Current thresholds (constants.py): AUTHENTIC<=30, WARNING 31-60, SUSP 61-85, FAKE>=86
AUTH, SUSP, FAKE = 30, 61, 86


def verdict(score: int) -> str:
    if score >= FAKE:
        return "FAKE_CERTAIN"
    if score >= SUSP:
        return "SUSPICIOUS"
    if score > AUTH:
        return "WARNING"
    return "AUTHENTIC"


def dist(scores, edges=(0, 31, 61, 86, 1000)):
    names = ["AUTHENTIC(0-30)", "WARNING(31-60)", "SUSPICIOUS(61-85)", "FAKE(86+)"]
    out = []
    for i, n in enumerate(names):
        lo, hi = edges[i], edges[i + 1]
        c = sum(lo <= s < hi for s in scores)
        out.append(f"{n}={c} ({c/max(len(scores),1):.0%})")
    return "  ".join(out)


def main(csv_path: Path) -> int:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for r in rows:
        r["score"] = int(r["score"])
    auth = [r["score"] for r in rows if r["kind"] == "authentic"]
    trans = [r["score"] for r in rows if r["kind"] == "transcode"]
    log.info(f"{len(rows)} files: {len(auth)} authentic, {len(trans)} transcode")

    log.info("\n=== Verdict distribution (current thresholds) ===")
    log.info(f"  AUTHENTICS : {dist(auth)}")
    log.info(f"  TRANSCODES : {dist(trans)}")

    log.info("\n=== Score percentiles ===")
    for lbl, sc in [("authentic", auth), ("transcode", trans)]:
        if sc:
            ps = {p: int(np.percentile(sc, p)) for p in (10, 25, 50, 75, 90, 95, 99)}
            log.info(f"  {lbl:>10}: " + "  ".join(f"p{p}={v}" for p, v in ps.items()))

    # The WARNING-band question: who sits in 31-60?
    aw = [s for s in auth if AUTH < s < SUSP]
    tw = [s for s in trans if AUTH < s < SUSP]
    log.info(f"\n=== Who is in the WARNING band (31-60)? ===")
    log.info(f"  authentics in WARNING: {len(aw)} ({len(aw)/max(len(auth),1):.0%} of authentics)")
    log.info(f"  transcodes in WARNING: {len(tw)} ({len(tw)/max(len(trans),1):.0%} of transcodes)")

    # Sweep the WARNING/SUSPICIOUS cut: how recall (transcodes>=cut) and authentic
    # false-SUSPICIOUS (authentics>=cut) move. Lower cut = more actionable but more FP.
    log.info("\n=== Moving the SUSPICIOUS floor (currently 61) ===")
    log.info(f"{'cut':>4} | {'transcodes >= cut':>17} | {'authentics >= cut (FP)':>22}")
    for cut in (45, 50, 55, 61, 66, 70):
        tr = sum(s >= cut for s in trans) / max(len(trans), 1)
        fp = sum(s >= cut for s in auth) / max(len(auth), 1)
        log.info(f"{cut:>4} | {tr:>16.0%} | {fp:>21.0%}")

    # And the AUTHENTIC ceiling (currently 30): authentics below = correctly clean.
    log.info("\n=== Moving the AUTHENTIC ceiling (currently 30) ===")
    log.info(f"{'cut':>4} | {'authentics <= cut (clean)':>25} | {'transcodes <= cut (missed)':>26}")
    for cut in (20, 25, 30, 35, 40):
        a = sum(s <= cut for s in auth) / max(len(auth), 1)
        m = sum(s <= cut for s in trans) / max(len(trans), 1)
        log.info(f"{cut:>4} | {a:>24.0%} | {m:>25.0%}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/score_distribution.csv")
    args = p.parse_args()
    sys.exit(main(Path(args.csv)))
