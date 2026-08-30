#!/usr/bin/env python3
"""Can the idem fixed point count GENERATIONS, not just detect one?

Predictions G1-G5 registered first, before this ran, in
``ml/exchange/GENERATION_COUNT_REGISTRATION_2026-08-30.md``. This file only
produces the numbers that document scores.

The idea in one line: if re-encoding converges to a fixed point, the distance to
that fixed point should fall with each generation, and the reading becomes *how
many times was this transcoded* rather than *was it*.

Two ladders, because a result that holds for one encoder is that encoder's habit:

    L — libmp3lame CBR 320   the probe's own codec (self-pairing)
    A — ffmpeg AAC 256       a different filterbank the probe does not share

Generation n is the decode of generation n-1 re-encoded: a real chain, not the
same master encoded n times. ``build_audit_corpus.transcode`` does one leg,
including the lesson that the decode must force the SOURCE sample rate back, so
the ladder is built from the tested path rather than a fresh one.

Every read is at the best of the canonical phases {0, 529, 47}, never at phase 0
alone: Provir's grid lock (adopted 2026-08-22) says the fixed point has period
576 samples and zero tolerance, so a phase-0 read of anything past the first
generation measures the phase, not the chain.

Usage::

    python ml/generation_probe.py --out ml/generation_probe.csv --n 24
    python ml/generation_probe.py --score ml/generation_probe.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_audit_corpus import Codec, transcode  # noqa: E402
from idem_phase_probe import CANONICAL, crop  # noqa: E402
from mp3_idem_probe import mp3_idem, require_ffmpeg  # noqa: E402

AUTHENTIC = Path(r"C:\Users\loutr\audit_corpus\authentic")
GENERATIONS = 4

LADDERS: Dict[str, Codec] = {
    "L_mp3_320": Codec("mp3_320", "libmp3lame", "mp3", ("-b:a", "320k")),
    "A_aac_256": Codec("aac_ff256", "aac", "m4a", ("-b:a", "256k")),
}

FIELDS = ["file", "ladder", "generation", "R_phase0", "R_best", "best_phase", "sha_note"]


def read_best_canonical(path: Path, ffmpeg: str) -> Dict[str, float]:
    """R at each canonical phase; the file's read is the MINIMUM over them.

    Minimum, not phase 0: a lower R is the stronger claim of an existing chain,
    and the phase that produces it is the grid the chain actually sits on.
    """
    audio, rate = sf.read(str(path), dtype="float32")
    reads: Dict[int, float] = {}
    for k in CANONICAL:
        r, _d1, _d2 = mp3_idem(crop(audio, k), int(rate), ffmpeg)
        reads[k] = r
    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
    best = min(finite, key=lambda k: finite[k]) if finite else 0
    return {
        "R_phase0": reads.get(0, float("nan")),
        "R_best": finite.get(best, float("nan")),
        "best_phase": best,
    }


def build_and_measure(out_path: Path, n_sources: int) -> int:
    ffmpeg = require_ffmpeg()
    sources = sorted(AUTHENTIC.glob("*.flac"))[:n_sources]
    if not sources:
        print(f"aucun master sous {AUTHENTIC}")
        return 1

    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["ladder"], r["generation"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for index, src in enumerate(sources, 1):
            # Generation 0 is the master itself, measured once and shared by both
            # ladders (it is the same file).
            if (src.name, "master", "0") not in done:
                reads = read_best_canonical(src, ffmpeg)
                writer.writerow(
                    {"file": src.name, "ladder": "master", "generation": 0, "sha_note": "", **reads}
                )
                fh.flush()
            for ladder, codec in LADDERS.items():
                with tempfile.TemporaryDirectory() as tmp:
                    work = Path(tmp)
                    current = src
                    for generation in range(1, GENERATIONS + 1):
                        nxt = work / f"gen{generation}.flac"
                        if transcode((current, nxt, codec)) is None:
                            print(f"  ECHEC {ladder} gen{generation} sur {src.name}")
                            return 1
                        current = nxt
                        if (src.name, ladder, str(generation)) in done:
                            continue
                        reads = read_best_canonical(current, ffmpeg)
                        writer.writerow(
                            {
                                "file": src.name,
                                "ladder": ladder,
                                "generation": generation,
                                "sha_note": "",
                                **reads,
                            }
                        )
                        fh.flush()
            print(f"  {index}/{len(sources)} {src.name}", flush=True)
    print(f"ecrit {out_path}")
    return 0


def _auc(pos: List[float], neg: List[float]) -> float:
    """P(a random pos reads LOWER than a random neg), draws at half."""
    pos = [x for x in pos if np.isfinite(x)]
    neg = [x for x in neg if np.isfinite(x)]
    if not pos or not neg:
        return float("nan")
    p = np.array(pos)[:, None]
    n = np.array(neg)[None, :]
    return float(((p < n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def score(csv_path: Path) -> int:
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    if not rows:
        print("csv vide")
        return 1

    def r_of(ladder: str, generation: int) -> Dict[str, float]:
        return {
            row["file"]: float(row["R_best"])
            for row in rows
            if row["ladder"] == ladder and int(row["generation"]) == generation
        }

    def med(values) -> float:
        vals = [v for v in values if np.isfinite(v)]
        return float(np.median(vals)) if vals else float("nan")

    print(f"{len(rows)} mesures\n")
    held: Dict[str, bool] = {}

    # G1 — monotonicity per file on ladder L
    ladder = "L_mp3_320"
    gens = {g: r_of(ladder, g) for g in range(1, GENERATIONS + 1)}
    files = sorted(set(gens[1]) & set(gens[GENERATIONS]))
    monotone = 0
    for f in files:
        series = [gens[g].get(f, float("nan")) for g in range(1, GENERATIONS + 1)]
        if all(np.isfinite(v) for v in series) and all(
            b <= a + 1e-9 for a, b in zip(series, series[1:])
        ):
            monotone += 1
    held["G1"] = monotone >= 18
    print(
        f"G1 monotonie 1->4 sur {ladder}: {monotone}/{len(files)} (borne 18) "
        f"{'TENU' if held['G1'] else 'ECHEC'}"
    )

    # G2 — separation between one and two generations
    g1, g2 = r_of(ladder, 1), r_of(ladder, 2)
    delta = med(g1.values()) - med(g2.values())
    auc12 = _auc(list(g2.values()), list(g1.values()))
    held["G2"] = delta >= 0.15 and auc12 >= 0.75
    print(
        f"G2 gen1 vs gen2: mediane {med(g1.values()):.3f} -> {med(g2.values()):.3f} "
        f"(delta {delta:+.3f}, borne 0.15), AUC {auc12:.3f} (borne 0.75) "
        f"{'TENU' if held['G2'] else 'ECHEC'}"
    )

    # G3 — the master stays out
    g0 = r_of("master", 0)
    med_g1 = med(g1.values())
    below = [f for f, v in g0.items() if np.isfinite(v) and v < med_g1]
    held["G3"] = med(g0.values()) > med_g1 and not below
    print(
        f"G3 masters: mediane {med(g0.values()):.3f} vs gen1 {med_g1:.3f}, "
        f"{len(below)} masters sous la mediane gen1 (borne 0) "
        f"{'TENU' if held['G3'] else 'ECHEC'}"
    )

    # G4 — cross-codec ladder
    ladder_a = "A_aac_256"
    a1, a2 = r_of(ladder_a, 1), r_of(ladder_a, 2)
    auc_a = _auc(list(a2.values()), list(a1.values()))
    held["G4"] = np.isfinite(auc_a) and auc_a >= 0.65
    print(
        f"G4 {ladder_a} gen1 vs gen2: AUC {auc_a:.3f} (borne 0.65) "
        f"{'TENU' if held['G4'] else 'ECHEC'}"
    )

    # G5 — the control: the phase must move past generation 1
    def phase0_share(ladder_name: str, generation: int) -> float:
        vals = [
            row
            for row in rows
            if row["ladder"] == ladder_name and int(row["generation"]) == generation
        ]
        if not vals:
            return float("nan")
        return sum(1 for row in vals if int(row["best_phase"]) == 0) / len(vals)

    share_g1 = phase0_share(ladder, 1)
    share_g2plus = np.mean([phase0_share(ladder, g) for g in range(2, GENERATIONS + 1)])
    held["G5"] = np.isfinite(share_g2plus) and share_g2plus < 0.5
    print(
        f"G5 controle de phase: gen1 a phase 0 {share_g1:.0%}, gen2+ {share_g2plus:.0%} "
        f"(borne <50%) {'TENU' if held['G5'] else 'ECHEC — la ladder est mal construite'}"
    )

    print("\nmedianes R_best par generation:")
    for ladder_name in ("master", "L_mp3_320", "A_aac_256"):
        line = []
        for g in range(0, GENERATIONS + 1):
            values = r_of(ladder_name, g)
            if values:
                line.append(f"gen{g} {med(values.values()):6.3f}")
        if line:
            print(f"  {ladder_name:12s} " + "  ".join(line))

    print(
        "\n"
        + (
            "TOUT TENU"
            if all(held.values())
            else "ECHECS: " + ", ".join(k for k, v in held.items() if not v)
        )
    )
    return 0 if all(held.values()) else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--score", type=Path)
    args = ap.parse_args(argv)
    if args.score:
        return score(args.score)
    if not args.out:
        ap.error("--out ou --score")
    return build_and_measure(args.out, args.n)


if __name__ == "__main__":
    sys.exit(main())
