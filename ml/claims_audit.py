#!/usr/bin/env python3
"""Distrust stated practice: every public number either has evidence, or is listed.

Where this comes from
---------------------
Provir, 2026-08-20: an automated pass over their own repository, told to distrust
stated practice *on principle rather than on suspicion*, returned a contradiction
list — and a published denominator (634) turned out to have no ledger and no
producing script anywhere. It could not be shown stale, corrected or defended.
Only withdrawn. Their public page also claimed "every published number is
re-derived by an automated harness" while the harness covered 14 of 33 bolded
figures. Nobody was checking, because nobody had reason to doubt.

This is our version of that pass, built to run before every release.

What it does
------------
1. Inventories every **bolded numeric claim** in the public-facing documents
   (README, docs site pages) — bold is where this project puts the numbers it
   wants believed.
2. Checks each entry of ``ml/claims_register.json``:
   - the claim's pattern still appears in its stated file (else STALE — the prose
     moved and the register did not, which is how his 656-that-became-646 stayed
     honest and his 634 could not);
   - its evidence exists: an artifact path in the repository, or a machine check
     (``json_count``: a JSON file's field must equal the claimed value).
3. Reports every bolded numeric claim NOT covered by the register. An uncovered
   claim is not necessarily wrong — it is unverifiable, which after this week is
   not a distinction worth defending.

Exit code is non-zero on STALE or MISSING-EVIDENCE entries (a wrong register is
worse than none). Uncovered claims are a report, not a failure — the register is
expected to grow toward the prose, release by release.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "ml" / "claims_register.json"

PUBLIC_FILES = [
    "README.md",
    "docs/index.md",
    "docs/technical-details.md",
    "docs/getting-started.md",
    "docs/start-here.md",
]

BOLD_NUMERIC = re.compile(r"\*\*([^*\n]*\d[^*\n]*)\*\*")

# Not claims: bare versions, years, python versions, score-band labels, dates.
NOISE = re.compile(
    r"^(v?\d+\.\d+(\.\d+)?|\d{4}(-\d{2}){0,2}|Python \d.*|≤ ?\d+|≥ ?\d+|\d+–\d+|"
    r"\d+(\.\d+)?x|#\d+)$"
)

# Bold that is structure, not assertion: markdown links, interrogative headings,
# ordinal-prefixed scenario labels ("1. MP3 320 kbps VBR"), and the bare
# "0 points" outcome rows — a bolded zero asserts the absence of an award, and
# what CAN drift there is the nonzero claim beside it, which stays inventoried.
STRUCTURE = re.compile(r"^\[.*\]\(.*\)$|\?$|^\d+\.\s|^0 points$")


def inventory() -> List[dict]:
    """Every bolded numeric claim in the public files."""
    found: List[dict] = []
    for rel in PUBLIC_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in BOLD_NUMERIC.finditer(text):
            claim = match.group(1).strip()
            if NOISE.match(claim) or STRUCTURE.search(claim):
                continue
            found.append({"file": rel, "claim": claim})
    return found


def check_register(entries: List[dict]) -> List[str]:  # noqa: C901
    """Verify each registered claim; return failure strings."""
    failures: List[str] = []
    for entry in entries:
        rel = entry["file"]
        text_path = ROOT / rel
        if not text_path.exists():
            failures.append(f"STALE {entry['id']}: file {rel} does not exist")
            continue
        text = text_path.read_text(encoding="utf-8")
        if not re.search(entry["pattern"], text):
            failures.append(f"STALE {entry['id']}: pattern {entry['pattern']!r} no longer in {rel}")
            continue
        ev = entry.get("evidence", {})
        kind = ev.get("kind")
        if kind == "artifact":
            for artifact in ev["paths"]:
                if not (ROOT / artifact).exists():
                    failures.append(f"MISSING-EVIDENCE {entry['id']}: artifact {artifact} absent")
        elif kind == "rule_count":
            rules_dir = ROOT / "src" / "flac_detective" / "analysis" / "new_scoring" / "rules"
            defs = []
            for py in rules_dir.glob("*.py"):
                defs += re.findall(r"def apply_rule_(\d+)", py.read_text(encoding="utf-8"))
            numbers = set(defs)
            count = len(numbers)
            if ev.get("cnn_excluded"):
                count -= 1 if "12" in numbers else 0
            if count != ev["expected"]:
                failures.append(
                    f"CONTRADICTION {entry['id']}: code defines {count} rules "
                    f"({'CNN excluded' if ev.get('cnn_excluded') else 'all'}), "
                    f"claim says {ev['expected']}"
                )
        elif kind == "json_count":
            data = json.loads((ROOT / ev["path"]).read_text(encoding="utf-8"))
            actual = data
            for key in ev["keys"]:
                actual = actual[key]
            if isinstance(actual, list):
                actual = len(actual)
            if actual != ev["expected"]:
                failures.append(
                    f"CONTRADICTION {entry['id']}: {ev['path']}:{'.'.join(ev['keys'])} "
                    f"= {actual}, claim says {ev['expected']}"
                )
        elif kind == "code_pattern":
            code_path = ROOT / ev["path"]
            if not code_path.exists():
                failures.append(f"MISSING-EVIDENCE {entry['id']}: {ev['path']} absent")
            elif not re.search(ev["regex"], code_path.read_text(encoding="utf-8")):
                failures.append(
                    f"CONTRADICTION {entry['id']}: {ev['regex']!r} not found in {ev['path']}"
                )
        elif kind == "none_yet":
            failures.append(
                f"MISSING-EVIDENCE {entry['id']}: registered with no evidence "
                f"({ev.get('note', 'no note')})"
            )
        else:
            failures.append(f"MISSING-EVIDENCE {entry['id']}: unknown evidence kind {kind!r}")
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-uncovered", action="store_true", help="print every uncovered bolded numeric claim"
    )
    args = parser.parse_args(argv)

    entries = json.loads(REGISTER.read_text(encoding="utf-8")) if REGISTER.exists() else []
    failures = check_register(entries)

    claims = inventory()
    covered = 0
    uncovered: List[dict] = []
    for claim in claims:
        if any(
            e["file"] == claim["file"] and re.search(e["pattern"], f"**{claim['claim']}**")
            for e in entries
        ):
            covered += 1
        else:
            uncovered.append(claim)

    print(
        f"public bolded numeric claims: {len(claims)} "
        f"({covered} covered by the register, {len(uncovered)} not)"
    )
    print(f"register entries: {len(entries)}, failures: {len(failures)}")
    for failure in failures:
        print(f"  {failure}")
    if args.list_uncovered:
        print("\nUNCOVERED (unverifiable until registered):")
        for claim in uncovered:
            print(f"  {claim['file']}: {claim['claim']}")
    if failures:
        print("\nA wrong register is worse than none — fix the failures above.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
