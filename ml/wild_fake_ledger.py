#!/usr/bin/env python3
"""A ledger for fakes that were actually sold or traded as lossless.

The gap this exists to close
----------------------------
Every number this project publishes was measured on transcodes it made itself. So
the benchmark partly measures our own ffmpeg, and nothing in it demonstrates that
the tool helps anyone. Provir has a wild section — 50 of 53 adjudicated by ear on
MP3-320 passed off as lossless — and FLAC Detective has **zero**. It is the only
deficit that depends on nobody else, and the only number that would settle whether
either tool is useful rather than merely interesting.

What is hard here is not collection. It is **ground truth**: knowing that a file
found in the wild really is a transcode. This tool therefore does not try to
decide that. It makes the human decision cheap, and — more importantly — makes it
*durable*, so a corpus accumulates with its provenance attached instead of
evaporating into a spreadsheet.

The adjudication ledger
-----------------------
One JSON record per file, keyed by content hash so a rename or a re-download does
not create a duplicate entry, holding:

* the audio's SHA-256 and basic format facts;
* where it came from, in the submitter's words;
* every verdict this tool has ever produced for it, with the version that produced
  it — so a corpus built today still means something after the engine changes;
* the human adjudication, its basis, and who made it.

``basis`` is the field that matters and the one worth being strict about. "It
sounds bad" and "the tracker's staff trumped it as a transcode" are not the same
evidence, and a corpus that does not record which one it had cannot be audited
later. The accepted values are deliberately few.

Deliberately NOT automated
--------------------------
The engine's own verdict is recorded but never becomes the label. A corpus labelled
by the detector under test measures nothing except its own self-consistency, which
is the oldest way to produce a confident wrong number.

Usage::

    python ml/wild_fake_ledger.py add <path>... --source "c411, 2026-08, 'lossless' rip"
    python ml/wild_fake_ledger.py adjudicate <sha> --label fake --basis tracker_staff
    python ml/wild_fake_ledger.py status
    python ml/wild_fake_ledger.py export --out ml/wild_fakes.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

LEDGER = Path("ml/wild_fake_ledger.json")

# How the human knew. Ordered strongest first, and short on purpose: a long list
# invites "other", and "other" is how a corpus quietly fills with guesses.
BASES = {
    "tracker_staff": "a private tracker's staff adjudicated it a transcode",
    "provenance_pair": "a verified-lossless copy of the same master exists and differs",
    "uploader_admission": "the uploader or distributor acknowledged the source",
    "listening": "adjudicated by ear, by someone who does this competently",
}

LABELS = ("fake", "genuine", "undecided")


def sha256(path: Path) -> str:
    """Content hash — the ledger key, so renames do not fork a record."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load() -> Dict[str, dict]:
    """Read the ledger, or start an empty one."""
    if not LEDGER.exists():
        return {}
    data: Dict[str, dict] = json.loads(LEDGER.read_text(encoding="utf-8"))
    return data


