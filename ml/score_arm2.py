#!/usr/bin/env python3
"""Scoring Provir's ARM-2 return on the first blind set — the resample effect.

What ARM-2 is (his words, 2026-08-22)
--------------------------------------
The same 599 files of fd-exchange-2026-08, re-read after the 48 kHz items were
downsampled to 44.1 kHz (179 converted, 420 byte-copied), same engine
configuration as run 1, same four sentinels. Declared EXPERIMENTAL and
FP-unpriced before the first run-1 row existed — so its rows are fires, never
convictions, and run 1 remains the only scored return. Eight of 599 verdicts
differ from run 1 (591 agree): "those eight are the resample effect, and they
are yours to score." We hold the key.

Why it matters: run 1 carried a container leak we disclosed ourselves — the
first set's Opus arm was the only one at 48 kHz, and his engine fired an
AI_SR_48000 flag on it. ARM-2 is the first read of that set with the leak
removed. The movers are therefore the leak's footprint in his verdicts.

PREDICTIONS, registered before the key is opened on the movers
---------------------------------------------------------------
    A2-1  DETERMINISM. Every mover is a CONVERTED item (run-1 sample_rate
          48000); zero movers among the 420 byte-copied files. A mover among
          the copies would be engine non-determinism, not resampling.
    A2-2  THE TELL. At least 5 of the 8 movers carry the opus_256 label —
          the arm whose 48 kHz rate was the leak.
    A2-3  DIRECTION. At least 5 of the 8 move toward "clear" (less
          detection): removing a leak that HELPED catch Opus should cost
          recall on Opus, not add it. If most movers instead move toward
          detection, the 48 kHz rate was hurting him, and the leak story
          has a second chapter.

Results appended below after the run; hash of the received file recorded.
--------------------------------------------------------------------------------
RESULTS
(not yet run)
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

RUN1 = Path("ml/exchange/provir_return_2026-08.csv")
ARM2 = Path("ml/exchange/provir_return_arm2_2026-08.csv")
KEY = Path(r"C:\Users\loutr\fd-exchange-2026-08-LABELS.json")

DETECT = {"flagged", "convicted"}


def load(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


def main() -> int:
    run1, arm2 = load(RUN1), load(ARM2)
    key = json.loads(KEY.read_text(encoding="utf-8"))["labels"]
    assert len(run1) == len(arm2) == 599, (len(run1), len(arm2))

    converted = {f for f, r in run1.items() if r["sample_rate"] == "48000"}
    print(f"converted (run-1 at 48 kHz): {len(converted)}  byte-copied: {599 - len(converted)}")
    rate_now = Counter(r["sample_rate"] for r in arm2.values())
    print(f"ARM-2 sample rates: {dict(rate_now)}")

    movers = [f for f in run1 if run1[f]["verdict"] != arm2[f]["verdict"]]
    print(f"\nmovers: {len(movers)} (he announced 8)")
    toward_clear = 0
    opus = 0
    among_copied = 0
    for f in sorted(movers):
        label = key[f.replace(".flac", "")]["label"]
        v1, v2 = run1[f]["verdict"], arm2[f]["verdict"]
        if f not in converted:
            among_copied += 1
        if label == "opus_256":
            opus += 1
        if v1 in DETECT and v2 not in DETECT:
            toward_clear += 1
        correct_now = (v2 in DETECT) == (label != "genuine")
        print(
            f"  {f[-9:-5]}  {label:10} {v1:9} -> {v2:9}  "
            f"{'converted' if f in converted else 'COPIED'}  "
            f"{'now correct' if correct_now else 'now wrong'}"
        )

    print(f"\nA2-1 zero movers among byte-copied: {'HELD' if among_copied == 0 else 'FAILED'} ({among_copied})")
    print(f"A2-2 >= 5 movers labelled opus_256: {'HELD' if opus >= 5 else 'FAILED'} ({opus}/{len(movers)})")
    print(f"A2-3 >= 5 movers toward clear: {'HELD' if toward_clear >= 5 else 'FAILED'} ({toward_clear}/{len(movers)})")

    # The whole-set picture, for the record (fires, never convictions by his declaration).
    print("\nper-label detection, run 1 -> ARM-2 (flagged+convicted / n):")
    by = {}
    for f, r in run1.items():
        label = key[f.replace(".flac", "")]["label"]
        d = by.setdefault(label, [0, 0, 0])
        d[0] += 1
        d[1] += r["verdict"] in DETECT
        d[2] += arm2[f]["verdict"] in DETECT
    for label in sorted(by):
        n, a, b = by[label]
        print(f"  {label:10} {a:3}/{n:<3} -> {b:3}/{n:<3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
