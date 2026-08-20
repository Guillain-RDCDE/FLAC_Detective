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
* the human adjudication, its basis, HOW THE FILE WAS SELECTED, and who made it.

``basis`` is the field that matters and the one worth being strict about. "It
sounds bad" and "the tracker's staff trumped it as a transcode" are not the same
evidence, and a corpus that does not record which one it had cannot be audited
later. The accepted values are deliberately few.

``selection`` is the field this ledger nearly failed to have, and it answers a
different question: not how the file was *settled* but how it was *chosen*. Provir
convicts 88 % of the fakes their author picked out by eye and 0 % of the ones he
had to listen for. Those are not two scores, they are one instrument measured
against the sense that chose its problem — and no basis field can reveal it,
because the labels on both groups may be equally sound. Only the cross-tabulation
shows it, so ``status`` prints it unasked.

Deliberately NOT automated
--------------------------
The engine's own verdict is recorded but never becomes the label. A corpus labelled
by the detector under test measures nothing except its own self-consistency, which
is the oldest way to produce a confident wrong number.

First stress-test: Provir's wild53 ledger (2026-08-20), and the three gaps it found
------------------------------------------------------------------------------------
Jamie Dodd sent his 53 wild files as a feature ledger — labels, bases, dates, no
audio (archived in ``ml/exchange/``). He framed it as "a test of your taxonomy,
never a shared benchmark", and the schema failed it three ways before a single
row was entered:

1. **No basis could express his strongest tier.** 34 of 53 are "owner-knowledge":
   the physical owner of the release attests its source — no instrument, no eyes,
   no ears. That is referee-grade for a spectral axis and this file had no name
   for it. Added: ``owner_attestation``.
2. **No way to record a ruling made by extension.** His CD3 tier examined 5 tracks
   and ruled 19 — the panel covered the hardest cases and the ruling was extended
   to the disc. An adjudication's SCOPE (this file vs a group it belongs to) is a
   separate fact from its basis, and a corpus that cannot record it will silently
   present 19 rulings as 19 examinations. Added: ``--scope group`` requiring a
   note that says what was actually examined.
3. **Selection is a pipeline, not a value.** His CD3 files were chosen by a metric
   and settled by an eye — ``detector`` then ``human_eye``. A single-valued field
   forces a lie either way (the earlier lesson "bases must be a set, not a single
   value", arriving on the other field). Accepted now: ``+``-chained selections,
   each link validated, and the cross-tabulation treats a chain as tainted by its
   most sensory link.

And one thing the failure was RIGHT about, kept deliberately: the ledger is keyed
by the audio's sha256, so **a file whose bytes we do not hold cannot enter it**.
His ledger ships with empty hash fields and he names that as its real gap — a
ledger without byte identity cannot prove two parties measured the same thing.
The 53 stay archived as HIS ledger in ``ml/exchange/``, not imported as rows here.

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
    "byte_identity": "byte-identical to a known lossy source",
    "owner_attestation": "the release's physical owner attests its source from "
                         "knowledge and ownership, no instrument involved",
    "listening": "adjudicated by ear, by someone who does this competently",
    "spectrogram": "adjudicated by looking at a spectrogram",
}

# The bases that do NOT come from a human's eyes or ears. Only these are ground
# truth for a spectral axis; the rest are circular against one by construction.
#
# `spectrogram` is listed at all because refusing to name it does not stop anyone
# using it — it only forces them to mislabel it as `listening`, which is the same
# corpus with the evidence hidden. Provir's ledger records 16 of 34 fakes settled
# this way and 9 more by ear, leaving 6 referee-grade rows out of 34.
REFEREE_BASES = frozenset({"tracker_staff", "provenance_pair", "uploader_admission",
                           "byte_identity", "owner_attestation"})

