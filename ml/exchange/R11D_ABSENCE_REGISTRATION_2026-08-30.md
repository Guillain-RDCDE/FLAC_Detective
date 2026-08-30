# R11D and the fourth instance of the species — registered 2026-08-30, before measurement

Written and committed **before the repair is made and before the before/after
passes are run**, per the convention that has governed every change in this
engine since April: the criteria are fixed while the answer is still unknown.

Prompted by Jamie Dodd's letter of 2026-08-29. His `edge_std` coercion was
one-directional and could only lose recall. **Ours is not**, and it is live.

---

## The defect, stated as mechanism rather than as suspicion

`analysis/spectrum.py` computes the cutoff wander across the sampled windows:

```python
cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0
```

`num_samples = 3 if total_duration > 90 else 1`. So for any file of 90 seconds
or less there is exactly one window, the standard deviation **cannot be
computed**, and the not-computable case is returned as the value `0.0` — an
absence wearing the clothes of a measurement, the same species as
`detect_cutoff` returning Nyquist and as Provir's `width` sentinel of 1500.0.
Fourth instance across the two engines, and the first one that is ours and
load-bearing.

It is consumed in `rules/cassette.py`, TEST 11D:

```python
if 50 < cutoff_std < 300:   cassette_score += 15   # "wow/flutter"
elif cutoff_std < 30:       cassette_score -= 10   # "very stable, suspect digital"
elif cutoff_std < 50:       pass                   # "neutral zone"
```

and `cassette_score >= CASSETTE_THRESHOLD` (15) awards **−40 points and
disables Rule 1** (`calculator.py:211`).

**The consequence, derived from the weights rather than guessed.** The other
tests can contribute 11A +30 (tape hiss) and 11B +20 / −20 (progressive
roll-off), so the cassette score excluding 11D takes values
S ∈ {−20, 0, 10, 20, 30, 50}. With the phantom −10 applied:

| S (11A + 11B) | shipped: S − 10 | ≥ 15 ? | without the phantom | ≥ 15 ? |
|---|---|---|---|---|
| 20 (11B alone) | 10 | **no** | 20 | **yes** |
| 30 (11A alone) | 20 | yes | 30 | yes |
| 50 (both) | 40 | yes | 50 | yes |
| 10, 0, −20 | ≤ 0 | no | ≤ 10 | no |

So the absence flips exactly one population: **files whose only cassette
evidence is a progressive roll-off (11B alone, S = 20) are denied the −40
protection and keep Rule 1** — on a variance that was never measured. Unlike
Provir's, this coercion pushes **toward** conviction, and it fires on every
file of 90 seconds or less, which is every file in both of our measurement
corpora (`cutoff_std_hz` reads 0.0 on 590 of 590 rows of
`fd-exchange-v2_columns_flacdetective.csv` — one distinct value).

## Two further defects in the same test, from the same cause

Both follow from the reporting grid rather than from the absence.
`detect_cutoff` returns slice boundaries, so every cutoff is quantised to a
**250 Hz cell**, and with `num_samples = 3` the reachable values of the
standard deviation below 300 Hz are exactly:

    0.0   (three windows in one cell)
    117.9 (one window one cell away)
    204.1 (three different cells)
    235.7 (one window two cells away)

1. **`elif cutoff_std < 50` is unreachable.** Nothing can land in [30, 50).
   Dead code that has read as a calibrated neutral zone since v1.8.
2. **The wow/flutter band fires on one grid cell.** 117.9 Hz sits inside
   `50 < std < 300` and earns +15 as "natural cutoff variation (wow/flutter)",
   when it is the smallest possible non-zero value of a quantised statistic.
   The engine already knows this: Rule 1's gate A is set at
   `CUTOFF_VARIANCE_THRESHOLD = 130.0`, chosen as "the smallest round figure
   above the one-cell wander" (`ml/r1_gates_repricing.py`). Two rules read the
   same statistic with incompatible ideas of what its quantum means.

## The repair, fixed before the cost is known

1. `cutoff_std` becomes `float("nan")` when it cannot be computed. NaN, not
   None, to match `residual_floor_db` and `EdgeReading.width_hz`, to keep the
   type, and because a NaN poisons a median loudly where a 0.0 poisons it
   silently. The dataclass and keyword defaults follow.
2. **An absence contributes nothing to Rule 11.** Not +15, not −10.
3. The unreachable `< 50` branch is removed.
4. The wow/flutter band's lower bound moves 50 → `CUTOFF_VARIANCE_THRESHOLD`
   (130), so one cell of grid wander is no longer read as tape flutter, and the
   two consumers of `cutoff_std` share one definition of its quantum.
5. Rule 1's own `cutoff_std == 0.0` safety skip becomes "not known to vary"
   (`0.0` **or** NaN), so the conservative behaviour is preserved rather than
   silently lost when the value stops being 0.0.
6. `CASSETTE_THRESHOLD` is **not** touched. Compensating a repair with a
   threshold move would preserve the numbers and keep the defect.

## Criteria, registered before the passes run

Two corpora, one before pass on the shipped code and one after, same files,
same order (`ml/r11d_absence_pass.py`):

