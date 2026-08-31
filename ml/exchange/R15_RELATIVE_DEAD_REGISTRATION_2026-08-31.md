# Rule 15, the relative dead test — registered before the constant is chosen

Written and committed **before the sweep runs, before the constant is picked and
before `stereo_image.py` is touched**. The previous attempt
(`R15_BANDLIMIT_REGISTRATION_2026-08-31.md`) was refused by its own check; this
one records the procedure for choosing the constant so that the choice cannot be
made after seeing which value flatters the answer.

---

## One correction to the previous document, first

That document said the price of a repair "is not ours to set on a set we built"
and that Provir's set B was the right terrain. **That is too strong and it is
withdrawn.** The circularity worry applies to the *false-positive* side — a
threshold must not be tuned against our own band-limited construction. The
*recall* side is different: `audit_corpus`'s transcodes are labelled by
construction, every constant this engine ships was priced on them, and declining
to use them here would be a new standard invented for one inconvenient case.

So the price is measured now, on `audit_corpus`, and the fix does not wait.

## The defect, restated

Both channels are tested against the same absolute bar. The side channel already
sits 10-20 dB below the mid one above 10 kHz, so a roll-off only has to finish
the job: the side falls under the bar, the run length explodes, and the witness
reports "the side channel died" about a file that simply has no top octave.
Measured: **15 convictions on 44 authentic sources given a 14 kHz roll-off and
nothing else.**

## The repair: structure instead of level

Codec coupling **zeroes some bins and leaves others alone** — holes in a live
side channel. A roll-off lowers **every** bin together. A level test cannot tell
those apart; a test relative to the file's own side channel can.

    dead(bin) = side(bin) < REL_FLOOR * median(side over the band, this frame)

A coupled file has bins far below its own median: contrast, so runs. A
band-limited file has a side channel that is uniformly low, median included:
no contrast, so no runs. The mono gate, the frame minimum and the interior-run
exclusion are untouched.

## How REL_FLOOR is chosen — the procedure, fixed now

A sweep over `REL_FLOOR ∈ {0.02, 0.05, 0.10, 0.20, 0.30}`, evaluated on three
populations, **none of which is set A**:

* `audit_corpus/authentic`, 40 files — the null;
* `audit_corpus/fake/{mp3_320, aac_ff256, opus_256, vorbis_q8}`, 40 each — the
  signal, and the witness's documented domain (opus_256 fires 92 %);
* the 44 parked band-limited controls — the artefact.

**The rule for picking the value, written before the numbers exist:** take the
**largest** `REL_FLOOR` whose separation between arms and genuine, measured as
AUC, is within **0.03** of the current absolute test's AUC on the same files.
Largest, because a larger floor is the stronger claim about structure; the AUC
guard is what stops it being bought with recall. **If no candidate value clears
the AUC guard, the relative test is refused and this document says so.**

## Criteria

| # | criterion | bound |
|---|---|---|
| **S1** | convictions on the 44 band-limited controls | **≤ 2**, from **15** |
| **S2** | false convictions on set A's own 36 genuine | **0**, from **1** |
| **S3** | convictions lost on the four `audit_corpus` arms (160 files) | **≤ 6** — the price, and the criterion that can refuse the repair |
| **S4** | the witness's AUC (arms vs genuine) on `audit_corpus` | within **0.03** of the absolute test's, the same guard that chose the constant, re-checked after the fact on the verdicts rather than on the statistic |

**S3 is binding.** A repair that removes a false-positive mechanism by making the
witness deaf is not a repair, it is a deletion — and deleting Rule 15 would be an
honest option, but it would have to be argued as one rather than smuggled in as a
threshold change.

**S2 is a floor, not an achievement.** A set we built, at a threshold we chose,
must not convict its own genuine files.

Results appended below, dated after the fact. Nothing above may be edited once
the sweep has run.

---

# RESULTS — appended 2026-08-31. The refusal clause fired.

`ml/r15_sweep.py`, spectra computed once per file and every candidate floor read
off the same spectra. 40 genuine, 160 arm files, 34 band-limited controls that
survive the mono gate.

| variant | AUC arms/genuine | median genuine | median arms | median band-limited | band-limited over the 2.0 bar |
|---|---|---|---|---|---|
| **absolute (shipped)** | **0.905** | 0.00 | 7.36 | 3.50 | **27 of 34** |
| relative 0.02 | 0.805 | 0.00 | 1.30 | 0.00 | **0 of 34** |
| relative 0.05 | 0.760 | 1.00 | 1.52 | 1.00 | 0 of 34 |
| relative 0.10 | 0.703 | 1.12 | 1.72 | 1.00 | 0 of 34 |
| relative 0.20 | 0.658 | 1.34 | 1.86 | 1.20 | 1 of 34 |
| relative 0.30 | 0.614 | 1.53 | 1.88 | 1.50 | 2 of 34 |

The guard was AUC within **0.03** of 0.905. The best candidate reaches **0.805**,
ten points below. **No value clears it, so the relative test is refused**, as this
document said it would be.

## What the refusal teaches, and it is not nothing

The relative test does exactly what it was designed to do — **0 of 34
band-limited files above the bar, against 27 of 34** — and it costs a tenth of
the separation the witness exists for. So the absolute bar is not an oversight
that survived: **it is where the signal lives.** A coupled side channel is
distinguishable from an uncoupled one mostly by being *quiet*, not by being
*holey*, and a statistic that only sees structure sees a much weaker version of
the thing.

That also means the false positive is **intrinsic to the statistic as designed**,
not a bug in it. Rule 15 cannot be made band-limit-blind from the inside without
becoming a different and worse witness.

## Where the repair has to go instead

Two places, neither of them inside `side_dead_run`:

1. **A domain gate**, on the same principle as `MONO_GATE`: the witness abstains
   when the file has no top octave to have a stereo image in. That is a
   restriction of where the statistic applies, not a change to what it measures —
   which is the honest shape for an instrument whose signal really does live in
   the absolute level.
2. **An independence guard on the corroboration gate.** The conviction needed two
   families and got `spectral` and `stereo` — both reading the missing top
   octave. The gate counts families; it does not ask whether they are looking at
   the same thing.

The first is measurable immediately and gets its own registration. The second is
the deeper fix and touches every rule pair, so it needs the priced corpus and a
registration of its own.
