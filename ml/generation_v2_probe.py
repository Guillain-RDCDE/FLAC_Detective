#!/usr/bin/env python3
"""Counting generations, layer two: the phase search instead of three phases.

Predictions H1-H4 registered first, before this ran, in
``ml/exchange/GENERATION_V2_REGISTRATION_2026-08-31.md``.

Layer one read R at the three canonical phases {0, 529, 47}. The fixed point is
grid-locked with period 576 and zero tolerance, so three phases out of 576 is a
coarse instrument, and layer one's per-file noise (11 of 24 monotone, gen1 vs
gen2 at AUC 0.644) may be the instrument rather than the files. This tests that
and changes nothing else: same 24 sources, same libmp3lame-320 ladder, same four
generations, same R.

The search itself is ``idem_phase_probe.phase_read`` unchanged — canonical reads,
then a d1 search across the grid on a short excerpt (one round-trip per phase,
which is what makes 72 phases affordable), then the full R at the phase the
search chose. Step 8: 576 round-trips a file is eight hours, 72 is under one.

Usage::

    python ml/generation_v2_probe.py --out ml/generation_v2_probe.csv --n 24
    python ml/generation_v2_probe.py --score ml/generation_v2_probe.csv
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
from generation_probe import AUTHENTIC, GENERATIONS  # noqa: E402
from idem_phase_probe import phase_read  # noqa: E402
from mp3_idem_probe import require_ffmpeg  # noqa: E402

LADDER = Codec("mp3_320", "libmp3lame", "mp3", ("-b:a", "320k"))
STEP = 8  # 72 phases of 576; see the registration for why not 1

# Layer one's medians, quoted here so H3 is checkable without opening two files.
LAYER_ONE_MEDIANS = {1: 0.877, 2: 0.486, 3: 0.311, 4: 0.227}

FIELDS = ["file", "generation", "R_phase0", "R_best", "best_phase", "searched_phase", "searched_d1"]


def run(out_path: Path, n_sources: int) -> int:
    ffmpeg = require_ffmpeg()
    sources = sorted(AUTHENTIC.glob("*.flac"))[:n_sources]
    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["generation"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for index, src in enumerate(sources, 1):
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                current = src
                for generation in range(1, GENERATIONS + 1):
                    nxt = work / f"gen{generation}.flac"
                    if transcode((current, nxt, LADDER)) is None:
                        print(f"  ECHEC gen{generation} sur {src.name}")
                        return 1
                    current = nxt
                    if (src.name, str(generation)) in done:
                        continue
                    audio, rate = sf.read(str(current), dtype="float32")
                    reads = phase_read(audio, int(rate), ffmpeg, step=STEP)
                    writer.writerow({"file": src.name, "generation": generation, **reads})
                    fh.flush()
            print(f"  {index}/{len(sources)} {src.name}", flush=True)
    print(f"ecrit {out_path}")
    return 0


def _auc(pos: List[float], neg: List[float]) -> float:
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

    def r_of(generation: int) -> Dict[str, float]:
        return {r["file"]: float(r["R_best"]) for r in rows if int(r["generation"]) == generation}

    gens = {g: r_of(g) for g in range(1, GENERATIONS + 1)}
    files = sorted(set(gens[1]) & set(gens[GENERATIONS]))
    held: Dict[str, bool] = {}
    print(f"{len(rows)} mesures, {len(files)} fichiers complets\n")

    monotone = sum(
        1
        for f in files
        if all(np.isfinite(gens[g].get(f, float("nan"))) for g in gens)
        and all(gens[g + 1][f] <= gens[g][f] + 1e-9 for g in range(1, GENERATIONS))
    )
    held["H1"] = monotone >= 16
    print(
        f"H1 monotonie par fichier: {monotone}/{len(files)} (borne 16, couche 1: 11/24) "
        f"{'TENU' if held['H1'] else 'ECHEC'}"
    )

    auc12 = _auc(list(gens[2].values()), list(gens[1].values()))
    held["H2"] = auc12 >= 0.75
    print(
        f"H2 gen1 vs gen2: AUC {auc12:.3f} (borne 0.75, couche 1: 0.644) "
        f"{'TENU' if held['H2'] else 'ECHEC'}"
    )

    drift = {}
    for g in range(1, GENERATIONS + 1):
        values = [v for v in gens[g].values() if np.isfinite(v)]
        drift[g] = abs(float(np.median(values)) - LAYER_ONE_MEDIANS[g]) if values else float("nan")
    held["H3"] = all(np.isfinite(d) and d <= 0.15 for d in drift.values())
    print(
        "H3 medianes proches de la couche 1: "
        + ", ".join(f"gen{g} ecart {d:.3f}" for g, d in drift.items())
        + f" (borne 0.15) {'TENU' if held['H3'] else 'ECHEC'}"
    )

    non_zero = sum(1 for r in rows if int(r["best_phase"]) != 0)
    share = non_zero / len(rows)
    held["H4"] = share >= 0.25
    print(
        f"H4 phase non nulle retenue: {non_zero}/{len(rows)} = {share:.0%} (borne 25%) "
        f"{'TENU' if held['H4'] else 'ECHEC — la recherche n a rien trouve a trouver'}"
    )

    print(
        "\nmedianes R_best par generation: "
        + ", ".join(
            f"gen{g} {float(np.median([v for v in gens[g].values() if np.isfinite(v)])):.3f}"
            for g in range(1, GENERATIONS + 1)
        )
    )
    failed = [k for k, v in held.items() if not v]
    print("\n" + ("TOUT TENU" if not failed else "ECHECS: " + ", ".join(failed)))
    return 0 if not failed else 1


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
    return run(args.out, args.n)


if __name__ == "__main__":
    sys.exit(main())
