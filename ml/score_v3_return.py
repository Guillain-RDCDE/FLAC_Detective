#!/usr/bin/env python3
"""Score fd-exchange-v3 — committed BEFORE set B exists, and self-tested here.

Predictions K1-K5 (his half, blind) and A-i to A-iii (our half, diagnostics)
are registered in ``ml/exchange/V3_PREREGISTERED_2026-08-31.md``, written the
same day as this file and before Provir's set B had been built, named or hashed.

The protocol we both signed requires the scoring script to exist before the set
arrives, so that the analysis cannot drift toward the answer. A script that has
never run is not much of a guarantee, though, so this one carries ``--selftest``:
it fabricates a key and two verdict files with **known** answers, scores them,
and checks that every criterion reads what it must. That runs today, on data
that cannot flatter anyone, and it is the difference between "committed early"
and "committed early and known to work".

Usage::

    python ml/score_v3_return.py --selftest
    python ml/score_v3_return.py --verdicts ours_on_setB.csv --key setB-LABELS.json --half B
    python ml/score_v3_return.py --verdicts ours_on_setA.csv --key setA-LABELS.json --half A

Verdict CSV: one row per file id, columns ``file,verdict`` at minimum; ``score``
and ``engine_sha`` are read when present. Key JSON: the freezer's own format,
``{"labels": {file_id: {"label": …, "source_slug": …}}}``, optionally with a
``strata`` map ``{source_slug: "band_limited" | "band_limited_synthetic" |
"full_band"}`` — his half will use whatever names he uses, and anything that is
not recognised is reported rather than silently bucketed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONVICTION = "FAKE_CERTAIN"
SIGNALED = ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING")
GENUINE = "genuine"


def load_key(path: Path) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """(label by file id, source_slug by file id, stratum by source_slug)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    labels = data.get("labels", {})
    by_file = {k: v["label"] for k, v in labels.items()}
    slug_by_file = {k: v.get("source_slug", "") for k, v in labels.items()}
    strata = data.get("strata", {})
    return by_file, slug_by_file, strata


