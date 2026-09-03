"""Measure our own band-limited stratum against our own audio.

We told Provir that twelve of set A's thirty-six sources carry a declared
analogue-style roll-off, and we told him not to take the file date for it because
the stratum is measurable in the files he holds. He measured it. We never did.

Outsourcing the verification of your own claim to the party it is aimed at is
elegant once and a gap if it stays that way, so this is the same measurement from
this side, written to his description rather than to our engine's:

    a plain long-term average spectrum, reference taken in 10-13 kHz, reading
    where each file first falls 20 dB and then 40 dB below that reference.

Deliberately NOT reusing ``detect_cutoff`` or anything else from the engine. The
engine's cutoff is what the map was built with; checking a map against the
instrument that drew it proves only that the instrument is consistent. His
numbers to reproduce: every band-limited file with its 20 dB point between 14,174
and 14,573 Hz, median 14,486.

Usage::

    python ml/verify_own_stratum.py --set <frozen set dir> --key <labels json> \
        --strata <strata json> --out ml/own_stratum_check.csv
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf
from scipy import signal

REF_LOW_HZ = 10_000.0
REF_HIGH_HZ = 13_000.0


def edge_frequencies(path: Path) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (reference dBFS, -20 dB frequency, -40 dB frequency) for one file.

    The reference is the mean level in 10-13 kHz. The edges are the first
    frequency above that band where the spectrum stays below the reference by 20
    and 40 dB — "first" so a single noisy bin cannot declare an edge on its own.
    """
    data, rate = sf.read(str(path), always_2d=True)
    mono = data.mean(axis=1)
    freqs, power = signal.welch(mono, fs=rate, nperseg=8192, noverlap=4096, scaling="spectrum")
    with np.errstate(divide="ignore"):
        db = 10.0 * np.log10(np.maximum(power, 1e-20))

    band = (freqs >= REF_LOW_HZ) & (freqs <= REF_HIGH_HZ)
    if not band.any():
        return None, None, None
    reference = float(db[band].mean())

    above = freqs > REF_HIGH_HZ

    def first_below(drop: float) -> Optional[float]:
        mask = above & (db < reference - drop)
        if not mask.any():
            return None
        return float(freqs[mask][0])

    return reference, first_below(20.0), first_below(40.0)


def main() -> int:
    """Measure every file in a frozen set and report per stratum."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_dir", type=Path, required=True)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--strata", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    labels = json.loads(args.key.read_text(encoding="utf-8"))["labels"]
    strata = json.loads(args.strata.read_text(encoding="utf-8"))["strata"]

    rows = []
    by_source: dict = {}
    files = sorted((args.set_dir / "audio").glob("*.flac"))
    print(f"{len(files)} fichiers", flush=True)
    for index, path in enumerate(files, 1):
        entry = labels.get(path.stem)
        if entry is None:
            print(f"  hors clef: {path.name}", flush=True)
            continue
        stratum = strata.get(entry["source_slug"], "?")
        reference, e20, e40 = edge_frequencies(path)
        # The written row carries NEITHER the label NOR the source slug. The
        # label is the answer key outright; the slug says which files share a
        # source, which is the grouping a blind set exists to hide, so it is key
        # structure even after a round closes. The stratum is safe because it was
        # published to the other party with the key. Keys never enter this
        # repository — the first version of this script wrote both columns and
        # was caught at `git add`, by a leak check that had to be widened to see
        # a CSV as well as a JSON.
        rows.append(
            {
                "file": path.stem,
                "stratum": stratum,
                "reference_db": "" if reference is None else f"{reference:.2f}",
                "edge_20db_hz": "" if e20 is None else f"{e20:.1f}",
                "edge_40db_hz": "" if e40 is None else f"{e40:.1f}",
            }
        )
        # Kept in memory only, for the per-source reporting below.
        by_source.setdefault(entry["source_slug"], []).append((path.stem, e20))
        if index % 25 == 0:
            print(f"  {index}/{len(files)}", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"ecrit {args.out}", flush=True)

    for stratum in sorted({r["stratum"] for r in rows}):
        vals = [float(r["edge_20db_hz"]) for r in rows if r["stratum"] == stratum and r["edge_20db_hz"]]
        if not vals:
            print(f"{stratum}: aucune arete mesurable")
            continue
        arr = np.array(vals)
        print(
            f"{stratum}: n={len(arr)}  -20 dB de {arr.min():.0f} a {arr.max():.0f} Hz, "
            f"mediane {np.median(arr):.0f}"
        )

    # Printed, never written: naming a source is how a disagreement gets checked
    # rather than argued about, and the console is not the repository.
    low = sorted(
        (slug, [f for f, e in v if e is not None and e < 16_000])
        for slug, v in by_source.items()
    )
    flagged = [(slug, files_) for slug, files_ in low if files_]
    if flagged:
        print("\nsources dont au moins un fichier tombe -20 dB sous 16 kHz:")
        for slug, files_ in flagged:
            print(f"   {slug}: {len(files_)} fichier(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