* **fd-exchange-v2**, 590 files, the adjudicated key of 2026-08-23;
* **audit_corpus**, 80 genuine and 80 `mp3_320`, labelled by construction.

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`) on either corpus | **0** — a safety criterion, no tolerance |
| **A2** | genuine files newly signaled (`WARNING`+) | **0** |
| **A3** | transcodes that stop being convicted | ≤ 5 of the 296 currently convicted on fd-exchange-v2 |
| **A4** | files that move at all | must be a subset of `cutoff < 19,000 Hz` **and** 11B-alone, as derived above — any mover outside it means the mechanism above is wrong |
| **E1** | genuine files that gain the cassette protection | reported, not bounded — this is what the repair is for |

A1 or A2 breached means the repair ships behind a re-priced
`CASSETTE_THRESHOLD` instead, and that re-pricing gets its own registration.
A4 breached means this document is wrong and the repair is withdrawn until it
is understood.

Results are appended below, after the run, in a section dated after the fact.

---

# RESULTS — appended 2026-08-30, after the passes, criteria unedited above

## The scope, measured and exactly as derived

`ml/r11d_scope_pass.py`, 750 files (590 fd-exchange-v2 + 80 genuine + 80
mp3_320): **74 files cross the cassette gate** when the phantom -10 is removed —
70 on the exchange set, 2 genuine, 2 mp3_320. Every one of the 74 has the
predicted profile, with **no exceptions at all**:

    cassette score  10 -> 20   74 of 74
    cutoff < 19,000 Hz         74 of 74
    reasons                    {R11B, R11D} — roll-off only, plus the phantom
    cutoff_std                 0.0 on all 74 (single window, absence)

Criterion **A4 held**: nothing outside `cutoff < 19,000` moved, and nothing
outside the 11B-alone population moved either. The derivation from the weights
predicted the population before it was measured.

## The repair as registered was REFUSED by its own criteria

Full engine, before on v1.13.0 in a pristine worktree, after on the repair, same
132 files (the 74 movers plus 58 controls drawn from the non-movers of all three
strata):

| criterion | bound | measured | |
|---|---|---|---|
| A1 genuine newly convicted | 0 | **0** | held |
| A2 genuine newly signaled | 0 | **0** | held |
| A3 transcodes losing conviction | ≤ 5 | **44** | **FAILED** |
| A4 movers outside the derived population | 0 | **0** | held |

52 of 132 verdicts moved: 23 `FAKE_CERTAIN -> WARNING`, 21
`FAKE_CERTAIN -> AUTHENTIC`, 6 `WARNING -> AUTHENTIC`, 2 `SUSPICIOUS ->
AUTHENTIC`. Not one genuine file was harmed — the damage was entirely recall.

**What that measured, and it is the finding of the day:** the phantom had been
absorbed into the calibration. `CASSETTE_THRESHOLD` was set to 15 in v1.8 in a
world where every file of 90 s or less carried a silent -10, so the gate's
*effective* height for that population was 25. Remove the phantom alone and
roll-off-only files (11B = 20) start clearing a gate of 15, collecting -40 and
disabling Rule 1. A defect that has been shipping long enough stops being a
defect and becomes a constant, and the constant belongs in the gate.

## What shipped instead, and its cost

The escape clause registered above, applied — with the precedent from this very
file: v1.8 removed test 11C's flat +15 and dropped the threshold by the same 15,
"so that every other test keeps exactly the weight it had".

1. `cutoff_wander()` returns **NaN** when fewer than two windows were sampled.
2. An absent wander contributes **nothing** to Rule 11.
3. The "very stable, suspect digital" **-10 is removed**: on a 250 Hz grid it
   means "the windows landed in one cell", the ordinary case for genuine and
   transcode alike, and it separated nothing.
4. `CASSETTE_THRESHOLD` rises **15 -> 25**, the same 10 points, in the gate
   where a constant belongs.
5. The wow/flutter band's lower bound moves 50 -> `CUTOFF_VARIANCE_THRESHOLD`
   (130), now a single shared constant, so one 250 Hz cell of grid wander stops
   reading as tape flutter and Rule 1's gate A and Rule 11's TEST 11D finally
   agree about the instrument's quantum.
6. The unreachable `elif cutoff_std < 50` branch is gone.
7. Rule 1's 20 kHz ambiguity skip becomes "not known to vary" — `0.0` **or**
   NaN — so the conservative exit is kept rather than silently lost.

**Cost, on the same 132 files, before against after:**

    verdicts changed   0
    scores changed     0
    A1 / A2 / A3 / A4  0 / 0 / 0 / 0 — all held

The compensation is exact on every file of both corpora, because every file is
60 s and therefore every wander is a NaN. The behaviour that changes is
elsewhere and is the point of the repair: files longer than 90 s whose measured
wander falls in (50, 130] Hz — one grid cell — no longer earn +15 as flutter,
and a single test no longer protects a file on its own. `tests/test_rule11.py`
pins the gate decision against the v1.13.0 table, input class by input class.

## One more instance, found by the audit rather than by a letter

Extending `ml/typed_absence_audit.py` with shape C (`m = expr if len(xs) > 1
else <number>`) also caught `analysis/hires.py:110`, where a one-bin spectrum
fabricated a 1.0 Hz bin width to size a smoothing kernel. Harmless in practice
and repaired the same way: the degenerate case returns "unanalysable" instead of
a number. Audit now reads **150 modules, 0 findings**, with the tripwire
verified against its control first (6 of 6 caught, 0 false positives).