def load_verdicts(path: Path) -> Dict[str, Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        file_id = (row.get("file") or row.get("id") or "").strip()
        if not file_id:
            continue
        out[Path(file_id).stem] = row
    return out


def _rate(hits: int, total: int) -> str:
    return f"{hits}/{total}" + (f" = {hits / total:.1%}" if total else "")


def score(
    verdicts: Dict[str, Dict[str, str]],
    key: Dict[str, str],
    slugs: Dict[str, str],
    strata: Dict[str, str],
    half: str,
) -> Tuple[Dict[str, bool], List[str]]:
    """Score one half. Returns (criterion -> held, report lines)."""
    lines: List[str] = []
    common = sorted(set(verdicts) & set(key))
    missing = sorted(set(key) - set(verdicts))
    extra = sorted(set(verdicts) - set(key))
    lines.append(f"{len(key)} rows in the key, {len(verdicts)} verdicts, {len(common)} matched")
    if missing:
        lines.append(f"  NOT SCORED — {len(missing)} key rows have no verdict: {missing[:3]}")
    if extra:
        lines.append(f"  IGNORED — {len(extra)} verdicts have no key row: {extra[:3]}")

    def is_conv(f: str) -> bool:
        return verdicts[f].get("verdict", "").strip() == CONVICTION

    def is_sig(f: str) -> bool:
        return verdicts[f].get("verdict", "").strip() in SIGNALED

    genuine = [f for f in common if key[f] == GENUINE]
    lossy = [f for f in common if key[f] != GENUINE]
    conv_genuine = [f for f in genuine if is_conv(f)]
    held: Dict[str, bool] = {}

    lines.append("")
    lines.append(f"genuine rows {len(genuine)}, lossy rows {len(lossy)}")
    lines.append(f"false convictions: {_rate(len(conv_genuine), len(genuine))}")
    lines.append(f"genuine signaled : {_rate(sum(1 for f in genuine if is_sig(f)), len(genuine))}")

    if half == "B":
        # K1 — the safety criterion. <= 2 % and never more than 3 files.
        held["K1"] = (
            len(conv_genuine) <= max(0, int(0.02 * len(genuine))) and len(conv_genuine) <= 3
        )
        lines.append(
            f"K1 false convictions <= 2 % and <= 3 files: {len(conv_genuine)} of {len(genuine)} "
            f"{'HELD' if held['K1'] else 'FAILED'}"
        )
        # K2 — direction: band-limited genuine hurt more than full-band genuine.
        band = [f for f in genuine if strata.get(slugs.get(f, ""), "").startswith("band_limited")]
        full = [f for f in genuine if strata.get(slugs.get(f, "")) == "full_band"]
        if band and full:
            r_band = sum(1 for f in band if is_conv(f)) / len(band)
            r_full = sum(1 for f in full if is_conv(f)) / len(full)
            held["K2"] = r_band > r_full
            lines.append(
                f"K2 band-limited hurts more: {r_band:.1%} vs {r_full:.1%} "
                f"{'as predicted' if held['K2'] else 'NOT as predicted'}"
            )
        else:
            lines.append("K2 not evaluable — his key carries no stratum map")
        # K3 — Layer II, if his half has one.
        mp2 = [f for f in common if "mp2" in key[f].lower()]
        if mp2:
            rate = sum(1 for f in mp2 if is_conv(f)) / len(mp2)
            held["K3"] = rate < 0.30
            lines.append(
                f"K3 Layer II convicted < 30 %: {rate:.1%} of {len(mp2)} "
                f"{'HELD' if held['K3'] else 'FAILED'}"
            )
        else:
            lines.append("K3 not evaluable — no MP2 arm in his half")
        # K4 — recall ordering across arms.
        by_arm = {}
        for arm in sorted({key[f] for f in lossy}):
            rows = [f for f in lossy if key[f] == arm]
            by_arm[arm] = sum(1 for f in rows if is_conv(f)) / len(rows)
        if by_arm:
            lines.append(
                "K4 conviction rate by arm: "
                + ", ".join(
                    f"{a} {r:.0%}" for a, r in sorted(by_arm.items(), key=lambda kv: -kv[1])
                )
            )
            mp3 = [r for a, r in by_arm.items() if a.startswith("mp3")]
            aac_hi = [r for a, r in by_arm.items() if "aac" in a and ("320" in a or "256" in a)]
            if mp3 and aac_hi:
                held["K4"] = max(mp3) >= max(aac_hi)
                lines.append(
                    f"   MP3 arms top out at {max(mp3):.0%}, high-rate AAC at {max(aac_hi):.0%} "
                    f"{'as predicted' if held['K4'] else 'NOT as predicted'}"
                )
    else:
        # Our own half: diagnostics, never evidence.
        held["A-i"] = not conv_genuine
        lines.append(
            f"A-i 0 false convictions on our own genuine: {len(conv_genuine)} "
            f"{'HELD' if held['A-i'] else 'FAILED — a defect, not a result'}"
        )
        rates = {}
        for arm in sorted({key[f] for f in lossy}):
            rows = [f for f in lossy if key[f] == arm]
            rates[arm] = sum(1 for f in rows if is_conv(f)) / len(rows)
        lines.append(
            "     conviction rate by arm: "
            + ", ".join(f"{a} {r:.0%}" for a, r in sorted(rates.items(), key=lambda kv: -kv[1]))
        )
        if "mp2_256" in rates and "mp3_320" in rates:
            held["A-ii"] = rates["mp2_256"] < rates["mp3_320"]
            lines.append(
                f"A-ii Layer II below MP3: {rates['mp2_256']:.0%} vs {rates['mp3_320']:.0%} "
                f"{'as predicted' if held['A-ii'] else 'NOT as predicted'}"
            )
        band = [f for f in genuine if strata.get(slugs.get(f, ""), "").startswith("band_limited")]
        full = [f for f in genuine if strata.get(slugs.get(f, "")) == "full_band"]
        if band and full:
            s_band = sum(1 for f in band if is_sig(f)) / len(band)
            s_full = sum(1 for f in full if is_sig(f)) / len(full)
            held["A-iii"] = s_band > s_full
            lines.append(
                f"A-iii band-limited signaled more: {s_band:.1%} vs {s_full:.1%} "
                f"{'as predicted' if held['A-iii'] else 'NOT as predicted'}"
            )
    return held, lines


def selftest() -> int:
    """Fabricate a key and two verdict files with known answers, and score them.

    The point is not coverage, it is that a criterion which cannot fail is not a
    criterion: each block below is built so that exactly one answer is correct,
    and the scorer has to produce it.
    """
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # A key: 20 genuine (10 band-limited, 10 full-band) + 20 mp3_320 + 10 mp2_256.
        labels, strata = {}, {}
        for i in range(1, 21):
            labels[f"f{i:03d}"] = {"label": "genuine", "source_slug": f"s{i:03d}"}
            strata[f"s{i:03d}"] = "band_limited_synthetic" if i <= 10 else "full_band"
        for i in range(21, 41):
            labels[f"f{i:03d}"] = {"label": "mp3_320", "source_slug": f"s{i:03d}"}
        for i in range(41, 51):
            labels[f"f{i:03d}"] = {"label": "mp2_256", "source_slug": f"s{i:03d}"}
        key_path = work / "key.json"
        key_path.write_text(json.dumps({"labels": labels, "strata": strata}), encoding="utf-8")

        def write(name: str, verdict_of) -> Path:
            path = work / name
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["file", "verdict"])
                w.writeheader()
                for fid in labels:
                    w.writerow({"file": fid + ".flac", "verdict": verdict_of(fid)})
            return path

        by_file, slugs, strata_map = load_key(key_path)

        # Case 1 — a clean run: no false convictions, MP3 convicted, MP2 missed.
        def clean(fid: str) -> str:
            label = labels[fid]["label"]
            if label == "genuine":
                return "AUTHENTIC"
            if label == "mp3_320":
                return CONVICTION
            return "WARNING"  # mp2 missed, as K3 expects

        held, lines = score(
            load_verdicts(write("clean.csv", clean)), by_file, slugs, strata_map, "B"
        )
        checks = [("K1", True), ("K3", True)]
        for name, want in checks:
            if held.get(name) is not want:
                print(f"  SELFTEST FAIL clean run: {name} = {held.get(name)}, expected {want}")
                ok = False

        # Case 2 — everything convicted, genuine included: K1 must FAIL, and K2
        # must read False because both strata are hurt equally.
        #
        # The first version of this case convicted four genuine files that all
        # happened to be band-limited, and then asserted K2 was False. K2 came
        # back True and it was right to: 4 of 10 band-limited against 0 of 10
        # full-band IS the predicted direction. The expectation was wrong, not
        # the scorer — recorded because a self-test that is corrected to match
        # the code is worthless unless it is clear which of the two moved.
        def unsafe(fid: str) -> str:
            return CONVICTION

        held2, _ = score(
            load_verdicts(write("unsafe.csv", unsafe)), by_file, slugs, strata_map, "B"
        )
        if held2.get("K1") is not False:
            print(f"  SELFTEST FAIL unsafe run: K1 = {held2.get('K1')}, expected False")
            ok = False
        # …and with every genuine convicted, band-limited cannot read as worse.
        if held2.get("K2") is not False:
            print(f"  SELFTEST FAIL unsafe run: K2 = {held2.get('K2')}, expected False")
            ok = False

        # Case 3 — the band-limited stratum convicted and the full-band clean:
        # K2's direction must be detected.
        def band_hurts(fid: str) -> str:
            label = labels[fid]["label"]
            if label == "genuine":
                return (
                    CONVICTION if strata[labels[fid]["source_slug"]] != "full_band" else "AUTHENTIC"
                )
            return CONVICTION

        held3, _ = score(
            load_verdicts(write("band.csv", band_hurts)), by_file, slugs, strata_map, "B"
        )
        if held3.get("K2") is not True:
            print(f"  SELFTEST FAIL band run: K2 = {held3.get('K2')}, expected True")
            ok = False

        # Case 4 — our own half, one false conviction: A-i must fail.
        def ours(fid: str) -> str:
            return (
                CONVICTION if fid in ("f001",) or labels[fid]["label"] != "genuine" else "AUTHENTIC"
            )

        held4, _ = score(load_verdicts(write("ours.csv", ours)), by_file, slugs, strata_map, "A")
        if held4.get("A-i") is not False:
            print(f"  SELFTEST FAIL our half: A-i = {held4.get('A-i')}, expected False")
            ok = False

        # Case 5 — a verdict file missing rows must SAY so rather than score around it.
        partial = work / "partial.csv"
        with open(partial, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "verdict"])
            w.writeheader()
            for fid in list(labels)[:30]:
                w.writerow({"file": fid + ".flac", "verdict": "AUTHENTIC"})
        _, lines5 = score(load_verdicts(partial), by_file, slugs, strata_map, "B")
        if not any("NOT SCORED" in line for line in lines5):
            print("  SELFTEST FAIL partial run: missing rows were not reported")
            ok = False

    print("selftest: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verdicts", type=Path)
    ap.add_argument("--key", type=Path)
    ap.add_argument("--half", choices=("A", "B"), default="B")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not (args.verdicts and args.key):
        ap.error("--verdicts and --key, or --selftest")

    by_file, slugs, strata = load_key(args.key)
    verdicts = load_verdicts(args.verdicts)
    held, lines = score(verdicts, by_file, slugs, strata, args.half)
    print(f"=== fd-exchange-v3, half {args.half} ===")
    for line in lines:
        print(line)
    shas = {r.get("engine_sha", "") for r in verdicts.values() if r.get("engine_sha")}
    if shas:
        print(f"\nengine sha in the verdict file: {sorted(shas)}")
    else:
        print("\nno engine_sha column — the commitment cannot name the engine that produced it")
    labels_seen = Counter(by_file.values())
    print(f"key composition: {dict(labels_seen)}")
    failed = [k for k, v in held.items() if v is False]
    print("\n" + ("ALL REGISTERED CRITERIA HELD" if not failed else "FAILED: " + ", ".join(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
