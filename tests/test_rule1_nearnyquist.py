"""Rule 1's near-Nyquist gate: the instrument must be reachable, and only where used.

Why this file exists
--------------------
``compute_residual_floor_db`` is the calibrated instrument (ROC AUC 0.95) that tells
a 320 kbps brickwall from an authentic band-limited rolloff where the cutoff alone
cannot. Rule 1 consults it — after four guards, one of which returns for every
cutoff at or above 0.94 * Nyquist.

Until 2026-08-20 ``analyze_spectrum`` computed that residual across
[0.90, 0.95) * Nyquist. Rule 1 could never consult the top 220 Hz of that window,
so it was computed and discarded on every file that landed there.

That is a mild version of the defect this project keeps finding in itself and that
Jamie Dodd found six of in Provir: an instrument that runs for a population it can
never be asked about. Rule 14 was unreachable for its own target population for the
same reason. A table of inputs cannot catch it, so these tests ask the reachability
question directly:

1. both branches of the residual gate are reachable — it is not dead code;
2. the discarded slice really is unusable by the rule, so narrowing was correct;
3. the computation window and the rule's guard agree, so the slice cannot silently
   come back.

Test 3 is the one that would fail if someone moved either constant without the
other, which is the only way this regresses.
"""

from __future__ import annotations

import re
from pathlib import Path

from flac_detective.analysis.new_scoring.rules.spectral import (
    NEARNYQ_FLOOR_DB,
    apply_rule_1_mp3_bitrate,
)

SAMPLE_RATE = 44100
NYQUIST = SAMPLE_RATE / 2.0

# A cutoff inside the 320 kbps signature band AND below the 0.94 * Nyquist guard,
# so the residual gate is actually consulted. 0.94 * 22050 = 20,727 Hz.
CUTOFF_REACHABLE = 20500.0

# A cutoff inside the slice that used to be computed and thrown away:
# [0.94, 0.95) * Nyquist = [20,727, 20,947.5).
CUTOFF_DISCARDED_SLICE = 20800.0

# Container bitrate inside Rule 1's expected range for a 320 kbps source (700-1050).
CONTAINER_KBPS = 900.0


def _rule1(cutoff: float, residual: float):
    """Rule 1 with everything but the near-Nyquist question held constant."""
    return apply_rule_1_mp3_bitrate(
        cutoff_freq=cutoff,
        container_bitrate=CONTAINER_KBPS,
        cutoff_std=0.0,
        sample_rate=SAMPLE_RATE,
        energy_ratio=0.0,
        residual_floor_db=residual,
    )


def test_a_hard_floor_still_convicts_where_the_gate_is_reachable():
    """A digital-silence floor below the bar is a transcode: the +50 must survive."""
    (score, reasons), estimated = _rule1(CUTOFF_REACHABLE, NEARNYQ_FLOOR_DB - 15.0)
    assert score == 50, f"expected the 320 signature to hold, got {score} ({reasons})"
    assert estimated == 320


def test_a_high_floor_drops_the_signature_where_the_gate_is_reachable():
    """An analog/dither floor above the bar is authentic: the +50 must be withheld.

    This is the half that proves the instrument is not dead code. If this passed
    only because some earlier guard returned, the test above would fail too.
    """
    (score, reasons), estimated = _rule1(CUTOFF_REACHABLE, NEARNYQ_FLOOR_DB + 15.0)
    assert score == 0, f"expected the signature to be dropped, got {score}"
    assert estimated is None
    assert any("residual floor" in r for r in reasons), (
        "the rule must say WHY it declined; a silent zero is indistinguishable from "
        f"a guard that returned earlier. reasons={reasons}"
    )


def test_the_discarded_slice_cannot_use_the_residual_at_all():
    """In [0.94, 0.95) * Nyquist the rule returns before the residual is consulted.

    Both extremes of the residual must give the same answer there. If they ever
    differ, the slice became usable and ``analyze_spectrum`` must start computing it
    again — the two changes belong together.
    """
    hard = _rule1(CUTOFF_DISCARDED_SLICE, NEARNYQ_FLOOR_DB - 15.0)
    soft = _rule1(CUTOFF_DISCARDED_SLICE, NEARNYQ_FLOOR_DB + 15.0)
    assert hard[0][0] == soft[0][0] == 0, (
        "a cutoff in the discarded slice must score 0 whatever the residual says; "
        f"got hard={hard[0][0]} soft={soft[0][0]}"
    )
    assert hard[1] is soft[1] is None


def test_the_computation_window_matches_its_consumers():
    """The window's TOP is the near-Nyquist rule's guard; its FLOOR is C-prime's.

    Rewritten for v1.13, as this test's own failure message demanded. The top
    invariant is unchanged: computing above Rule 1's 0.94 guard wastes a Welch
    pass on a slice the rule cannot consult. The floor gained a consumer in
    v1.12: gate C-prime accepts an uninformative (PCM-level) container only
    when the wall proves its depth, so the floor must sit at or below the
    lowest MP3 signature cell C-prime can score — 18,750 Hz, i.e. 0.85 x
    Nyquist at 44.1 kHz. A floor quietly raised above that silently starves
    C-prime on uncompressed input, which is exactly how the v1.12 campaign
    missed its G2 bar (15/34 instead of >= 20).
    """
    source = Path("src/flac_detective/analysis/spectrum.py").read_text(encoding="utf-8")
    match = re.search(
        r"if\s+([0-9.]+)\s*\*\s*nyquist\s*<=\s*final_cutoff\s*<\s*([0-9.]+)\s*\*\s*nyquist",
        source,
    )
    assert match, (
        "could not find the residual-floor computation window in spectrum.py; if it "
        "was restructured, this test must be rewritten rather than deleted — the "
        "invariants it pins are that the window's top and Rule 1's guard agree, and "
        "that its floor covers gate C-prime's MP3 cells."
    )
    window_floor = float(match.group(1))
    window_top = float(match.group(2))

    rule_source = Path("src/flac_detective/analysis/new_scoring/rules/spectral.py").read_text(
        encoding="utf-8"
    )
    guard = re.search(r"nyquist_limit_percent\s*=\s*([0-9.]+)\s*\*\s*nyquist_freq", rule_source)
    assert guard, "could not find Rule 1's 320 kbps Nyquist guard in spectral.py"
    guard_fraction = float(guard.group(1))

    assert window_top == guard_fraction, (
        f"the residual is computed up to {window_top} * Nyquist but Rule 1 stops "
        f"consulting it at {guard_fraction} * Nyquist. Either the window wastes a "
        "Welch pass on a slice the rule cannot use, or the rule needs a residual "
        "that is no longer computed. They must move together."
    )
    # 18,750 Hz is the lowest MP3 signature cell C-prime scores on uncompressed
    # input; 0.85 * 22,050 = 18,742.5 sits just under it.
    assert window_floor <= 18750.0 / 22050.0, (
        f"the residual computation floor ({window_floor} * Nyquist) sits above the "
        "18,750 Hz MP3 cell — gate C-prime is starved of its depth reading on "
        "uncompressed input, the exact mechanism of v1.12's missed G2."
    )
