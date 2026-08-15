"""CI guard: no rule ships without a measurement, and no dead rule ships at all.

This exists because of a specific failure. Rule 9's pre-echo test contributed
+15 points to any file that passed its gate, fired on 85 % of transcodes and
83 % of genuine files, and had an AUC of 0.51 — a coin flip. It shipped for a
year. Nothing caught it, because nothing ever measured a rule on its own; only
the twelve-rule total was ever looked at, and inside a total a coin flip is
invisible.

The fix is structural rather than a one-off cleanup:

* ``test_every_rule_is_measured`` — the set of scoring rules in the code must
  equal the set of rules in the committed audit. Add a rule without re-running
  ml/rule_audit.py and CI fails. This is the part that cannot be forgotten.
* ``test_no_dead_rules`` — every rule that actually fires must separate.
* ``test_no_rule_taxes_genuine_files`` — a rule may not hand free points to
  genuine files without earning them, because those points move innocent files
  toward the WARNING threshold.

The audit CSV is committed (``ml/rule_audit_baseline.csv``), so CI needs no audio
corpus. Regenerate it with::

    python ml/build_audit_corpus.py --out <dir> --n 80
    python ml/rule_audit.py score --corpus <dir> --csv ml/rule_audit_baseline.csv
"""

import csv
import importlib
import inspect
from pathlib import Path

import pytest

from flac_detective.analysis.new_scoring.strategies import ScoringRule

AUDIT_CSV = Path(__file__).resolve().parents[1] / "ml" / "rule_audit_baseline.csv"

# A rule firing on fewer files than this is inert rather than harmful: it cannot
# tax many verdicts, and its AUC would be estimated from too few points to mean
# anything. Inert rules are allowed; firing-but-not-separating rules are not.
MIN_FIRE_RATE = 0.10

# |AUC - 0.5| below this is a coin flip. Rule 9's three tests measured 0.013,
# 0.086 and 0.003 away from chance.
MIN_AUC_DISTANCE = 0.05

# Points a rule may hand to genuine files on average without discriminating.
MAX_GENUINE_TAX = 2.0


def _code_rule_names() -> set:
    """Every concrete ScoringRule subclass the pipeline can run."""
    module = importlib.import_module("flac_detective.analysis.new_scoring.strategies")
    return {
        name
        for name, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, ScoringRule) and obj is not ScoringRule and not inspect.isabstract(obj)
    }


