#!/usr/bin/env python3
"""Price Rule 15's domain gate — the before/after pass for T1 to T5.

Criteria registered first in
``ml/exchange/R15_DOMAIN_GATE_REGISTRATION_2026-08-31.md``.

Three populations, run with the full engine:

    band-limited   44 parked genuine sources + the 14 kHz roll-off — the artefact
    high-rate      mp3_320, aac_ff256, opus_256, vorbis_q8 — none below the gate
    low-rate       mp3_192, aac_ff128 — where the gate genuinely bites (T4)

Set A's own 288 files are priced separately by ``ml/run_engine_on_set.py``.

Usage::

    python ml/r15_gate_pass.py --out ml/r15_gate_before.csv     # on the old constant
    python ml/r15_gate_pass.py --out ml/r15_gate_after.csv      # on the new one
    python ml/r15_gate_pass.py --compare ml/r15_gate_before.csv ml/r15_gate_after.csv
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CORPUS = Path(r"C:\Users\loutr\audit_corpus")
PARKED = (
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_unused"),
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_dup_series"),
)
HIGH_RATE = ("mp3_320", "aac_ff256", "opus_256", "vorbis_q8")
LOW_RATE = ("mp3_192", "aac_ff128")
N_PER_ARM = 40

FIELDS = ["file", "population", "verdict", "score", "evidence_families", "stereo_witness"]


def populations() -> List[tuple]:
    out: List[tuple] = []
    for arm in HIGH_RATE + LOW_RATE:
        for path in sorted((CORPUS / "fake" / arm).glob("*.flac"))[:N_PER_ARM]:
            out.append((path, arm, False))
    for folder in PARKED:
        for path in sorted(folder.glob("*.flac")):
            out.append((path, "bandlimited", True))
    return out


def run(out_path: Path) -> int:
    from v3_build_set_a import BAND_LIMIT_FILTER

    from flac_detective.analysis.analyzer import FLACAnalyzer

    items = populations()
    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["population"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} deja faits", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for index, (path, population, filtered) in enumerate(items, 1):
                if (path.name, population) in done:
                    continue
                target = path
                if filtered:
                    band = work / "bl.flac"
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-y",
                            "-i",
                            str(path),
                            "-map",
                            "0:a:0",
                            "-map_metadata",
                            "-1",
                            "-af",
                            BAND_LIMIT_FILTER,
                            "-ar",
                            "44100",
                            "-sample_fmt",
                            "s16",
                            "-c:a",
                            "flac",
                            str(band),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    target = band
                try:
                    result = analyzer.analyze_file(str(target))
                except Exception as exc:
                    print(f"  ECHEC {path.name}: {exc}", flush=True)
                    continue
                families = result.get("evidence_families") or []
                writer.writerow(
                    {
                        "file": path.name,
                        "population": population,
                        "verdict": result.get("verdict", ""),
                        "score": result.get("score", ""),
                        "evidence_families": "+".join(families),
                        "stereo_witness": int("stereo" in families),
                    }
                )
                fh.flush()
                if index % 25 == 0:
                    print(f"  {index}/{len(items)}", flush=True)
    print(f"ecrit {out_path}", flush=True)
    return 0


def compare(before_path: Path, after_path: Path) -> int:
    def load(path: Path) -> Dict[str, Dict[str, str]]:
        with open(path, newline="", encoding="utf-8") as fh:
            return {f"{r['population']}/{r['file']}": r for r in csv.DictReader(fh)}

    before, after = load(before_path), load(after_path)
    common = sorted(set(before) & set(after))
    print(f"{len(common)} fichiers communs\n")

    def convicted(row: Dict[str, str]) -> bool:
        return row["verdict"] == "FAKE_CERTAIN"

    def count(population: str, rows: Dict[str, Dict[str, str]]) -> int:
        return sum(
            1 for k in common if before[k]["population"] == population and convicted(rows[k])
        )

    held: Dict[str, bool] = {}
    b_band, a_band = count("bandlimited", before), count("bandlimited", after)
    held["T1"] = a_band <= 2
    print(
        f"T1 band-limited convictions: {b_band} -> {a_band} (borne 2) "
        f"{'TENU' if held['T1'] else 'ECHEC'}"
    )

    lost_high = sum(count(arm, before) - count(arm, after) for arm in HIGH_RATE)
    held["T3"] = lost_high <= 2
    print(
        f"T3 convictions perdues sur les bras haut debit: {lost_high} (borne 2) "
        f"{'TENU' if held['T3'] else 'ECHEC'}"
    )
    for arm in HIGH_RATE:
        print(f"     {arm:12s} {count(arm, before):3d} -> {count(arm, after):3d}")

    lost_low = sum(count(arm, before) - count(arm, after) for arm in LOW_RATE)
    print(f"T4 convictions perdues sur les bras bas debit (rapporte, non borne): {lost_low}")
    for arm in LOW_RATE:
        print(f"     {arm:12s} {count(arm, before):3d} -> {count(arm, after):3d}")

    wit_b = sum(1 for k in common if before[k]["stereo_witness"] == "1")
    wit_a = sum(1 for k in common if after[k]["stereo_witness"] == "1")
    print(f"\ntemoin stereo actif: {wit_b} -> {wit_a} fichiers")
    for population in ("bandlimited",) + HIGH_RATE + LOW_RATE:
        wb = sum(
            1
            for k in common
            if before[k]["population"] == population and before[k]["stereo_witness"] == "1"
        )
        wa = sum(
            1
            for k in common
            if before[k]["population"] == population and after[k]["stereo_witness"] == "1"
        )
        print(f"     {population:12s} {wb:3d} -> {wa:3d}")

    failed = [k for k, v in held.items() if not v]
    print("\n" + ("T1 ET T3 TENUS" if not failed else "ECHECS: " + ", ".join(failed)))
    return 0 if not failed else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"), type=Path)
    args = ap.parse_args(argv)
    if args.compare:
        return compare(*args.compare)
    if not args.out:
        ap.error("--out ou --compare")
    return run(args.out)


if __name__ == "__main__":
    sys.exit(main())
