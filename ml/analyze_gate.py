#!/usr/bin/env python3
"""Analyse gate_testset.csv to answer two questions:

(a) THRESHOLD COST — if we raise Rule-12's decision threshold from 0.5, how much
    transcode recall do we lose? Reported overall, per codec, and per source
    rolloff bucket (the loss should concentrate in band-limited sources, where
    transcodes are near-undetectable anyway).

(b) ABSTENTION GATE — among files the model flags (p>=0.5), can a heuristic
    signal separate the genuine transcodes (keep flagging) from the band-limited
    authentic false positives (abstain)? We sweep a threshold on each candidate
    signal and report, for each operating point: authentic-FP removed (good) vs
    transcode true-positives lost (bad).

Pure CSV analysis, no audio. Run after build_gate_testset.py:
    .venv/Scripts/python.exe ml/analyze_gate.py --csv ml/gate_testset.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

BUCKETS = ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]
THRESHOLDS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.8]


def load(csv_path: Path) -> list[dict]:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for r in rows:
        r["p"] = float(r["p_transcoded"])
        r["is_t"] = r["is_transcode"] == "1"
        r["comp"] = float(r["comp_ratio"])
        r["energy"] = float(r["energy_ratio"])
        r["cutoff"] = float(r["cutoff_freq"])
        r["br"] = float(r["real_bitrate_kbps"])
    return rows


def threshold_cost(rows: list[dict]) -> None:
    trans = [r for r in rows if r["is_t"]]
    auth = [r for r in rows if not r["is_t"]]
    log.info("=" * 70)
    log.info(f"(a) THRESHOLD COST  —  {len(trans)} transcodes, {len(auth)} authentics")
    log.info("-" * 70)
    log.info(f"{'thr':>5} | {'trans recall':>12} | {'auth specificity':>16} | {'balanced':>9}")
    for t in THRESHOLDS:
        rec = sum(r["p"] >= t for r in trans) / len(trans)
        spec = sum(r["p"] < t for r in auth) / len(auth)
        log.info(f"{t:>5} | {rec:>11.1%} | {spec:>15.1%} | {(rec + spec) / 2:>8.1%}")

    log.info("-" * 70)
    log.info("Transcode recall @0.5 vs @0.6, per codec:")
    by_codec: dict[str, list[dict]] = defaultdict(list)
    for r in trans:
        by_codec[r["kind"]].append(r)
    for codec, items in sorted(by_codec.items()):
        r5 = sum(r["p"] >= 0.5 for r in items) / len(items)
        r6 = sum(r["p"] >= 0.6 for r in items) / len(items)
        log.info(f"  {codec:>8}: @0.5={r5:6.1%}  @0.6={r6:6.1%}  (n={len(items)})")

    log.info("-" * 70)
    log.info("Transcode recall @0.5 vs @0.6, per SOURCE rolloff bucket:")
    by_b: dict[str, list[dict]] = defaultdict(list)
    for r in trans:
        by_b[r["src_rolloff_bucket"]].append(r)
    for b in BUCKETS:
        items = by_b.get(b, [])
        if not items:
            continue
        r5 = sum(r["p"] >= 0.5 for r in items) / len(items)
        r6 = sum(r["p"] >= 0.6 for r in items) / len(items)
        log.info(f"  {b:>7}: @0.5={r5:6.1%}  @0.6={r6:6.1%}  (n={len(items)})")


def gate_eval(rows: list[dict]) -> None:
    # Population the gate acts on: everything the model FLAGS at 0.5.
    flagged = [r for r in rows if r["p"] >= 0.5]
    fp = [r for r in flagged if not r["is_t"]]  # authentic, wrongly flagged -> want to drop
    tp = [r for r in flagged if r["is_t"]]  # transcode, correctly flagged -> want to keep
    log.info("\n" + "=" * 70)
    log.info(
        f"(b) ABSTENTION GATE  —  among {len(flagged)} model-flagged files: "
        f"{len(fp)} authentic-FP (drop), {len(tp)} transcode-TP (keep)"
    )

    # Candidate signals. For comp_ratio / bitrate: authentics compress BETTER
    # (lower), so gate = "abstain if signal < tau". For energy/cutoff: authentics
    # band-limited have low values too -> same direction. We sweep and report.
    log.info("-" * 70)
    log.info("Separation (median authentic-FP vs transcode-TP):")
    import statistics as st

    for key, label in [
        ("comp", "comp_ratio"),
        ("br", "real_bitrate"),
        ("energy", "energy_ratio"),
        ("cutoff", "cutoff_freq"),
    ]:
        if fp and tp:
            log.info(
                f"  {label:>13}: FP med={st.median(r[key] for r in fp):.4g}  "
                f"TP med={st.median(r[key] for r in tp):.4g}"
            )

    # Sweep comp_ratio gate: abstain (drop the flag) if comp < tau.
    log.info("-" * 70)
    log.info("comp_ratio gate — abstain if comp_ratio < tau:")
    log.info(f"{'tau':>6} | {'auth-FP dropped':>15} | {'trans-TP lost':>13}")
    cmin = min((r["comp"] for r in flagged if r["comp"] > 0), default=0.5)
    cmax = max((r["comp"] for r in flagged), default=1.0)
    steps = [cmin + (cmax - cmin) * i / 12 for i in range(1, 12)]
    for tau in steps:
        dropped = sum(1 for r in fp if 0 < r["comp"] < tau) / len(fp) if fp else 0
        lost = sum(1 for r in tp if 0 < r["comp"] < tau) / len(tp) if tp else 0
        log.info(f"{tau:>6.3f} | {dropped:>14.1%} | {lost:>12.1%}")


def main(csv_path: Path) -> int:
    if not csv_path.is_file():
        log.error(f"Not found: {csv_path}")
        return 1
    rows = load(csv_path)
    log.info(f"Loaded {len(rows)} rows from {csv_path.name}")
    threshold_cost(rows)
    gate_eval(rows)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/gate_testset.csv")
    args = p.parse_args()
    sys.exit(main(Path(args.csv)))
