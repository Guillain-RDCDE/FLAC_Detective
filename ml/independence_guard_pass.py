#!/usr/bin/env python3
"""Price the independence guard on the corroboration barrier.

Criteria, populations, candidate constants and the choice rule were registered
first, before any number here existed, in
``ml/exchange/INDEPENDENCE_GUARD_REGISTRATION_2026-09-01.md``.

The engine runs **once** per file and records everything a candidate could need —
score, per-rule breakdown, evidence families, cutoff. Every candidate guard is
then evaluated offline against those records, so the comparison is between
constants and not between runs. The same shape as ``ml/r15_sweep.py``.

Populations, exactly as registered:

    P1  authentic          the null
    P2  bandlimited        44 parked sources + the 14 kHz roll-off
    P3  high-rate arms     where a lost conviction refuses the guard outright
    P4  low-rate arms      where the guard is dangerous, and priced BEFORE choosing

Usage::

    python ml/independence_guard_pass.py --out ml/independence_guard.csv
    python ml/independence_guard_pass.py --evaluate ml/independence_guard.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CORPUS = Path(r"C:\Users\loutr\audit_corpus")
PARKED = (
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_unused"),
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_dup_series"),
)
HIGH_RATE = ("mp3_320", "mp3_V0", "aac_ff256", "aacmf_256", "opus_256", "vorbis_q8")
LOW_RATE = ("aac_ff128", "mp3_192", "mp3_128", "mp3_V2")
N_PER_ARM = 40

# Registered candidates. Nothing outside these lists may be tried afterwards.
GUARD_HZ_CANDIDATES = (14000.0, 15000.0, 16000.0, 17000.0)
CNN_MIN_CANDIDATES = (20, 30, 40)

CNN_RULE = "Rule12MLClassifier"

FIELDS = ["file", "population", "verdict", "score", "cutoff", "families", "breakdown"]


def populations() -> List[Tuple[Path, str, bool]]:
    """(path, population, needs_band_limiting) for every file under measurement."""
    out: List[Tuple[Path, str, bool]] = []
    for path in sorted((CORPUS / "authentic").glob("*.flac"))[: N_PER_ARM * 2]:
        out.append((path, "authentic", False))
    for arm in HIGH_RATE + LOW_RATE:
        for path in sorted((CORPUS / "fake" / arm).glob("*.flac"))[:N_PER_ARM]:
            out.append((path, arm, False))
    for folder in PARKED:
        for path in sorted(folder.glob("*.flac")):
            out.append((path, "bandlimited", True))
    return out


def run(out_path: Path) -> int:
    """One engine pass over every population, resumable."""
    from v3_build_set_a import BAND_LIMIT_FILTER

    from flac_detective.analysis.analyzer import FLACAnalyzer

    items = populations()
    done: Set[Tuple[str, str]] = set()
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
                except Exception as exc:  # a crash is data, not a reason to stop
                    print(f"  ECHEC {path.name}: {exc}", flush=True)
                    continue
                writer.writerow(
                    {
                        "file": path.name,
                        "population": population,
                        "verdict": result.get("verdict", ""),
                        "score": result.get("score", ""),
                        "cutoff": result.get("cutoff_freq", ""),
                        "families": "+".join(result.get("evidence_families") or []),
                        "breakdown": json.dumps(result.get("score_breakdown") or {}),
                    }
                )
                fh.flush()
                if index % 25 == 0:
                    print(f"  {index}/{len(items)}", flush=True)
    print(f"ecrit {out_path}", flush=True)
    return 0


def _guarded_families(
    families: Set[str],
    cutoff: Optional[float],
    breakdown: Dict[str, int],
    guard_hz: float,
    mechanism: str,
    cnn_min: int = 0,
) -> Set[str]:
    """Apply one candidate guard to one file's evidence set.

    An unknown cutoff is not a low cutoff: the guard is inert (criterion I5).
    """
    if cutoff is None or not (cutoff < guard_hz):
        return families
    if not {"cnn", "spectral"} <= families:
        return families
    if mechanism == "A":
        return (families - {"cnn", "spectral"}) | {"cnn+spectral"}
    # Mechanism B only speaks when those two are the ONLY families present.
    if families != {"cnn", "spectral"}:
        return families
    return families if breakdown.get(CNN_RULE, 0) >= cnn_min else families - {"cnn"}


def _convicted(score: int, families: Set[str]) -> bool:
    from flac_detective.analysis.new_scoring.verdict import (
        determine_verdict,
        uncorroborated_conviction_blocked,
    )

    verdict, _ = determine_verdict(score, families)
    if uncorroborated_conviction_blocked(score, families):
        return False
    return verdict == "FAKE_CERTAIN"


def _load(path: Path) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["score_i"] = int(float(row["score"] or 0))
        row["families_s"] = {f for f in (row["families"] or "").split("+") if f}
        row["breakdown_d"] = json.loads(row["breakdown"] or "{}")
        try:
            cut = float(row["cutoff"])
            row["cutoff_f"] = None if cut != cut or cut <= 0 else cut
        except (TypeError, ValueError):
            row["cutoff_f"] = None
    return rows


def _counts(rows: Sequence[dict], guard) -> Dict[str, int]:
    """Convictions per population group under ``guard`` (None = baseline)."""
    groups = {"authentic": 0, "bandlimited": 0, "high": 0, "low": 0}
    for row in rows:
        families = row["families_s"] if guard is None else guard(row)
        if not _convicted(row["score_i"], families):
            continue
        pop = row["population"]
        key = (
            pop if pop in ("authentic", "bandlimited") else ("high" if pop in HIGH_RATE else "low")
        )
        groups[key] += 1
    return groups


def evaluate(path: Path) -> int:
    rows = _load(path)
    print(f"{len(rows)} fichiers lus\n")
    base = _counts(rows, None)
    print(
        f"BASELINE  authentiques {base['authentic']}  band-limited {base['bandlimited']}  "
        f"haut debit {base['high']}  bas debit {base['low']}\n"
    )

    header = (
        f"{'mecanisme':>12s} {'authent.':>9s} {'band-lim':>9s} {'haut deb.':>10s} {'bas deb.':>9s}"
    )
    print(header + f" {'I1':>4s} {'I2':>4s} {'I3':>4s} {'I4':>4s}")

    eligible: List[Tuple[float, str, int, Dict[str, int]]] = []
    for guard_hz in GUARD_HZ_CANDIDATES:
        specs: List[Tuple[str, int]] = [("A", 0)] + [("B", c) for c in CNN_MIN_CANDIDATES]
        for mechanism, cnn_min in specs:

            def guard(row, hz=guard_hz, mech=mechanism, cmin=cnn_min):
                return _guarded_families(
                    row["families_s"], row["cutoff_f"], row["breakdown_d"], hz, mech, cmin
                )

            got = _counts(rows, guard)
            i1 = got["bandlimited"] <= 1
            i2 = got["authentic"] <= base["authentic"]
            i3 = got["high"] == base["high"]
            lost_low = base["low"] - got["low"]
            i4 = lost_low <= 0.03 * base["low"]
            label = f"{mechanism} {int(guard_hz)}" + (f"/{cnn_min}" if mechanism == "B" else "")
            mark = lambda ok: " OK " if ok else "FAIL"  # noqa: E731
            print(
                f"{label:>12s} {got['authentic']:9d} {got['bandlimited']:9d} "
                f"{got['high']:10d} {got['low']:9d} "
                f"{mark(i1):>4s} {mark(i2):>4s} {mark(i3):>4s} {mark(i4):>4s}"
            )
            if i1 and i2 and i3 and i4:
                eligible.append((guard_hz, label, cnn_min, got))

    print()
    if not eligible:
        print("AUCUN candidat ne satisfait I1+I3+I4 : le garde est REFUSE (clause enregistree)")
        return 1
    # Choice rule, written before the sweep: smallest GUARD_HZ, ties toward A.
    chosen = min(eligible, key=lambda e: (e[0], 0 if e[1].startswith("A") else 1))
    print(f"candidats retenus : {[e[1] for e in eligible]}")
    print(f"CHOISI (plus petit GUARD_HZ, egalite vers A) : {chosen[1]} -> {chosen[3]}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--evaluate", type=Path)
    args = ap.parse_args(argv)
    if args.evaluate:
        return evaluate(args.evaluate)
    if args.out:
        return run(args.out)
    ap.error("either --out or --evaluate")
    return 2


if __name__ == "__main__":
    sys.exit(main())
