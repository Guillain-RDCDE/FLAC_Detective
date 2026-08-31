#!/usr/bin/env python3
"""Attribution, layer two: a calibrated null, a held-out set, and an abstention rule.

Predictions B1-B5 registered first, before this ran, in
``ml/exchange/ATTRIBUTION_V2_REGISTRATION_2026-08-31.md``.

Layer one compared raw R across five probes as though one scale fitted all of
them; the twolame probe won 22 of 60 lossy files by sitting lower than the
others. Centring each probe on its own genuine median fixed that — but on the
same twelve files the calibration came from, which is not a measurement.

Here the calibration comes from files 1-12 (already measured, layer one's data)
and the evaluation from files 13-24 and their arms, which this instrument has
never seen. The abstention rule and both its constants are frozen by the
registration:

    attribute to argmin(z) ONLY IF min(z) <= -1.0 AND second(z) - min(z) >= 1.0
    otherwise abstain

Usage::

    python ml/attribution_v2_probe.py --out ml/attribution_v2_probe.csv
    python ml/attribution_v2_probe.py --score ml/attribution_v2_probe.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from attribution_probe import CORPUS, PROBES, read_file, require_ffmpeg  # noqa: E402

CALIBRATION_CSV = Path(__file__).resolve().parent / "attribution_probe.csv"
HELD_OUT = slice(12, 24)  # files 13-24 of each population, never measured before

# Frozen by the registration, derived from the calibration set's geometry and
# not from the held-out files.
Z_FIRE = -1.0
Z_MARGIN = 1.0

POPULATIONS: Tuple[Tuple[str, str], ...] = (
    ("authentic", ""),
    ("fake/mp3_320", "mp3"),
    ("fake/aac_ff256", "aac"),
    ("fake/aacmf_256", "aac"),
    ("fake/opus_256", "opus"),
    ("fake/vorbis_q8", "vorbis"),
)

FAMILIES = [p[0] for p in PROBES]
FIELDS = ["file", "population", "expected", "attributed", "min_z", "margin"] + [
    f"R_{f}" for f in FAMILIES
]


def calibration() -> Dict[str, Tuple[float, float]]:
    """(median, spread) per probe, from the GENUINE rows of layer one only."""
    with open(CALIBRATION_CSV, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["population"] == "authentic"]
    if not rows:
        raise SystemExit(f"no genuine rows in {CALIBRATION_CSV}; run layer one first")
    out: Dict[str, Tuple[float, float]] = {}
    for family in FAMILIES:
        values = [float(r[f"R_{family}"]) for r in rows if np.isfinite(float(r[f"R_{family}"]))]
        spread = float(np.std(values)) if len(values) > 1 else float("nan")
        out[family] = (float(np.median(values)), spread if spread > 0 else 1.0)
    return out


def attribute(
    reads: Dict[str, float], null: Dict[str, Tuple[float, float]]
) -> Tuple[str, float, float]:
    """(family or 'abstain', min z, margin to the runner-up)."""
    zs = {}
    for family in FAMILIES:
        value = reads.get(f"R_{family}", float("nan"))
        if not np.isfinite(value):
            continue
        median, spread = null[family]
        zs[family] = (value - median) / spread
    if len(zs) < 2:
        return "abstain", float("nan"), float("nan")
    ordered = sorted(zs.items(), key=lambda kv: kv[1])
    best, best_z = ordered[0]
    margin = ordered[1][1] - best_z
    if best_z <= Z_FIRE and margin >= Z_MARGIN:
        return best, best_z, margin
    return "abstain", best_z, margin


def run(out_path: Path) -> int:
    ffmpeg = require_ffmpeg()
    null = calibration()
    print(
        "null (median, spread) par sonde:",
        {k: (round(v[0], 2), round(v[1], 2)) for k, v in null.items()},
    )

    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["population"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for population, expected in POPULATIONS:
            files = sorted((CORPUS / population).glob("*.flac"))[HELD_OUT]
            for index, path in enumerate(files, 1):
                if (path.name, population) in done:
                    continue
                reads = read_file(path, ffmpeg)
                family, min_z, margin = attribute(reads, null)
                writer.writerow(
                    {
                        "file": path.name,
                        "population": population,
                        "expected": expected,
                        "attributed": family,
                        "min_z": f"{min_z:.3f}",
                        "margin": f"{margin:.3f}",
                        **{k: f"{v:.4f}" for k, v in reads.items()},
                    }
                )
                fh.flush()
                print(f"  {population} {index}/{len(files)} -> {family}", flush=True)
    print(f"ecrit {out_path}")
    return 0


def score(csv_path: Path) -> int:
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    if not rows:
        print("csv vide")
        return 1
    held: Dict[str, bool] = {}
    genuine = [r for r in rows if r["population"] == "authentic"]
    lossy = [r for r in rows if r["expected"]]

    attributed_genuine = [r for r in genuine if r["attributed"] != "abstain"]
    held["B1"] = len(attributed_genuine) <= 2
    print(
        f"B1 genuine attribues au lieu de s'abstenir: {len(attributed_genuine)}/{len(genuine)} "
        f"(borne 2) {'TENU' if held['B1'] else 'ECHEC'}"
    )

    for name, population, family in (
        ("B2", "fake/mp3_320", "mp3"),
        ("B3", "fake/opus_256", "opus"),
    ):
        sub = [r for r in rows if r["population"] == population]
        hits = sum(1 for r in sub if r["attributed"] == family)
        held[name] = hits >= 10
        print(
            f"{name} {population} -> {family}: {hits}/{len(sub)} (borne 10) "
            f"{'TENU' if held[name] else 'ECHEC'}"
        )

    hard = [
        r for r in rows if r["population"] in ("fake/aac_ff256", "fake/aacmf_256", "fake/vorbis_q8")
    ]
    abstained = sum(1 for r in hard if r["attributed"] == "abstain")
    held["B4"] = abstained > len(hard) - abstained
    print(
        f"B4 s'abstient plus qu'il n'attribue sur AAC/Vorbis: {abstained} abstentions contre "
        f"{len(hard) - abstained} attributions {'TENU' if held['B4'] else 'ECHEC'}"
    )

    mp2 = sum(1 for r in lossy if r["attributed"] == "mp2")
    held["B5"] = mp2 <= 2
    print(
        f"B5 Layer II par accident: {mp2}/{len(lossy)} (borne 2) {'TENU' if held['B5'] else 'ECHEC'}"
    )

    print("\nmatrice (lignes = verite, colonnes = attribue):")
    cols = FAMILIES + ["abstain"]
    print(f"{'population':18s} " + " ".join(f"{c:>8s}" for c in cols))
    for population, _ in POPULATIONS:
        sub = [r for r in rows if r["population"] == population]
        if not sub:
            continue
        counts = {c: sum(1 for r in sub if r["attributed"] == c) for c in cols}
        print(f"{population:18s} " + " ".join(f"{counts[c]:8d}" for c in cols))

    failed = [k for k, v in held.items() if not v]
    print("\n" + ("TOUT TENU" if not failed else "ECHECS: " + ", ".join(failed)))
    return 0 if not failed else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--score", type=Path)
    args = ap.parse_args(argv)
    if args.score:
        return score(args.score)
    if not args.out:
        ap.error("--out ou --score")
    return run(args.out)


if __name__ == "__main__":
    sys.exit(main())
