# Admission audit — is every calibrated statistic computed on the population its rule can read?

## The species, and why this audit exists

Three instances in one week, across two engines, of the same defect:

1. **Our Rule 1 residual** (v1.11.3): calibrated on a 220 Hz window the rule could
   never consult — computed, then thrown away, on every file.
2. **Provir's width range** (2026-08-20): 390–519 Hz quoted against a 160 Hz
   admission gate, measured by an ungated sweep; both interval endpoints came
   from files the gate refuses (4 admissible of 11, actual range 398–474).
3. **Provir's Opus flatness probe** (same day, his report): same species.

The species: **a statistic computed across a population the rule cannot read.**
A calibration quantile is a false-alarm budget, and a budget priced on files the
rule will never see is priced on the wrong risk pool. This audit walks every
calibrated constant in the scoring engine and checks the calibration population
against the rule's own admission conditions, with the evidence file:line.

## Method

For each calibrated constant: (a) list the rule's runtime admission gates from
its code; (b) identify the calibration population and instrument from the
constant's provenance comment and the `ml/` harness that produced it; (c) verify
whether each gate was applied to the calibration population; (d) where it was
not, **count** the out-of-gate files from the committed per-file CSVs and bound
the effect on the quantile. Counts below use the 258-genuine corpus
(80 audit-certified in `ml/rule_audit_baseline.csv` + 178 wild in
`ml/wild_scan.csv`) and the 877-file recertification (`ml/recert_880.csv`).

## Verdicts

| statistic | runtime gates | calibration population | verdict |
|---|---|---|---|
| Rule 1 `compute_residual_floor_db` window | consulted only in `[0.90, 0.94) × Nyquist` | window now stops where the rule stops | **ALIGNED (fixed v1.11.3)** — `tests/test_rule1_nearnyquist.py` pins the two constants together |
| Rule 12 Platt calibration (`a=1.509 b=-0.541`, 690 probs) | reliability gate abstains below 7 kHz rolloff (`_ROLLOFF_GATE_HZ`, `ml_classifier.py:66`) | `ml/emit_probs.py` **skips abstained files by default** (line 73, `--include-abstained` opt-in) | **ALIGNED** — the calibration saw exactly the population the gate admits |
| Rule 13 `CERTIFIED_GENUINE_P999 = 1.614` (877 files) | `should_run_rule_13`: cutoff ≥ **18,000 Hz** and score < FAKE_CERTAIN (`mdct_alignment.py:150-163`) | recert measured ALL 877 certified files, no cutoff filter; `recert_880.csv` records no per-file cutoff | **MISALIGNED, bounded** — see below |
| Rule 14 `SEAM_BAR = 0.60` (258 genuine) | cutoff ≥ **15,000 Hz** (`temporal_seam.py:67,90`) | `ml/hf_seam_probe.py` measures below its own local cutoff but applies no 15 kHz admission floor | **MISALIGNED, negligible** — 2/258 out-of-gate (both at 14,000 Hz — grid cells), ≤ 1 rank of the p95, ±0.4 % on the testify rate |
| Rule 15 `RUN_BAR = 2.0` (228 measured genuine) | mono gate (`MONO_GATE`, NaN) **and** cutoff ≥ 12,000 Hz (`stereo_seam.py:87`) | `ml/side_dead_run_probe.py` applies the mono gate; no 12 kHz floor | **ALIGNED in effect** — 0/258 genuine files sit below 12 kHz, so the unapplied gate excludes nobody |

## Rule 13, the one real finding

**17 of 258 genuine files (6.6 %) carry a cutoff below the rule's 18 kHz
admission floor** (3/80 audit-certified: 16,250 / 17,750 / 17,750; 14/178 wild,
from 14,000 to 17,750). If the 877-file library recert has a similar band-limited
fraction, roughly **58 of the 877 calibration files are ones Rule 13 will never
be asked about.**

Bounded effect, from the recorded tail (`median 1.269 · p99 1.449 · p99.9 1.614 ·
max 2.418`):

- The measured review exceedance moves from 1/877 = 0.11 % to at most
  1/819 = 0.12 % (Wilson-95: 0.64 % → 0.68 %) — the shipped safety arithmetic
  (a lone review at 25 points cannot flag a file, `SCORE_REVIEW < SCORE_WARNING`)
  is untouched.
- The p99.9 of the admitted population lives, under every removal scenario, in
  the same interpolation interval between the second-highest value (~1.61) and
  the max (2.418). Worst case (all 58 removed from below the tail) shifts the
  interpolation weight and reads the admitted-population p99.9 at ~1.67 — the
  review bar stays above it, but the published "24 % clear of p99.9" margin is
  optimistic by up to ~4 points in that worst case.

**No constant changes today**: every scenario leaves the bars above the admitted
population's p99.9 and the two-family conviction arithmetic intact. What changes
is the obligation on the next recertification:

1. filter the population through `should_run_rule_13` (or record per-file cutoff
   in the CSV so both quantiles can be computed);
2. state both numbers — all-certified and admitted-only — and calibrate on the
   admitted one.

**MEASURED the same day** (`ml/recert_admission_pass.py`, joined on the recert's
own key — sha1(normpath)[:16], recovered by matching all 877 paths exactly;
per-file rows in `ml/recert_admission.csv`, hashes only): **22/877 certified
files (2.5 %) sit under the 18 kHz floor** — less than the 6.6 % the 258-corpus
extrapolation suggested, the CD library being less band-limited than the wild
corpus. Admitted-only tail: median 1.269 · p99 1.447 · **p99.9 1.634** ·
max 2.418, against the published all-certified 1.614 — inside the worst-case
bound (~1.67) argued above. Exceedance: review bar 1/855 = 0.12 % (vs 1/877 =
0.11 %), hard bar 0 on both populations. The verdict stands with a number under
it: misaligned, bounded, no constant moves, both quantiles now shipped in
`mdct.py` (`CERTIFIED_GENUINE_ADMITTED_P999`).

## Standing rule, adopted

**A calibration is computed under the admission conditions of the rule that
consumes it, or it states explicitly that it is not and why the superset is
safe.** Every future `ml/` calibration harness quotes the rule's gates in its
docstring and applies them, the way `ml/emit_probs.py` already does for the
Rule 12 gate.