# How the file ENTERED the candidate pool — a different question from how it was
# settled, and the one this ledger nearly failed to ask.
#
# Jamie Dodd's measurement is the reason it is here. On his corpus his engine
# convicts 14 of 16 files he had picked out by eye (88 %) and 0 of 9 he had to
# listen to (0 %). Those are not two performance figures: they are one instrument
# scored against the sense that selected its problem. A label settled by provenance
# is not circular — but if a human eye chose which files got a provenance check,
# every statistic computed over the survivors still inherits that eye.
#
# A basis field alone cannot show this. Only the cross-tabulation can, which is why
# `status` prints it whether or not anyone asks.
SELECTIONS = {
    "systematic": "every file in a defined set was submitted, with no human triage",
    "reported": "someone else flagged it — tracker report, forum thread, complaint",
    "detector": "this tool flagged it (records the loop; never a label)",
    "human_eye": "a human picked it out of a larger pool by looking",
    "human_ear": "a human picked it out of a larger pool by listening",
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
                                 "selection": None, "referee": False,
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
    # Selection is required for every decided label, not just 'fake'. A genuine
    # label chosen by eye biases a spectral axis exactly as hard, in the other
    # direction, and the ledger is empty so there is no legacy row to grandfather.
    if args.label in ("fake", "genuine") and args.selection is None:
        print("a decided label needs --selection: how did this file enter the pool?\n  "
              + "\n  ".join(f"{k}: {v}" for k, v in SELECTIONS.items())
              + "\n\nThis is not the same question as --basis. Basis says how it was "
                "settled;\nselection says how it was chosen, and the choosing is what "
                "biases any\nstatistic computed over the survivors.\n\nA pipeline is "
                "written with '+': a metric shortlisted and an eye ruled is\n"
                "'detector+human_eye' (Provir's CD3 tier).")
        return 1
    # A selection may be a pipeline — validate every link, not the joined string.
    if args.selection is not None:
        links = args.selection.split("+")
        bad = [link for link in links if link not in SELECTIONS]
        if bad:
            print(f"unknown selection link(s) {bad}. Accepted links: "
                  f"{', '.join(sorted(SELECTIONS))}, chained with '+'.")
            return 1
    # Scope: was THIS file examined, or does its ruling extend from a group?
    # Provir's CD3 examined 5 tracks and ruled 19; a ledger that cannot say so
    # presents 19 rulings as 19 examinations.
    if args.scope == "group" and not args.note:
        print("a group-scope ruling needs --note saying what was actually examined "
              "and how far the ruling was extended (e.g. '5 of 19 tracks examined, "
              "one master per disc').")
        return 1

    records[key]["adjudication"] = {
        "label": args.label,
        "basis": args.basis,
        "selection": args.selection,
        "scope": args.scope,
        "referee": args.basis in REFEREE_BASES,
        "by": args.by or getpass.getuser(),
        "at": _now(),
        "note": args.note,
    }
    save(records)
    print(f"{records[key]['filename']} -> {args.label}"
          + (f" ({args.basis})" if args.basis else ""))
    return 0


def _print_selection_breakdown(fakes: List[dict], rate) -> None:
    """The split that gets printed whether or not anyone asks for it.

    A single headline conviction rate averages the population a human eye picked out
    with the population it could not, and the average is meaningless. That is
    Provir's 88 % / 0 % measurement, and their headline number carried exactly this
    defect until they broke it out. A number nobody breaks out is a number nobody can
    see is wrong — so this is not an option or a verbose flag.
    """
    if not fakes:
        return

    def links(row: dict) -> frozenset:
        """A selection chain's links — a chain is tainted by its most sensory link."""
        raw = row["adjudication"].get("selection") or ""
        return frozenset(raw.split("+")) if raw else frozenset()

    referee = [r for r in fakes if r["adjudication"].get("referee")]
    eyeball = [r for r in fakes if links(r) & {"human_eye", "human_ear"}]

    print("\n  BROKEN OUT — the headline above averages these and means little:")
    print(f"    referee-grade labels only  {rate(referee, lambda v: v == 'FAKE_CERTAIN')}"
          "   <- the only rows valid for a spectral axis")
    for selection in sorted(SELECTIONS):
        rows = [r for r in fakes if selection in links(r)]
        if rows:
            print(f"    selected by {selection:12} "
                  f"{rate(rows, lambda v: v == 'FAKE_CERTAIN')}")

    if len(eyeball) == len(fakes):
        print("\n  WARNING: every fake here was chosen by a human's eyes or ears. Any")
        print("  band-edge measure scored on this corpus is scored against the sense")
        print("  that selected it, and will read better than it is.")
    if not referee:
        print("\n  WARNING: no referee-grade label in the corpus. Nothing here is ground")
        print("  truth for a spectral axis yet.")


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

    _print_selection_breakdown(fakes, rate)

    if len(fakes) < 30:
        print(f"\n  n={len(fakes)} fakes is too few to quote publicly. Provir's wild "
              "row is 53 — of which only 6 are referee-grade, so the honest target is "
              "referee rows, not files.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Flat CSV of the adjudicated part, for joining against other measurements."""
    records = load()
    rows = [r for r in records.values() if r["adjudication"]["label"] != "undecided"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "sha256", "label", "basis", "referee", "selection", "scope",
            "verdict", "score", "families", "version"])
        writer.writeheader()
        for record in sorted(rows, key=lambda r: r["sha256"]):
            last = record["verdicts"][-1] if record["verdicts"] else {}
            writer.writerow({
                "sha256": record["sha256"],
                "label": record["adjudication"]["label"],
                "basis": record["adjudication"]["basis"] or "",
                "referee": int(bool(record["adjudication"].get("referee"))),
                "selection": record["adjudication"].get("selection") or "",
                "scope": record["adjudication"].get("scope") or "file",
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
    adj.add_argument("--selection",
                     help="how the file entered the pool — NOT how it was settled. "
                          "A pipeline chains with '+', e.g. detector+human_eye")
    adj.add_argument("--scope", choices=("file", "group"), default="file",
                     help="was THIS file examined, or does the ruling extend from "
                          "a group? group requires --note")
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
