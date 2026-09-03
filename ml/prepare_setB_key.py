"""Convert Provir's set B key CSV into the key JSON the scorer reads.

Data preparation, not scoring: ``score_v3_return.py`` is not modified, and this
script never looks at a verdict. It only reshapes his key into the freezer's own
format so the scorer can read it, and it fails loudly rather than guessing.

Two decisions are made here and both are declared rather than buried:

**The stratum.** The scorer's K2 needs a ``strata`` map, and asks for genuine
rows split into band-limited and full-band. His key marks provenance in
``source_bucket``, and the three VINYL_TRANSFER sources are the stratum he
disclosed on 31 August — the thing our K2 condition asked him for. They are
mapped to ``band_limited_analog``; everything else to ``full_band``. The name
keeps the ``band_limited`` prefix the scorer matches on, and says in the same
word that this stratum is analog provenance rather than a measured roll-off.
Whether those three actually read band-limited to our instrument is a separate
measurement, reported beside the score and not used to build this map.

**The id.** The scorer joins on the stem, so ``b001.wav`` becomes ``b001``.

Usage::

    python ml/prepare_setB_key.py --csv <his key> --out ml/setB_key.json
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import List, Optional

VINYL_BUCKET = "VINYL_TRANSFER"
EXPECTED_ROWS = 280
EXPECTED_PER_CLASS = 35
EXPECTED_CLASSES = 8
EXPECTED_STEMS = 35


def main(argv: Optional[List[str]] = None) -> int:
    """Reshape his key CSV into the scorer's JSON, checking every declared count."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    raw = args.csv.read_bytes()
    print(f"source {args.csv.name}  {len(raw)} bytes")
    print(f"sha256 {hashlib.sha256(raw).hexdigest()}")

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"{len(rows)} rows, expected {EXPECTED_ROWS} — nothing written")

    labels = {}
    strata = {}
    classes: Counter = Counter()
    buckets: Counter = Counter()
    for row in rows:
        file_id = Path(row["id"]).stem
        stem = row["source_stem"]
        labels[file_id] = {"label": row["class"], "source_slug": stem}
        classes[row["class"]] += 1
        buckets[row["source_bucket"]] += 1
        stratum = "band_limited_analog" if row["source_bucket"] == VINYL_BUCKET else "full_band"
        if stem in strata and strata[stem] != stratum:
            raise SystemExit(f"source {stem} has two buckets — refusing to guess")
        strata[stem] = stratum

    if len(labels) != EXPECTED_ROWS:
        raise SystemExit(f"{len(labels)} unique ids, expected {EXPECTED_ROWS}")
    if len(strata) != EXPECTED_STEMS:
        raise SystemExit(f"{len(strata)} stems, expected {EXPECTED_STEMS}")
    if len(classes) != EXPECTED_CLASSES or set(classes.values()) != {EXPECTED_PER_CLASS}:
        raise SystemExit(f"classes are not {EXPECTED_CLASSES} x {EXPECTED_PER_CLASS}: {dict(classes)}")

    print(f"rows {len(labels)}, classes {len(classes)} x {EXPECTED_PER_CLASS}, stems {len(strata)}")
    for name, count in sorted(classes.items()):
        print(f"   {name:<16} {count}")
    print("buckets:")
    for name, count in sorted(buckets.items()):
        print(f"   {name:<16} {count}")
    band = sorted(s for s, v in strata.items() if v.startswith("band_limited"))
    genuine_band = [
        f for f, v in labels.items()
        if v["label"] == "genuine" and strata[v["source_slug"]].startswith("band_limited")
    ]
    print(f"stratum: {len(band)} sources {band} -> {len(genuine_band)} genuine rows")

    body = json.dumps({"labels": labels, "strata": strata}, indent=2, sort_keys=True) + "\n"
    args.out.write_bytes(body.encode("utf-8"))
    print(f"wrote {args.out}  sha256 {hashlib.sha256(args.out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
