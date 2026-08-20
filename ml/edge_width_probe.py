#!/usr/bin/env python3
"""Does transition WIDTH separate where edge POSITION provably cannot?

The retraction that produced this
----------------------------------
Jamie Dodd handed over a frequency — 21,570.9 Hz, an era-LAME 320 wall — and then
withdrew it himself, with the error bars he had omitted:

* it is one reading, of one file, by one edge-finder written that morning;
* early 3.9x LAME at ``-b 320`` applies **no lowpass at all**, so the number
  measures the SOURCE and not the encoder — the same build group swings 3,800 Hz on
  content alone (17,420 Hz on one CD track, 21,226 Hz on another from the same disc);
* in his lawful corpus 503 of 1,180 files (42.6 %) already read an edge at or above
  it, so a threshold there convicts lawful CD masters at scale, classical and
  acoustic material first.

And the conclusion that survives the retraction is stronger than the number was.
Of his 17 real 2009 DJ-master MP3s, 11 carry a sharp wall topping out at 21,479 Hz
and 6 have no wall at all up to 22,023 Hz; meanwhile 28 of his 75 lawful masters sit
above 21,570. **Both populations live on both sides of every line.** No edge
position separates them, which is why our own 21,500 constant was wrong in both
directions rather than merely set too low.

What he uses instead, and the caveat he volunteered
----------------------------------------------------
Frequency is only a gate (21,350-21,650 Hz). The test underneath is transition
WIDTH, and it is a conjunction rather than a threshold: his MP3 positives return
390-519 Hz, his lawful masters overwhelmingly return a *no wall found* sentinel.

Unprompted, he added: of 75 lawful files inside that window, **5 do show a sharp
wall** (409-900 Hz). So width does the work and is still not a separator on its own.

His numbers are not ours and must not be imported
--------------------------------------------------
Different smoothing, different reference band, different definition of where a
transition begins and ends. His own standing rule — never quote an absolute edge
without naming the instrument — applies to his width figures exactly as much. So
this probe calibrates on our corpus or not at all, and 390-519 is context.

What is measured
----------------
For every file: the edge position, whether an edge was found AT ALL (the sentinel
``detect_cutoff`` cannot express, since it returns Nyquist for "full spectrum",
"bass concentration" and "found nothing" alike), and the transition width.

Then the three questions that decide whether this becomes a rule:

1. does the sentinel alone separate?  (his lawful population is mostly sentinel)
2. does width separate among files where an edge WAS found?
3. what does the conjunction cost on the genuine arm — the only figure that
   licenses anything, on a project where every false conviction ever shipped came
   from a +50 spectral rule.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import (  # noqa: E402
    _welch_magnitude_db,
    detect_cutoff_detailed,
)

EXCERPT_SEC = 30.0

ARMS = {
    "genuine": ["C:/Users/loutr/audit_corpus/authentic/*.flac",
                "C:/Users/loutr/wild_authentic/**/*.flac"],
    "mp3_320": ["C:/Users/loutr/audit_corpus/fake/mp3_320/*.flac"],
    "mp3_V0": ["C:/Users/loutr/audit_corpus/fake/mp3_V0/*.flac"],
    "aac_ff320": ["C:/Users/loutr/audit_corpus/fake/aac_ff320/*.flac"],
    "aacmf_256": ["C:/Users/loutr/audit_corpus/fake/aacmf_256/*.flac"],
    "opus_256": ["C:/Users/loutr/audit_corpus/fake/opus_256/*.flac"],
    "vorbis_q8": ["C:/Users/loutr/audit_corpus/fake/vorbis_q8/*.flac"],
}


def measure(path: str) -> Optional[dict]:
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0:
        return None
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    try:
        freq, magnitude_db = _welch_magnitude_db(np.asarray(mono, dtype=np.float64), rate)
        if freq is None or magnitude_db is None:
            return None
        reading = detect_cutoff_detailed(freq, magnitude_db, rate)
    except Exception:
        return None
    return {
        "path": Path(path).name,
        "rate": rate,
        "cutoff": reading.cutoff_hz,
        "found": int(reading.found),
        "width": reading.width_hz,
    }


def collect(limit_genuine: int, limit_arm: int) -> List[dict]:
    rows: List[dict] = []
    for arm, patterns in ARMS.items():
        limit = limit_genuine if arm == "genuine" else limit_arm
        paths: List[str] = []
        for pattern in patterns:
            found = sorted(glob.glob(pattern, recursive="**" in pattern))
            paths.extend(found[: limit // len(patterns) + 1])
        seen = 0
        for path in paths:
            if seen >= limit:
                break
            row = measure(path)
            if row is None:
                continue
            row["arm"] = arm
            rows.append(row)
            seen += 1
        print(f"{arm}: {seen} mesures", flush=True)
    return rows


def report(rows: List[dict]) -> None:
    print("\n" + "=" * 78)
    print("1. LA SENTINELLE SEULE : un bord a-t-il ete trouve ?")
    print("=" * 78)
    print(f"\n{'arm':12}{'n':>5}{'aucun bord':>13}{'%':>7}")
    for arm in ARMS:
        rowset = [r for r in rows if r["arm"] == arm]
        if not rowset:
            continue
        none_found = sum(1 for r in rowset if not r["found"])
        print(f"{arm:12}{len(rowset):>5}{none_found:>13}{100*none_found/len(rowset):>6.0f}%")

    print("\n" + "=" * 78)
    print("2. LA LARGEUR, parmi les fichiers ou un bord A ete trouve")
    print("=" * 78)
    print(f"\n{'arm':12}{'n':>5}{'largeur ok':>12}{'med':>9}{'p05':>9}{'p95':>9}")
    widths = {}
    for arm in ARMS:
        w = np.array([r["width"] for r in rows
                      if r["arm"] == arm and r["found"]], dtype=float)
        w = w[np.isfinite(w)]
        widths[arm] = w
        rowset = [r for r in rows if r["arm"] == arm and r["found"]]
        if w.size:
            print(f"{arm:12}{len(rowset):>5}{w.size:>12}{np.median(w):>9.0f}"
                  f"{np.percentile(w, 5):>9.0f}{np.percentile(w, 95):>9.0f}")
        else:
            print(f"{arm:12}{len(rowset):>5}{0:>12}")

    if widths.get("genuine") is not None and widths["genuine"].size:
        print(f"\n{'arm':12}{'AUC largeur vs genuine':>26}")
        for arm in ARMS:
            if arm == "genuine" or not widths[arm].size:
                continue
            print(f"{arm:12}{auc(-widths[arm], -widths['genuine']):>26.2f}")
        print("\n(negatee : une largeur PLUS PETITE = plus mur = plus suspect)")

    print("\n" + "=" * 78)
    print("3. LA CONJONCTION, tarifee sur l'arme authentique")
    print("=" * 78)
    gen = widths.get("genuine", np.array([]))
    if not gen.size:
        print("pas d'authentique mesurable — rien ne peut etre tarife.")
        return
    for pct in (1, 5, 10):
        bar = float(np.percentile(gen, pct))
        print(f"\nbarre = p{pct} des authentiques = {bar:.0f} Hz  "
              f"(cout authentique {pct} %)")
        for arm in ARMS:
            if arm == "genuine" or not widths[arm].size:
                continue
            fires = int((widths[arm] <= bar).sum())
            total = sum(1 for r in rows if r["arm"] == arm)
            print(f"    {arm:12} {fires:3d}/{widths[arm].size:3d} des bords trouves"
                  f"   = {100*fires/total:5.1f} % de l'arme entiere ({total})")

    print("\nLecture : le taux 'de l'arme entiere' est le seul honnete — un fichier")
    print("sans bord trouve ne peut pas temoigner, et l'exclure du denominateur")
    print("gonflerait le chiffre exactement comme la population choisie a l'oeil")
    print("gonfle le sien.")


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC, callers pass the discriminating direction."""
    if not len(fake) or not len(genuine):
        return float("nan")
    values = np.concatenate([fake, genuine])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    rank_sum = ranks[: len(fake)].sum()
    return float((rank_sum - len(fake) * (len(fake) + 1) / 2) / (len(fake) * len(genuine)))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genuine", type=int, default=120)
    parser.add_argument("--arm", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/edge_width.csv"))
    args = parser.parse_args(argv)

    rows = collect(args.genuine, args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["arm", "path", "rate", "cutoff", "found", "width"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} lignes -> {args.out}", flush=True)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
