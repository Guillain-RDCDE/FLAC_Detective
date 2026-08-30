#!/usr/bin/env python3
"""Which files can the R11D repair move, and why — the cheap pass.

Criteria registered first in ``ml/exchange/R11D_ABSENCE_REGISTRATION_2026-08-30.md``.

The full engine costs about ten seconds a file and four parallel shards make it
worse rather than better on a four-core machine (they contend on the CNN). It is
also unnecessary: the code path bounds the affected population exactly, and this
pass measures that population directly instead of rediscovering it.

    * Rule 11 runs only when ``cutoff_freq < 19000`` (``calculator.py``).
    * Its score gates one thing: ``cassette_score >= CASSETTE_THRESHOLD`` (15)
      awards -40 and disables Rule 1.
    * TEST 11D contributes -10 when ``cutoff_std < 30``, which under the absence
      defect is every file of 90 s or less.
    * So a file moves if and only if removing that -10 crosses the gate:
      ``S < 15 <= S + 10`` where S is 11A + 11B, i.e. **S == 20** given the
      reachable set S in {-20, 0, 10, 20, 30, 50}.

This pass computes, per file, the shipped ``cassette_score`` and the same score
with 11D's absence contribution removed, and reports every file that crosses the
gate. Those files, and only those, then get the full before/after engine run.

Usage::

    python ml/r11d_scope_pass.py --out ml/r11d_scope.csv
    python ml/r11d_scope_pass.py --out ml/r11d_scope.csv --movers   # just the list
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

EXCHANGE = Path(r"C:\Users\loutr\fd-exchange-v2-2026-08\audio")
CORPUS = Path(r"C:\Users\loutr\audit_corpus")
CASSETTE_GATE = 15

FIELDS = [
    "file",
    "corpus",
    "label",
    "cutoff_hz",
    "cutoff_std_hz",
    "rule11_runs",
    "cassette_shipped",
    "cassette_without_absence",
    "gate_shipped",
    "gate_repaired",
    "moves",
    "reasons",
]


def corpus_files() -> List[tuple]:
    out: List[tuple] = []
    for p in sorted(EXCHANGE.glob("*.flac")):
        out.append((p, "fd-exchange-v2", ""))
    for p in sorted((CORPUS / "authentic").glob("*.flac")):
        out.append((p, "audit_corpus", "genuine"))
    for p in sorted((CORPUS / "fake" / "mp3_320").glob("*.flac")):
        out.append((p, "audit_corpus", "mp3_320"))
    return out


def read_one(path: Path, corpus: str, label: str) -> Optional[dict]:
    import soundfile as sf

    from flac_detective.analysis.new_scoring.rules.cassette import (
        apply_rule_11_cassette_detection,
    )
    from flac_detective.analysis.spectrum import analyze_spectrum

    try:
        cutoff, _energy, std, _resid = analyze_spectrum(path)
        rate = sf.info(str(path)).samplerate
    except Exception as exc:
        print(f"  LECTURE ECHOUEE {path.name}: {exc}", flush=True)
        return None

    runs = cutoff < 19000
    shipped, reasons = (0, [])
    if runs:
        try:
            shipped, reasons = apply_rule_11_cassette_detection(str(path), cutoff, std, rate)
        except Exception as exc:
            print(f"  R11 ECHOUEE {path.name}: {exc}", flush=True)
            return None

    # The shipped call clamps at max(0, ...), so recover 11D's -10 from the
    # reason it emits rather than from the clamped number.
    absence_applied = any("very stable" in r for r in reasons)
    without = shipped + 10 if absence_applied else shipped

    return {
        "file": path.name,
        "corpus": corpus,
        "label": label,
        "cutoff_hz": f"{cutoff:.1f}",
        "cutoff_std_hz": f"{std:.1f}",
        "rule11_runs": int(runs),
        "cassette_shipped": shipped,
        "cassette_without_absence": without,
        "gate_shipped": int(shipped >= CASSETTE_GATE),
        "gate_repaired": int(without >= CASSETTE_GATE),
        "moves": int((shipped >= CASSETTE_GATE) != (without >= CASSETTE_GATE)),
        "reasons": " | ".join(reasons),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--movers", action="store_true", help="print the mover list and exit")
    args = ap.parse_args(argv)
    out = Path(args.out)

    if args.movers:
        with open(out, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        movers = [r for r in rows if r["moves"] == "1"]
        print(f"{len(rows)} fichiers, {len(movers)} bougent")
        for r in movers:
            print(
                f"  {r['file']} [{r['label'] or r['corpus']}] cutoff {r['cutoff_hz']} "
                f"cassette {r['cassette_shipped']} -> {r['cassette_without_absence']}"
            )
        return 0

    files = corpus_files()
    if args.limit:
        files = files[: args.limit]
    done = set()
    if out.exists():
        with open(out, newline="", encoding="utf-8") as fh:
            done = {r["file"] for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} deja faits", flush=True)

    new = not out.exists()
    with open(out, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for k, (path, corpus, label) in enumerate(files, 1):
            if path.name in done:
                continue
            row = read_one(path, corpus, label)
            if row is not None:
                writer.writerow(row)
                fh.flush()
            if k % 50 == 0:
                print(f"  {k}/{len(files)}", flush=True)
    print(f"ecrit {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
