#!/usr/bin/env python3
"""The v1.12 campaign: re-price Rule 1's three admission gates, wild53 held out.

What is being changed, precisely (registered before any measurement)
--------------------------------------------------------------------
The M-series proved the wild anatomy has one load-bearing layer: the stereo
witness reads the owner-attested wilds at AUC 0.97 and has nothing to
corroborate, because three Rule 1 admission gates — each calibrated on
direct-lab material — suppress the points. The three repairs:

  GATE A (variance). Old: exit when cutoff_std > 100 Hz. The instrument
  quantizes to 250 Hz cells, so a rock-stable wall near a cell boundary reads
  std up to 125 (50/50 between adjacent cells) and exits. New: exit when
  cutoff_std > 130 Hz — the smallest round figure above the one-cell wander
  bound. PRINCIPLE, not a fit: the bound (125) is arithmetic on the grid, and
  130 is not tuned against any corpus.

  GATE B (the 20,000-exact exception). Old: a cutoff of exactly 20,000 Hz is
  discarded as possible FFT rounding whenever energy_ratio > 1e-6 — which any
  wild press-noise floor satisfies. New: at 20,000 Hz, consult the DEPTH
  instead: if residual_floor_db <= NEARNYQ_FLOOR_DB (-55 dB) the wall is real
  and scoring proceeds; NaN or shallow keeps the old skip. (20,000/22,050 =
  0.907 sits inside the residual window, so the reading exists at 44.1 kHz;
  at 48 kHz the residual is NaN and the legacy skip is preserved.)

  GATE C (container bitrate by format). Old: mp3_ranges checks the container
  bitrate against windows calibrated for FLAC (320 -> 700-1050 kbps); a WAV
  reads ~1411 kbps and every WAV is structurally out of Rule 1's reach. New:
  when the container bitrate is at PCM level (>= 90 % of sample_rate x 32/1000,
  i.e. an uncompressed container), the container carries no compression
  information and the check is BYPASSED (treated as in-range), never failed.
  FLAC windows are unchanged in this campaign.

Acceptance — the G-series, registered before the inputs pass runs
------------------------------------------------------------------
    G1  SAFETY, the binding one: on the 258 genuine (80 audit-certified + 178
        wild), at most 2 files newly receive R1's +50 under the new gates —
        and a full-engine re-run on every such file yields ZERO new genuine
        conviction and at most +1 newly signaled.
    G2  EFFICACY: on the wild53 owner tier (34), the new gates award +50 to at
        least 20 files.
    G3  NO REGRESSION: on the 720 lab arms, the count of files receiving +50
        does not decrease.
    G4  END TO END: full engine with the new gates on the wild53 — owner tier
        signaled >= 50 % (from 8.8 %), eye tier reported separately, and any
        FAKE_CERTAIN triggers the W1-style audit before anything is celebrated.

If G1 fails the campaign stops and reports; no threshold is re-tuned against
the population that scored it. The wild53 is the held-out bench: no constant in
the three repairs above was derived from it (130 is grid arithmetic, -55 dB is
the shipped NEARNYQ_FLOOR_DB, the PCM test is format arithmetic).

Stage 1 (this file): measure Rule 1's inputs on every file — 258 genuine, 720
arms, 53 wild — then evaluate OLD (the shipped apply_rule_1, called directly)
vs NEW (the same sequence with gates A/B/C repaired) offline on those inputs.
Stage 2 (branch): apply the patch in src, full-engine the wild53 and every
genuine file whose R1 outcome changed, score G1-G4.

Results are appended below after each stage; the registrations stay.
--------------------------------------------------------------------------------
AMENDMENT — GATE D, found by G4 itself (2026-08-21, stage 2)
-------------------------------------------------------------
The first end-to-end run of the patched engine on the wild53 read EXACTLY the
v1.11.4 numbers — because this campaign's offline evaluation calls the RULE
FUNCTION, and the PIPELINE never calls it for WAV input: calculator.py disables
Rule 1 entirely for uncompressed containers ("no lossless-compression signal"),
which is the same rationale gate C just made obsolete inside the rule. That is
what an end-to-end criterion is FOR, and G4 caught it on its first firing.

  GATE D (the dispatch). Old: is_uncompressed -> Rule 1 removed from the rule
  list. New: Rule 1 runs on uncompressed input; gate C handles the
  uninformative container inside the rule, and every other guard (variance,
  residual, Nyquist) is container-agnostic.

  G1-ter  Registered before it runs: the genuine corpora (80 audit + 40 wild),
          CONVERTED to WAV, through the new rule — at most 2 files newly
          receive +50 relative to their FLAC selves. Same bound and same
          stop-rule as G1.

STAGE 1 MEASURED 2026-08-21, n = 1,031 — G2 and G3 HELD, G1 FAILED AS WRITTEN,
and the failure found something bigger than the campaign:

    population        n   old +50   new +50
    genuine_audit    80        3         3
    genuine_wild    178        2         6    <- G1: 4 newly +50, bound was 2
    arms (720)      720      142       160    <- G3 HELD (+15 on mp3_320 alone:
                                                 gate B repairs the LAB too)
    wild_owner       34        0        26    <- G2 HELD
    wild_eye         19        0        19    (reported separately, circular tier)

    G1 stage-1 FAILED: 4 genuine_wild files newly receive +50 — and all four
    are Calexico etree recordings. THE CAMPAIGN STOPS HERE AS REGISTERED. No
    threshold is re-tuned. src is untouched.

WHAT THE FAILURE FOUND. Before calling the four false positives, their archive
items' own metadata was consulted — provenance documented by the tapers
themselves, years before any of this: `ECM-DS70P > MZ-N10` and
`CSB > MZ-N10` / `MZ-R55`. **MZ-N10 and MZ-R55 are Sony MiniDisc recorders:
the chain is ATRAC, a lossy perceptual codec.** A full lineage audit of the
wild_authentic corpus followed (all 74 items; scratch scripts, results
recorded here): **11 Calexico items — 30 of the corpus's 180 files (16.7 %) —
carry a taper-documented MiniDisc chain.** One further item
(glenhansard2016-04-02, "Muvid IR815 digital Ausgang") is ambiguous and
listed for examination without a verdict.

So G1's four are not false positives of the repaired gates: they are the
repaired gates DETECTING documented ATRAC-sourced material inside our own
"genuine" labels — the corpus defect class Provir's whole exchange is about,
found by the very campaign the labels were scoring. Every calibration that
used "258 genuine" (RUN_BAR, SEAM_BAR, the v1.9 corroboration threshold, the
eligibility figures) included these files.

STATUS: CAMPAIGN SUSPENDED PENDING HUMAN ADJUDICATION — not failed, not
resumed. The 30 files are registered in ml/wild_fake_ledger.py with their
documented sources (label undecided: the ledger's design point is that the
engine's own detection never becomes the label, and the adjudication belongs
to a human with the archive.org pages open). If the human rules them lossy on
the documentary basis (uploader_admission — the taper states the chain), the
genuine labels correct, G1 re-scores against corrected labels, and stage 2
(branch, src patch, wild53 full-engine, G4) proceeds. If the human rules them
genuine despite the documentation, G1's failure stands and the campaign ends.

STAGE 2 FINAL — 2026-08-21 (night), after adjudication, on the branch
----------------------------------------------------------------------
The 30 MiniDisc files were adjudicated fake by Guillain on the documentary
basis (uploader_admission, group scope, taper-written chains). G1 re-scored
against corrected labels: HELD at 0. Then the end-to-end run exposed GATE D
(above), and gate C's first form FAILED its own G1-ter (4 genuine-as-WAV newly
+50, bound 2) — the sub-320 cells had lost their only guard. One registered
revision, gate C-PRIME: an uninformative container is accepted only when the
wall proves its depth (residual <= NEARNYQ_FLOOR_DB), gate B's logic extended.

Final scores, all measured:

    SAFETY   G1      HELD  0 genuine newly +50 (labels corrected)
             G1-bis  HELD  0 of 797 library files (the 24-bit control)
             G1-ter  HELD  0 genuine-as-WAV newly +50 under C-prime
             W1      HELD  0 FAKE_CERTAIN across the wild 53, end to end
    EFFICACY G2      MISSED  15/34 offline vs the registered >= 20 — the cost
                     of C-prime: cells below the residual window's 0.90 x Ny
                     floor have no depth reading on uncompressed input.
                     Widening the residual computation window is v1.13,
                     registered separately, not patched tonight.
             G4      HELD  owner tier 17/34 = 50.0 % signaled end to end
                     (from 8.8 %), all WARNING, none convicted
    NO-REG   G3      HELD  lab arms 142 -> 160 (+15 on mp3_320: gate B
                     repairs the lab bench too)
    (W2's direction reversed under the new gates — the eye tier answers
    loudest at 94.7 %, which is expected when a band-edge rule regains its
    voice on the tier the eye selected, and is reported separately as the
    circular tier it is.)

SHIP DECISION: gates A, B, C-prime and D ship as v1.12.0. The safety criteria
held everywhere; the one missed efficacy prediction is reported with its
mechanism named. The engine's wild owner-tier recall moves 8.8 % -> 50.0 %
with zero convictions and zero new genuine cost on three safety populations.

Usage::

    python ml/r1_gates_repricing.py --measure   # inputs pass (resumable)
    python ml/r1_gates_repricing.py --evaluate  # offline old-vs-new + G numbers
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import analyze_spectrum  # noqa: E402
from flac_detective.analysis.new_scoring.rules.spectral import (  # noqa: E402
    NEARNYQ_FLOOR_DB,
    apply_rule_1_mp3_bitrate,
    estimate_mp3_bitrate,
)

NEW_VARIANCE_THRESHOLD = 130.0
PCM_CONTAINER_FACTOR = 0.90

POPULATIONS: Dict[str, List[str]] = {
    "genuine_audit": [r"C:\Users\loutr\audit_corpus\authentic\*.flac"],
    "genuine_wild": [r"C:\Users\loutr\wild_authentic\*.flac"],
    "arm_mp3_192": [r"C:\Users\loutr\audit_corpus\fake\mp3_192\*.flac"],
    "arm_mp3_320": [r"C:\Users\loutr\audit_corpus\fake\mp3_320\*.flac"],
    "arm_mp3_V0": [r"C:\Users\loutr\audit_corpus\fake\mp3_V0\*.flac"],
    "arm_aac_ff128": [r"C:\Users\loutr\audit_corpus\fake\aac_ff128\*.flac"],
    "arm_aac_ff256": [r"C:\Users\loutr\audit_corpus\fake\aac_ff256\*.flac"],
    "arm_aac_ff320": [r"C:\Users\loutr\audit_corpus\fake\aac_ff320\*.flac"],
    "arm_aacmf_256": [r"C:\Users\loutr\audit_corpus\fake\aacmf_256\*.flac"],
    "arm_opus_256": [r"C:\Users\loutr\audit_corpus\fake\opus_256\*.flac"],
    "arm_vorbis_q8": [r"C:\Users\loutr\audit_corpus\fake\vorbis_q8\*.flac"],
    "wild_owner": [
        r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)\CD1 Darren Styles\*.wav",
        r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)\CD2 Dougal\*.wav",
    ],
    "wild_eye": [
        r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)"
        r"\CD3 Bonus (Mixed by Styles and Dougal)\*.wav",
    ],
}


def container_kbps(path: Path) -> Optional[float]:
    try:
        info = sf.info(str(path))
        seconds = info.frames / info.samplerate
        return path.stat().st_size * 8.0 / seconds / 1000.0
    except Exception:
        return None


def measure(out_csv: Path) -> None:
    done = set()
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done.add((row["population"], row["track"]))
        print(f"reprise: {len(done)} deja mesures", flush=True)
    fieldnames = [
        "population",
        "track",
        "sample_rate",
        "cutoff",
        "energy_ratio",
        "cutoff_std",
        "residual_floor_db",
        "container_kbps",
    ]
    with open(out_csv, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for population, patterns in POPULATIONS.items():
            n = 0
            for pattern in patterns:
                for raw in sorted(glob(pattern)):
                    path = Path(raw)
                    if (population, path.name) in done:
                        n += 1
                        continue
                    kbps = container_kbps(path)
                    if kbps is None:
                        continue
                    try:
                        cutoff, energy, std, resid = analyze_spectrum(path)
                        rate = int(sf.info(str(path)).samplerate)
                    except Exception:
                        continue
                    writer.writerow(
                        {
                            "population": population,
                            "track": path.name,
                            "sample_rate": rate,
                            "cutoff": f"{cutoff:.1f}",
                            "energy_ratio": f"{energy:.3e}",
                            "cutoff_std": f"{std:.1f}",
                            "residual_floor_db": f"{resid:.1f}" if np.isfinite(resid) else "nan",
                            "container_kbps": f"{kbps:.0f}",
                        }
                    )
                    fh.flush()
                    n += 1
            print(f"{population}: {n} mesures", flush=True)


def old_r1_plus50(row: dict) -> bool:
    """The shipped rule, called directly on the measured inputs."""
    resid = float(row["residual_floor_db"]) if row["residual_floor_db"] != "nan" else float("nan")
    (score, _reasons), _est = apply_rule_1_mp3_bitrate(
        cutoff_freq=float(row["cutoff"]),
        container_bitrate=float(row["container_kbps"]),
        cutoff_std=float(row["cutoff_std"]),
        sample_rate=int(row["sample_rate"]),
        energy_ratio=float(row["energy_ratio"]),
        residual_floor_db=resid,
    )
    return score >= 50


def new_r1_plus50(row: dict) -> bool:  # noqa: C901
    """The repaired gate sequence — mirrors apply_rule_1 with gates A/B/C fixed."""
    cutoff = float(row["cutoff"])
    rate = int(row["sample_rate"])
    std = float(row["cutoff_std"])
    energy = float(row["energy_ratio"])
    kbps = float(row["container_kbps"])
    resid = float(row["residual_floor_db"]) if row["residual_floor_db"] != "nan" else float("nan")
    nyquist = rate / 2.0

    if cutoff >= 0.95 * nyquist:
        return False
    if cutoff == 20000.0:
        # GATE B repaired: depth decides, not raw HF energy.
        wall_is_real = (not math.isnan(resid)) and resid <= NEARNYQ_FLOOR_DB
        if not wall_is_real:
            if energy > 0.000001 or std == 0.0:
                return False
    if cutoff > 21500:
        return False
    if std > NEW_VARIANCE_THRESHOLD:  # GATE A repaired: above one-cell wander.
        return False
    est = estimate_mp3_bitrate(cutoff)
    if est == 0:
        return False
    mp3_ranges = {
        128: (400, 550),
        160: (450, 650),
        192: (500, 750),
        224: (550, 800),
        256: (600, 850),
        320: (700, 1050),
    }
    if est not in mp3_ranges:
        return False
    if est == 320 and cutoff >= 0.94 * nyquist:
        return False
    # GATE C-PRIME (the one registered revision): an uncompressed container
    # carries no information, and the bypass demands the proof the container
    # can no longer give — a deep residual floor. Without a depth reading the
    # rule abstains on uncompressed input (G1-ter's lesson).
    pcm_level = PCM_CONTAINER_FACTOR * (rate * 32.0 / 1000.0)
    deep = (not math.isnan(resid)) and resid <= NEARNYQ_FLOOR_DB
    if kbps >= pcm_level:
        if not deep:
            return False
    else:
        lo, hi = mp3_ranges[est]
        if not (lo <= kbps <= hi):
            return False
    if est == 320 and (not math.isnan(resid)) and resid > NEARNYQ_FLOOR_DB:
        return False
    return True


def adjudicated_fakes() -> set:
    """Filenames adjudicated 'fake' in the wild ledger (human labels only)."""
    ledger = Path("ml/wild_fake_ledger.json")
    if not ledger.exists():
        return set()
    import json

    records = json.loads(ledger.read_text(encoding="utf-8"))
    return {r["filename"] for r in records.values() if r["adjudication"]["label"] == "fake"}


def evaluate(out_csv: Path) -> None:
    rows = list(csv.DictReader(open(out_csv, newline="", encoding="utf-8")))
    # Re-label rows whose file a HUMAN has since adjudicated fake (2026-08-21:
    # 30 MiniDisc/ATRAC files, documentary basis). They leave the genuine pool
    # and are scored as their own population — the G-series stays scored
    # against the ledger's labels, never against the engine's opinion.
    relabeled = adjudicated_fakes()
    moved = 0
    for r in rows:
        if r["population"].startswith("genuine") and r["track"] in relabeled:
            r["population"] = "relabeled_md"
            moved += 1
    if moved:
        POPULATIONS.setdefault("relabeled_md", [])
        print(f"{moved} rows re-labeled genuine -> relabeled_md (ledger adjudications)")
    print(f"{len(rows)} lignes d'entrees\n")
    print(f"{'population':16}{'n':>5}{'old +50':>9}{'new +50':>9}{'delta':>7}")
    genuine_newly: List[str] = []
    for population in POPULATIONS:
        subset = [r for r in rows if r["population"] == population]
        if not subset:
            continue
        old = sum(1 for r in subset if old_r1_plus50(r))
        new = sum(1 for r in subset if new_r1_plus50(r))
        print(f"{population:16}{len(subset):>5}{old:>9}{new:>9}{new - old:>+7}")
        if population.startswith("genuine"):
            genuine_newly += [
                r["track"] for r in subset if new_r1_plus50(r) and not old_r1_plus50(r)
            ]

    arms_old = sum(1 for r in rows if r["population"].startswith("arm_") and old_r1_plus50(r))
    arms_new = sum(1 for r in rows if r["population"].startswith("arm_") and new_r1_plus50(r))
    owner_new = sum(1 for r in rows if r["population"] == "wild_owner" and new_r1_plus50(r))

    print(
        f"\nG1 stage-1  genuine newly +50 (<=2): "
        f"{'HELD' if len(genuine_newly) <= 2 else 'FAILED'} "
        f"({len(genuine_newly)}: {genuine_newly[:6]})"
    )
    print(
        f"G2          wild owner new +50 (>=20/34): "
        f"{'HELD' if owner_new >= 20 else 'FAILED'} ({owner_new}/34)"
    )
    print(
        f"G3          arms +50 no decrease: "
        f"{'HELD' if arms_new >= arms_old else 'FAILED'} "
        f"({arms_old} -> {arms_new})"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("ml/r1_gates_inputs.csv"))
    args = parser.parse_args(argv)
    if args.measure:
        measure(args.out)
        return 0
    if args.evaluate:
        evaluate(args.out)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