def _load_rows():
    """Read the committed audit, or skip if it has not been generated yet."""
    if not AUDIT_CSV.exists():
        pytest.skip(f"no committed audit at {AUDIT_CSV} — run ml/rule_audit.py score")
    with open(AUDIT_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _auc(pos, neg):
    """Mann-Whitney AUC with ties at 0.5."""
    if not pos or not neg:
        return float("nan")
    ordered = sorted([(v, 0) for v in neg] + [(v, 1) for v in pos])
    ranks = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum = sum(r for r, (_, lab) in zip(ranks, ordered) if lab == 1)
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def _per_rule(rows, rule):
    """Return (genuine_values, fake_values) for one rule."""
    gen = [float(r[rule]) for r in rows if r["label"] == "0" and r.get(rule, "") != ""]
    fake = [float(r[rule]) for r in rows if r["label"] == "1" and r.get(rule, "") != ""]
    return gen, fake


def test_audit_csv_is_present_and_non_trivial():
    """The audit must cover both classes, or every assertion below is vacuous."""
    rows = _load_rows()
    assert len(rows) >= 100, f"audit too small to conclude anything: {len(rows)} rows"
    assert sum(1 for r in rows if r["label"] == "0") >= 30, "not enough genuine files"
    assert sum(1 for r in rows if r["label"] == "1") >= 60, "not enough fakes"


def test_every_rule_is_measured():
    """Adding a rule without measuring it must fail CI.

    This is the whole point of the file. A rule that no one has measured is a
    rule no one can defend, and the project has already paid for that once.
    """
    rows = _load_rows()
    measured = {name for name in rows[0] if name.startswith("Rule")}
    in_code = _code_rule_names()
    unmeasured = in_code - measured
    assert not unmeasured, (
        f"these rules exist in the code but not in the committed audit: "
        f"{sorted(unmeasured)}. Re-run ml/rule_audit.py before shipping them."
    )


def test_no_dead_rules():
    """Every rule that fires on a meaningful share of files must separate."""
    rows = _load_rows()
    dead = []
    for rule in sorted(name for name in rows[0] if name.startswith("Rule")):
        gen, fake = _per_rule(rows, rule)
        if not gen or not fake:
            continue
        fire_gen = sum(1 for v in gen if v != 0) / len(gen)
        fire_fake = sum(1 for v in fake if v != 0) / len(fake)
        if max(fire_gen, fire_fake) < MIN_FIRE_RATE:
            continue  # inert, not harmful
        auc = _auc(fake, gen)
        if auc == auc and abs(auc - 0.5) < MIN_AUC_DISTANCE:
            dead.append(f"{rule} (AUC {auc:.3f}, fires {fire_gen:.0%}/{fire_fake:.0%})")
    assert not dead, "rules that fire without separating: " + "; ".join(dead)


def test_no_rule_taxes_genuine_files():
    """A rule may not push genuine files toward WARNING for free.

    Rule 9 added +15 to any genuine file that passed its gate. With the WARNING
    bar at 31 that made the effective bar 16 for those files — a silent halving
    of the evidence needed to flag someone's legitimate purchase.
    """
    rows = _load_rows()
    offenders = []
    for rule in sorted(name for name in rows[0] if name.startswith("Rule")):
        gen, fake = _per_rule(rows, rule)
        if not gen or not fake:
            continue
        mean_gen = sum(gen) / len(gen)
        if mean_gen <= MAX_GENUINE_TAX:
            continue
        auc = _auc(fake, gen)
        # Points given to genuine files are only acceptable from a rule that is
        # genuinely discriminating — it will be giving fakes far more.
        if auc != auc or abs(auc - 0.5) < MIN_AUC_DISTANCE:
            offenders.append(f"{rule} (+{mean_gen:.1f} avg on genuine, AUC {auc:.3f})")
    assert not offenders, "rules taxing genuine files without discriminating: " + "; ".join(
        offenders
    )


def test_no_conviction_rests_on_a_single_evidence_family():
    """The composition guard — Jamie Dodd's sibling to "no unmeasured rule ships".

    "No unmeasured RULE ships" was not enough. A score is a sum, and a sum cannot
    say whether it came from one thing repeated or several things agreeing. In the
    v1.8 audit every false conviction, and every conviction on the 320 kbps MP3
    arm, was Rules 1 and 3 at +50 each — one bitrate inference counted twice.

    This reads the committed audit and fails if any file was convicted on a single
    family. It is a property of the shipped corpus, not of a mock, so it also
    catches the case where a future rule quietly joins an existing family and
    starts convicting through it.
    """
    rows = _load_rows()
    if "families" not in rows[0]:
        pytest.skip("audit predates the families column — re-run ml/rule_audit.py score")

    offenders = [
        r for r in rows if r["verdict"] == "FAKE_CERTAIN" and len(r["families"].split("+")) < 2
    ]
    assert not offenders, (
        f"{len(offenders)} file(s) convicted on a single evidence family, e.g. "
        f"{offenders[0]['slug']} (families={offenders[0]['families']!r}, "
        f"score={offenders[0]['score']}). One source cannot corroborate itself."
    )


def test_no_genuine_file_is_convicted():
    """The number that actually matters, asserted rather than hoped for."""
    rows = _load_rows()
    convicted = [r for r in rows if r["label"] == "0" and r["verdict"] == "FAKE_CERTAIN"]
    assert not convicted, (
        f"{len(convicted)} certified-genuine file(s) convicted: "
        f"{[r['slug'] for r in convicted][:3]}"
    )
