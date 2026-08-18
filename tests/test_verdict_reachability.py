"""Structural guard: a conviction may only be produced inside the corroboration gate.

Why an AST test and not another table of inputs
-----------------------------------------------
Jamie Dodd of Provir spent a week on a corroboration bug, wrote the repair, and
then found the same file still convicting a lawful record. The repair was correct —
over the offending flag set the predicate returned "not corroborated", exactly as
designed. **It was simply never called on the path that convicted.** The line that
actually produced the verdict was an inline copy of the rule with no corroboration
test at all, three screens from a comment that described what was supposed to run.
Twenty-five unit cases were green over the predicate the entire time.

His conclusion, and it applies to this engine exactly as much as to his:

    A table of inputs cannot catch a function that is not called.

Every corroboration test in this repository is of that kind. They feed rule scores
in and check the verdict that comes out, which proves the gate works *when reached*
and says nothing about whether some future branch reaches past it. This file asks
the structural question instead: is there anywhere in the scoring package that can
produce a conviction without going through the gate?

The check is deliberately narrow. It does not try to prove the gate is *correct* —
other tests do that — only that it is the sole producer.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

SCORING = Path(__file__).resolve().parent.parent / "src" / "flac_detective" / "analysis"

CONVICTION = "FAKE_CERTAIN"

# The one function allowed to produce it, and the module it must live in.
GATE_FUNCTION = "determine_verdict"
GATE_MODULE = "verdict.py"

# What the gate must consult. If a rename makes these stale the test fails, which
# is the intended behaviour: the gate's dependency on corroboration is the thing
# being pinned, so it should not be silently renameable.
GATE_MUST_REFERENCE = ("families", "CONVICTION_MIN_FAMILIES")


def _producers() -> List[Tuple[Path, int, str]]:
    """Every place the conviction string is produced, with its enclosing function.

    "Produced" means the literal appears in a ``return`` or an assignment — not in
    a comparison, a lookup table or a display map, which consume a verdict someone
    else decided. That distinction is the whole point: the danger is a second
    ORIGIN, not a second reader.
    """
    found: List[Tuple[Path, int, str]] = []
    for path in sorted(SCORING.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        # Map each node to its enclosing function by walking function bodies.
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for inner in ast.walk(node):
                produced = False
                if isinstance(inner, ast.Return) and inner.value is not None:
                    produced = _mentions(inner.value)
                elif isinstance(inner, ast.Assign):
                    produced = _mentions(inner.value)
                if produced:
                    found.append((path, inner.lineno, node.name))
    return found


def _mentions(node: ast.AST) -> bool:
    """True if the conviction literal appears anywhere in this expression."""
    return any(
        isinstance(child, ast.Constant) and child.value == CONVICTION for child in ast.walk(node)
    )


def test_only_one_function_can_produce_a_conviction() -> None:
    """No second origin for FAKE_CERTAIN anywhere in the scoring package."""
    producers = _producers()
    assert producers, (
        f"no code produces {CONVICTION!r} at all — this test has stopped testing "
        "anything. The literal was probably renamed or moved to a constant; point "
        "CONVICTION at whatever replaced it."
    )
    outside = [
        (path.name, line, func)
        for path, line, func in producers
        if not (path.name == GATE_MODULE and func == GATE_FUNCTION)
    ]
    assert not outside, (
        f"{CONVICTION} is produced outside {GATE_MODULE}:{GATE_FUNCTION} at "
        f"{outside}. Even if that site checks corroboration today, a second origin "
        "is how Provir's eighth corroboration bug survived its own repair: the fix "
        "went into a predicate the convicting path never called, and a table of "
        "inputs could not see it. Route the verdict through the gate instead."
    )


def test_the_gate_actually_consults_corroboration() -> None:
    """The sole producer must reference the corroboration inputs, not just exist.

    Guards against the degenerate pass: one producer, in the right place, that has
    quietly stopped looking at the families.
    """
    path = SCORING / "new_scoring" / GATE_MODULE
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    gate = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == GATE_FUNCTION
        ),
        None,
    )
    assert gate is not None, f"{GATE_FUNCTION} not found in {path}"

    names = {
        child.id if isinstance(child, ast.Name) else child.attr
        for child in ast.walk(gate)
        if isinstance(child, (ast.Name, ast.Attribute))
    }
    missing = [token for token in GATE_MUST_REFERENCE if token not in names]
    assert not missing, (
        f"{GATE_FUNCTION} no longer references {missing}. It is the only function "
        "allowed to convict, so if it has stopped consulting corroboration then "
        "nothing else is going to."
    )


# ===================== reachability, Provir's second lesson ===================
#
# The AST test above answers "is there a second origin?". This one answers a
# different question that Jamie Dodd paid for separately:
#
#     Reachability is by enclosing function, not by line order.
#
# Gating an inline conviction site handed his gate five fresh non-witnesses that
# had been appended between the old call sites and the new one — including a
# rung's own "I applied and declined to fire" telemetry, two lines above a
# predicate that then read it as evidence. Without barring those the gate was
# nearly inert. And he nearly barred four flags of the same apparent species that
# turned out to be emitted by a function running AFTER every gate — where an
# exclusion is pure dressing.
#
# This engine has the same shape. `calculate_score` evaluates the corroboration
# gate at three points, and each sees a DIFFERENT set of families, because the
# rules that could corroborate run further down. Short-circuit 1 fires before
# Rules 7, 12 and 13 exist at all, so no amount of correctness in the gate makes
# `cnn` or `mdct` available there.
#
# That is intended. What is not acceptable is for it to change silently — moving
# one rule above a gate, or one gate below a rule, alters which families can
# corroborate without touching the gate's own code.

GATE_CALL = "_is_corroborated"
SCORER = "new_scoring/calculator.py"
PIPELINE_FUNCTION = "_apply_scoring_rules"

# Families whose rules may have run before each gate, in source order.
# An UPPER BOUND: a rule above a gate might still be skipped by a condition, but a
# rule below it definitely has not run. That asymmetry is what makes the bound
# sound and the test meaningful.
EXPECTED_REACHABLE = [
    # Short-circuit 1: the fast rules only. Rules 7, 12 and 13 have not run, so
    # `silence`, `cnn` and `mdct` cannot corroborate here however correct the gate
    # is. That is deliberate — and it is exactly why the early exit had to start
    # requiring corroboration in v1.9, or it would have measured itself.
    {"spectral", "container"},
    # Short-circuit 3: after Rule 7 and Rule 13, before Rule 12.
    {"spectral", "container", "silence", "mdct"},
]


def _rules_by_function(tree: ast.AST) -> dict:
    """Rule classes instantiated inside each function, by function name."""
    from flac_detective.analysis.new_scoring.evidence import RULE_FAMILY

    inside: dict = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        names = {
            child.func.id
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id in RULE_FAMILY
        }
        if names:
            inside[node.name] = names
    return inside


def _terminal(body: List[ast.stmt]) -> bool:
    """Does this block end by leaving the function?"""
    return bool(body) and isinstance(body[-1], (ast.Return, ast.Raise))


def _collect(node: ast.AST, inside: dict, entry: str, out: List[Tuple[int, str]]) -> None:
    """Record rule positions in one statement, without descending into branches."""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Name):
            continue
        name = child.func.id
        if name in inside.get(entry, set()):
            out.append((child.lineno, name))
        elif name in inside and name != entry:
            for rule in sorted(inside[name]):
                out.append((child.lineno, rule))


def _walk_reachable(
    body: List[ast.stmt], inside: dict, entry: str, out: List[Tuple[int, str]]
) -> None:
    """Collect rule positions along paths that can still reach later statements.

    A branch ending in ``return`` cannot flow to a gate further down the function,
    so the rules it runs are not reachable *there* even though they are written
    above it. Recursing past those blocks — rather than collecting and subtracting —
    is the difference between a loose upper bound and a statement about execution.

    This is Jamie Dodd's warning applied three times, and it caught this test three
    times: a helper written above its call site; a terminal branch written above a
    gate it exits before reaching; and then that same branch nested one level
    deeper than the first attempt looked. Each looked "earlier" by line number and
    none was earlier in execution.
    """
    for stmt in body:
        if isinstance(stmt, ast.If):
            # The test itself is part of the straight-line path.
            _collect(stmt.test, inside, entry, out)
            for branch in (stmt.body, stmt.orelse):
                if not _terminal(branch):
                    _walk_reachable(branch, inside, entry, out)
        elif isinstance(stmt, ast.Try):
            # The scoring pipeline's whole body lives inside a try/finally, so
            # failing to descend here collected the function wholesale — terminal
            # branches included — which is how the third version of this test still
            # reported cnn as reachable at a gate the branch returns before.
            for block in (stmt.body, stmt.orelse, stmt.finalbody):
                _walk_reachable(block, inside, entry, out)
            for handler in stmt.handlers:
                _walk_reachable(handler.body, inside, entry, out)
        elif isinstance(stmt, (ast.For, ast.While)):
            _collect(stmt.iter if isinstance(stmt, ast.For) else stmt.test, inside, entry, out)
            _walk_reachable(stmt.body, inside, entry, out)
            _walk_reachable(stmt.orelse, inside, entry, out)
        elif isinstance(stmt, ast.With):
            _walk_reachable(stmt.body, inside, entry, out)
        else:
            _collect(stmt, inside, entry, out)


def _rule_positions(tree: ast.AST, entry: str) -> List[Tuple[int, str]]:
    """(execution position, rule class) for every rule that can reach later code.

    Position is the line at which the rule can first have run, which is NOT the
    line where it is written: a rule instantiated inside a helper runs where the
    HELPER IS CALLED, and helpers are defined above their callers.
    """
    inside = _rules_by_function(tree)
    scorer = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == entry),
        None,
    )
    assert scorer is not None, f"{entry} not found"
    out: List[Tuple[int, str]] = []
    _walk_reachable(scorer.body, inside, entry, out)
    return sorted(set(out))


def test_families_reachable_at_each_gate_are_declared() -> None:
    """Moving a rule across a gate must break a declared fact, not pass quietly.

    The two in-pipeline gates live in ``_apply_scoring_rules``; the final verdict is
    computed in ``new_calculate_score`` once that function has returned, so by then
    every rule has had its chance and all five families are reachable.
    """
    from flac_detective.analysis.new_scoring.evidence import RULE_FAMILY

    path = SCORING / "new_scoring" / "calculator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    scorer = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == PIPELINE_FUNCTION
    )
    rules = _rule_positions(tree, PIPELINE_FUNCTION)
    gates = sorted(
        node.lineno
        for node in ast.walk(scorer)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == GATE_CALL
    )

    assert len(gates) == len(EXPECTED_REACHABLE), (
        f"{SCORER} now evaluates corroboration at {len(gates)} points inside "
        f"{PIPELINE_FUNCTION}, not {len(EXPECTED_REACHABLE)}. Every evaluation point "
        "sees its own family set; declare what a new one can reach rather than "
        "assuming it matches another."
    )

    for gate, expected in zip(gates, EXPECTED_REACHABLE):
        reachable = {RULE_FAMILY[name] for line, name in rules if line < gate}
        assert reachable == expected, (
            f"at line {gate} the reachable families are {sorted(reachable)}, "
            f"declared {sorted(expected)}. A rule moved across a corroboration gate "
            "changes which families can corroborate there without any edit to the "
            "gate itself — Provir's gate was left nearly inert exactly this way. "
            "Update the declaration deliberately, or move the rule back."
        )


def test_the_final_verdict_sees_every_family() -> None:
    """Nothing may be structurally unable to reach the verdict that matters.

    The mirror of the gate test. An exclusion for a flag that can never arrive is
    dressing, in Jamie Dodd's phrase, and a family that can never arrive is worse:
    it inflates the apparent independence of the gate while contributing nothing.
    """
    from flac_detective.analysis.new_scoring.evidence import RULE_FAMILY

    path = SCORING / "new_scoring" / "calculator.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    reachable = {RULE_FAMILY[name] for _line, name in _rule_positions(tree, PIPELINE_FUNCTION)}

    declared = set(RULE_FAMILY.values())
    missing = declared - reachable
    assert not missing, (
        f"families {sorted(missing)} are declared in evidence.py but no rule "
        f"producing them is reachable from {PIPELINE_FUNCTION}. They can never "
        "corroborate anything, so counting them as independent witnesses overstates "
        "how many sources a conviction actually has."
    )
