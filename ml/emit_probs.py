#!/usr/bin/env python3
"""Emit a ``p_raw,label`` CSV using the SHIPPED, production inference path.

Calibration (``ml/calibrate_model.py``) and the WARNING-floor threshold
(``ml/calibrate_r12_threshold.py``) must be fitted on the *same* probabilities the
runtime produces. Since v#3 the runtime aggregates several windows
(:func:`flac_detective...ml_classifier.infer_file_probability`), not one middle
segment — so this helper walks a labelled corpus through that exact function and
writes the raw aggregated probability per file. Feed its output to
``calibrate_model.py``.

Point it at two directories (authentic and transcoded), or at one directory plus
a CSV manifest of ``path,label`` rows. Files the reliability gate makes the model
abstain on are skipped by default (``--include-abstained`` keeps them).

Usage::

    python ml/emit_probs.py --authentic dataset/authentic --transcoded dataset/transcoded \
        --out calib_probs.csv
    python ml/calibrate_model.py --input calib_probs.csv --method platt
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterator, Tuple

from flac_detective.analysis.new_scoring.rules.ml_classifier import infer_file_probability

_AUDIO_EXTS = {".flac", ".wav", ".m4a", ".ape"}


def _iter_dir(root: Path, label: int) -> Iterator[Tuple[Path, int]]:
    """Yield (path, label) for every audio file under ``root``."""
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in _AUDIO_EXTS:
            yield p, label


def main() -> None:
    """Walk the labelled corpus and write the p_raw,label CSV."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--authentic", type=Path, help="Directory of authentic (label 0) files")
    ap.add_argument("--transcoded", type=Path, help="Directory of transcoded (label 1) files")
    ap.add_argument("--out", type=Path, required=True, help="Output CSV path")
    ap.add_argument(
        "--include-abstained",
        action="store_true",
        help="Keep files the reliability gate abstains on (default: skip them)",
    )
    args = ap.parse_args()

    pairs = []
    if args.authentic:
        pairs += list(_iter_dir(args.authentic, 0))
    if args.transcoded:
        pairs += list(_iter_dir(args.transcoded, 1))
    if not pairs:
        raise SystemExit("Nothing to do: pass --authentic and/or --transcoded directories.")

    rows = 0
    skipped = 0
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["p_raw", "label"])
        for i, (path, label) in enumerate(pairs, 1):
            result = infer_file_probability(path)
            if result is None:
                skipped += 1
                continue
            if result["abstained"] and not args.include_abstained:
                skipped += 1
                continue
            writer.writerow([f"{result['p_raw']:.6f}", label])
            rows += 1
            if i % 100 == 0:
                print(f"  {i}/{len(pairs)} processed ({rows} rows, {skipped} skipped)")

    print(f"Wrote {rows} rows to {args.out} ({skipped} skipped: model unavailable/abstained)")


if __name__ == "__main__":
    main()