def save(records: Dict[str, dict]) -> None:
    """Write the ledger back, sorted so diffs stay readable."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(records, indent=1, sort_keys=True), encoding="utf-8")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_add(args: argparse.Namespace) -> int:
    """Register files and record what the engine currently says about them."""
    from flac_detective import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer

    records = load()
    analyzer = FLACAnalyzer(sample_duration=30.0, deep=True)
    added = updated = 0

    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            print(f"  skip {path}: not a file")
            continue
        key = sha256(path)
        record = records.get(key)
        if record is None:
            record = {
                "sha256": key,
                "filename": path.name,
                "bytes": path.stat().st_size,
                "source": args.source,
                "added": _now(),
                "adjudication": {"label": "undecided", "basis": None,
                                 "by": None, "at": None, "note": None},
                "verdicts": [],
            }
            records[key] = record
            added += 1
        else:
            updated += 1

        try:
            result = analyzer.analyze_file(str(path))
            record["verdicts"].append({
                "version": __version__,
                "at": _now(),
                "verdict": result["verdict"],
                "score": result["score"],
                "families": sorted(result.get("evidence_families") or []),
            })
        except Exception as exc:
            print(f"  {path.name}: analysis failed ({exc})")

        print(f"  {path.name}  {key[:12]}  {record['verdicts'][-1]['verdict']}"
              if record["verdicts"] else f"  {path.name}  {key[:12]}")

    save(records)
    print(f"\n{added} new, {updated} already known. Ledger: {LEDGER}")
    print("Nothing is labelled yet — run `adjudicate`, and note that the engine's "
          "own verdict must never be the label.")
    return 0


def cmd_adjudicate(args: argparse.Namespace) -> int:
    """Record a HUMAN decision, with the basis it rests on."""
    records = load()
    matches = [k for k in records if k.startswith(args.sha)]
    if len(matches) != 1:
        print(f"{'no' if not matches else 'ambiguous'} match for {args.sha!r}")
        return 1
    key = matches[0]

    if args.label == "fake" and args.basis is None:
        print("a 'fake' label needs --basis; guessing is what this ledger exists to "
              "prevent.\n  " + "\n  ".join(f"{k}: {v}" for k, v in BASES.items()))
        return 1
    if args.basis and args.basis not in BASES:
        print(f"unknown basis {args.basis!r}. Accepted: {', '.join(BASES)}")
        return 1

    records[key]["adjudication"] = {
        "label": args.label,
        "basis": args.basis,
        "by": args.by or getpass.getuser(),
        "at": _now(),
        "note": args.note,
    }
    save(records)
    print(f"{records[key]['filename']} -> {args.label}"
          + (f" ({args.basis})" if args.basis else ""))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """What the corpus holds, and what the engine gets right on the labelled part."""
    records = load()
    if not records:
        print(f"ledger empty ({LEDGER})")
        return 0

    labels = Counter(r["adjudication"]["label"] for r in records.values())
    bases = Counter(r["adjudication"]["basis"] for r in records.values()
                    if r["adjudication"]["basis"])
    print(f"{len(records)} files in the ledger")
    for label in LABELS:
        print(f"  {label:10} {labels.get(label, 0)}")
    if bases:
        print("\nbasis of the fake labels:")
        for basis, count in bases.most_common():
            print(f"  {basis:20} {count}")

    # The only number that matters, and only over ADJUDICATED files.
    judged = [r for r in records.values()
              if r["adjudication"]["label"] in ("fake", "genuine") and r["verdicts"]]
    if not judged:
        print("\nnothing adjudicated yet — no performance number can be quoted.")
        return 0

    fakes = [r for r in judged if r["adjudication"]["label"] == "fake"]
    genuine = [r for r in judged if r["adjudication"]["label"] == "genuine"]

    def rate(rows: List[dict], predicate) -> str:
        if not rows:
            return "—"
        hits = sum(1 for r in rows if predicate(r["verdicts"][-1]["verdict"]))
        return f"{hits}/{len(rows)} ({100 * hits / len(rows):.0f}%)"

    print(f"\nON ADJUDICATED FILES ONLY (n={len(judged)}):")
    print(f"  wild fakes flagged     {rate(fakes, lambda v: v != 'AUTHENTIC')}")
    print(f"  wild fakes convicted   {rate(fakes, lambda v: v == 'FAKE_CERTAIN')}")
    print(f"  genuine wrongly convicted "
          f"{rate(genuine, lambda v: v == 'FAKE_CERTAIN')}")
    if len(fakes) < 30:
        print(f"\n  n={len(fakes)} fakes is too few to quote publicly. Provir's wild "
              "row is 53.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Flat CSV of the adjudicated part, for joining against other measurements."""
    records = load()
    rows = [r for r in records.values() if r["adjudication"]["label"] != "undecided"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "sha256", "label", "basis", "verdict", "score", "families", "version"])
        writer.writeheader()
        for record in sorted(rows, key=lambda r: r["sha256"]):
            last = record["verdicts"][-1] if record["verdicts"] else {}
            writer.writerow({
                "sha256": record["sha256"],
                "label": record["adjudication"]["label"],
                "basis": record["adjudication"]["basis"] or "",
                "verdict": last.get("verdict", ""),
                "score": last.get("score", ""),
                "families": "+".join(last.get("families", [])),
                "version": last.get("version", ""),
            })
    # Filenames are deliberately absent: the ledger is committed, and a private
    # library's track titles are not ours to publish.
    print(f"{len(rows)} adjudicated rows -> {args.out}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Dispatch."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="register files and record the engine's verdict")
    add.add_argument("paths", nargs="+")
    add.add_argument("--source", required=True, help="where it came from, in your words")
    add.set_defaults(func=cmd_add)

    adj = sub.add_parser("adjudicate", help="record a HUMAN label")
    adj.add_argument("sha", help="sha256 prefix")
    adj.add_argument("--label", required=True, choices=LABELS)
    adj.add_argument("--basis", choices=sorted(BASES))
    adj.add_argument("--by")
    adj.add_argument("--note")
    adj.set_defaults(func=cmd_adjudicate)

    status = sub.add_parser("status", help="what the corpus holds")
    status.set_defaults(func=cmd_status)

    export = sub.add_parser("export", help="CSV of the adjudicated part")
    export.add_argument("--out", type=Path, default=Path("ml/wild_fakes.csv"))
    export.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    raise SystemExit(main())
