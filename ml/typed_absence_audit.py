#!/usr/bin/env python3
"""The typed-absence audit: no measurement may be tested for truth.

Why this exists
---------------
Provir reported on 2026-08-29 that a guard reading, in effect,

    (edge_std or 999) < 160

turns a measured standard deviation of **0.0** into the sentinel, so the file
reads as outside the stability window on the coercion rather than on the
measurement. A zero standard deviation is a legitimate reading -- it means every
window agreed -- and it is arguably the strongest evidence for an edge, not the
weakest.

That guard is not in this tree (see AUDIT RESULT below), but the *species* is
ours as much as his, and it has now been recorded three times across the two
engines in one week:

* his ``width`` field returning a magic ``1500.0`` when no 30 dB drop is found
  -- a sentinel living in a numeric field, indistinguishable from a measurement
  to any caller (his disclosure, 2026-08-20);
* our ``detect_cutoff`` returning Nyquist for three different conditions, which
  is why :class:`~flac_detective.analysis.spectrum.EdgeReading` exists at all;
* his ``edge_std`` coercion above.

So the rule is registered instead of the fix, because the fix is one line and
the rule is the asset:

    **An absence is typed. It is never a value, and never a falsy value.**
    Test ``x is None`` (or ``math.isnan``). Never test a measurement for truth,
    and never coerce one with ``or``, because 0.0, 0 and "" are readings.

This script makes that rule auditable rather than asserted. It walks the AST --
not the text -- of every module under ``src/`` and ``ml/`` and reports two
shapes on any identifier that names a measurement:

    A.  ``measurement or <number>``      (truthiness coercion to a sentinel)
    B.  ``if not measurement``           (truthiness test on a reading)

    C.  ``m = np.std(xs) if len(xs) > 1 else 0.0``   (an absence assigned a value)

It is deliberately name-driven and therefore approximate in both directions: it
cannot know that ``ok`` is a flag and ``occ`` is a count. It is a tripwire for
the species, not a type checker.

Shape C was added 2026-08-30, because shapes A and B did not catch our own
fourth instance and Provir's letter did. ``analysis/spectrum.py`` read

    cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0

with ``num_samples = 1`` for any file of 90 seconds or less: the
**not-computable** case returned as the value ``0.0``, consumed by Rule 11's
TEST 11D as "cutoff very stable, suspect digital" for -10, which is enough to
deny a file the -40 cassette protection. An absence, scored, in the direction of
conviction. A clean audit that misses the live instance is worse than no audit,
so the shape that missed it is now part of the tripwire and part of its control.

AUDIT RESULT, 2026-08-29, v1.13.0
---------------------------------
**0 findings across 148 modules of src/ and ml/**, with the tripwire verified
against its control first: 4 of 4 caught on the must-fire block (the reported
guard included), 0 false positives on the must-not-fire block. The reported
guard has no counterpart here -- ``opus_edge`` appears nowhere in this tree
except inside the archived copy of his own return CSV
(``ml/exchange/provir_return_v2_2026-08.csv``), where it is his telemetry and
not our code.

Run it as part of a release check::

    python ml/typed_absence_audit.py --selftest # the control; exits 1 on drift
    python ml/typed_absence_audit.py            # exits 1 on any finding
    python ml/typed_absence_audit.py --list     # also print what it inspected
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterator, List, NamedTuple

# Words that name a MEASUREMENT -- a scalar quantity whose zero is a reading.
# Matched against the LAST underscore-separated part of the identifier, because
# that is where the quantity lives: ``edge_std``, ``dead_max_run``, ``width_hz``.
#
# Matching the last part rather than any substring is what keeps the plural out:
# ``cutoffs`` and ``rates`` are collections, and an empty collection IS a
# legitimate absence -- ``if not cutoffs`` is correct code. So is ``running``,
# which merely contains "run". The first version of this script matched
# substrings anywhere and returned 11 findings, all of them collections, bools
# or module constants: the same defect it exists to catch, in its own filter.
MEASUREMENT_WORDS = frozenset(
    {
        "std",
        "width",
        "hz",
        "khz",
        "freq",
        "frequency",
        "cutoff",
        "edge",
        "rolloff",
        "db",
        "dbfs",
        "ratio",
        "corr",
        "depth",
        "floor",
        "margin",
        "score",
        "run",
        "occ",
        "count",
        "n",
        "delta",
        "distance",
        "phase",
        "entropy",
        "flatness",
        "energy",
        "duration",
        "offset",
        "bitrate",
        "kbps",
        "rate",
        "mean",
        "median",
        "var",
        "rms",
        "snr",
        "auc",
        "seconds",
        "ms",
        "pct",
    }
)

# Prefixes that mark a name as a PREDICATE. ``not has_low_cutoff`` is correct
# code; only a reading may not be tested for truth.
BOOLEAN_PREFIXES = ("is_", "has_", "was_", "can_", "should_", "found", "ok", "valid")


class Finding(NamedTuple):
    path: Path
    line: int
    shape: str
    name: str
    source: str

    def __str__(self) -> str:  # pragma: no cover - presentation only
        return f"{self.path}:{self.line}: [{self.shape}] {self.source.strip()}"


def _name_of(node: ast.AST) -> str | None:
    """The dotted name of a Name/Attribute node, or None for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name_of(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _is_measurement(name: str | None) -> bool:
    if not name:
        return False
    leaf = name.rsplit(".", maxsplit=1)[-1]
    if leaf.isupper():
        return False  # a module constant, not a reading
    leaf = leaf.lower()
    if leaf.startswith(BOOLEAN_PREFIXES):
        return False
    return leaf.split("_")[-1].rstrip("0123456789") in MEASUREMENT_WORDS


def _is_number(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return not isinstance(node.value, bool)
    # -1, -999: a sentinel is as often negative as it is large.
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _is_number(node.operand)
    return False


def _tests_computability(node: ast.AST) -> bool:
    """True for a test that asks whether a statistic CAN be computed.

    ``len(xs) > 1``, ``len(xs) >= 2``, ``xs.size > 0``, ``n > 1``. The point of
    shape C is exactly this pairing: a guard that admits the statistic is
    undefined, married to a numeric value in the else. Anything else -- a
    threshold on a measurement, a flag -- is not it.
    """
    if not isinstance(node, ast.Compare):
        return False
    left = node.left
    is_len = (
        isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len"
    )
    is_size = isinstance(left, ast.Attribute) and left.attr in ("size", "shape")
    leaf = (_name_of(left) or "").rsplit(".", maxsplit=1)[-1].lower()
    is_count = leaf in ("n", "count", "n_windows", "n_chunks", "nsamples", "num_samples")
    if not (is_len or is_size or is_count):
        return False
    return any(isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) for op in node.ops)


def audit_source(path: Path, text: str) -> Iterator[Finding]:  # noqa: C901
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return  # not ours to judge; the test suite catches broken modules
    lines = text.splitlines()

    def src(node: ast.AST) -> str:
        i = getattr(node, "lineno", 1) - 1
        return lines[i] if 0 <= i < len(lines) else ""

    for node in ast.walk(tree):
        # Shape A: measurement or <number>
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            for left, right in zip(node.values, node.values[1:]):
                name = _name_of(left)
                if _is_measurement(name) and _is_number(right):
                    yield Finding(path, node.lineno, "A: or-sentinel", name or "?", src(node))
        # Shape B: not measurement
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            name = _name_of(node.operand)
            if _is_measurement(name):
                yield Finding(path, node.lineno, "B: not-measurement", name or "?", src(node))
        # Shape C: measurement = <expr> if <computability test> else <number>
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [_name_of(t) for t in targets]
            if not any(_is_measurement(n) for n in names):
                continue
            value = node.value
            if (
                isinstance(value, ast.IfExp)
                and _is_number(value.orelse)
                and _tests_computability(value.test)
            ):
                yield Finding(
                    path,
                    node.lineno,
                    "C: absence-as-value",
                    next(n for n in names if _is_measurement(n)) or "?",
                    src(node),
                )


def iter_modules(roots: List[Path]) -> Iterator[Path]:
    skip = {"build", "dist", "__pycache__", ".mypy_cache", ".pytest_cache", "htmlcov"}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if any(part in skip for part in path.parts):
                continue
            yield path


# The control. A clean audit means nothing unless the tripwire is known to fire,
# so it is run against the reported guard itself plus the shapes that must NOT
# fire. Same discipline as any probe here: validate against a control that does
# not share the instrument's defect.
SELFTEST_MUST_FIRE = """
window_ok = (edge_std or 999) < 160          # the guard Provir reported
if not edge_std: return None                 # same coercion, other shape
w = telemetry.width_hz or 1500.0             # his own sentinel, our spelling
depth = residual_floor_db or -999
cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0
seam_db = compute(x) if xs.size > 0 else -999
"""

SELFTEST_MUST_NOT_FIRE = """
if not cutoffs: return None                  # a collection: empty IS absence
if not MUTAGEN_AVAILABLE: return None        # a module constant
if not has_low_cutoff: return None           # a predicate
if not running: return None                  # a flag that merely contains "run"
if not r.stdout: return None
name = label or "unknown"                    # a string default, not a reading
cutoff_std = float(np.std(xs)) if len(xs) > 1 else float("nan")   # the repair
width_hz = measure(xs) if cutoff_hz < 19000 else 0.0   # a domain gate, not computability
labels = collect(xs) if len(xs) > 1 else []             # a collection default
"""


def selftest() -> int:
    fired = list(audit_source(Path("<must-fire>"), SELFTEST_MUST_FIRE))
    quiet = list(audit_source(Path("<must-not-fire>"), SELFTEST_MUST_NOT_FIRE))
    print(f"control: {len(fired)}/6 caught, {len(quiet)} false positive(s)")
    for finding in fired:
        print(f"  caught  {finding.source.strip()}")
    for finding in quiet:
        print(f"  WRONGLY caught  {finding.source.strip()}")
    ok = len(fired) == 6 and not quiet
    print("selftest: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "roots",
        nargs="*",
        default=["src", "ml"],
        help="directories to audit (default: src ml)",
    )
    parser.add_argument("--list", action="store_true", help="print each file inspected")
    parser.add_argument(
        "--selftest", action="store_true", help="run the tripwire against its control and exit"
    )
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    repo = Path(__file__).resolve().parent.parent
    roots = [(repo / r) if not Path(r).is_absolute() else Path(r) for r in args.roots]

    findings: List[Finding] = []
    n_files = 0
    for path in iter_modules(roots):
        n_files += 1
        rel = path.relative_to(repo)
        if args.list:
            print(f"  inspected {rel}")
        findings.extend(
            f._replace(path=rel) for f in audit_source(path, path.read_text(encoding="utf-8"))
        )

    print(f"\ntyped-absence audit: {n_files} modules, {len(findings)} finding(s)")
    if not findings:
        print("clean -- no measurement is tested for truth or coerced to a sentinel")
        return 0
    print("\nEach of these turns a legitimate 0.0 / 0 reading into an absence:")
    for finding in findings:
        print(f"  {finding}")
    print("\nFix shape: test `is None` (or math.isnan), never truthiness.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
