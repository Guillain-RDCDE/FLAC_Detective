"""Translate Provir's set A return into the vocabulary our scorer reads.

Data preparation, not scoring: ``score_v3_return.py`` is not touched. His tiers
are mapped to ours using the mapping HE declared before his verdicts existed —
UPSCALE and LOSSY_MASTER convict, SUSPECT signals, GENUINE does neither, ERROR
sits on its own line. Nothing here is inferred from how the numbers come out.

Two columns come out, because he sent two:

**Column A**, his shipped engine, is a straight tier translation.

**Column B** is two research instruments, ``mp3_lattice`` and
``vorbis_detector``, each reporting FIRES or ``-``. A dash means two different
things depending on the row, and folding them together would report a coverage
limit as a detection rate — the thing this scorer was amended twice to stop
doing. So evaluability is decided by the row's TRUE CLASS, taken from our key,
never by the symbol:

* mp3 arms are covered by the lattice, vorbis by the vorbis detector, and
  genuine rows are covered by both — a fire there is a false positive, and one
  of them does fire. On those rows a dash means the instrument ran and stayed
  silent, which is a miss and is scored as one. That is the reading he asked for
  and we refused to soften: declaring an exposure is right, excluding on it is
  not.
* aac, opus and mp2 rows have no instrument at all. A dash there is not a miss,
  it is an absence of claim, and it leaves every denominator.

Usage::

    python ml/prepare_setA_return.py --verdicts <his csv> --key <our key json> \
        --out-a ml/his_setA_colA.csv --out-b ml/his_setA_colB.csv
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import List, Optional

# His declared tiers, from his letter of 2 September, before any number moved.
TIER = {
    "UPSCALE": "FAKE_CERTAIN",
    "LOSSY_MASTER": "FAKE_CERTAIN",
    "SUSPECT": "SUSPICIOUS",
    "GENUINE": "AUTHENTIC",
    "ERROR": "ERROR",
}

# Which research instrument covers which of our arms.
LATTICE_ARMS = ("mp3_320", "mp3_V0")
VORBIS_ARMS = ("vorbis_q8",)
GENUINE = "genuine"


def main(argv: Optional[List[str]] = None) -> int:
    """Write his two columns as two verdict files our scorer can read."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", type=Path, required=True)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--out-a", type=Path, required=True)
    ap.add_argument("--out-b", type=Path, required=True)
    args = ap.parse_args(argv)

    key = json.loads(args.key.read_text(encoding="utf-8"))["labels"]
    labels = {k: v["label"] for k, v in key.items()}

    with open(args.verdicts, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    print(f"{len(rows)} rows in, {len(labels)} in the key")

    out_a, out_b = [], []
    unknown: Counter = Counter()
    stats_a: Counter = Counter()
    stats_b: Counter = Counter()
    for row in rows:
        file_id = Path(row["file"]).stem
        cls = labels.get(file_id)
        if cls is None:
            unknown[file_id] += 1
            continue

        tier = row["engine_verdict"].strip().upper()
        if tier not in TIER:
            raise SystemExit(f"unmapped tier {tier!r} on {file_id} — refusing to guess")
        out_a.append({"file": file_id, "verdict": TIER[tier]})
        stats_a[TIER[tier]] += 1

        lattice = row["mp3_lattice"].strip().upper() == "FIRES"
        vorbis = row["vorbis_detector"].strip().upper() == "FIRES"
        covered = cls in LATTICE_ARMS or cls in VORBIS_ARMS or cls == GENUINE
        if lattice or vorbis:
            verdict = "FAKE_CERTAIN"
        elif covered:
            verdict = "AUTHENTIC"  # the instrument ran and stayed silent: a miss
        else:
            verdict = "-"  # no instrument on this codec: no claim to score
        out_b.append({"file": file_id, "verdict": verdict})
        stats_b[verdict] += 1

    if unknown:
        raise SystemExit(f"{len(unknown)} rows are not in the key: {list(unknown)[:3]}")

    for path, rowset in ((args.out_a, out_a), (args.out_b, out_b)):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["file", "verdict"])
            writer.writeheader()
            writer.writerows(rowset)
        print(f"wrote {path} ({len(rowset)} rows)")
    print(f"column A: {dict(stats_a)}")
    print(f"column B: {dict(stats_b)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
