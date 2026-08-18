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
