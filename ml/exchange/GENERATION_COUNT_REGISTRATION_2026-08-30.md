# Counting generations — registered 2026-08-30, before the measurement

Written and committed **before `ml/generation_probe.py` is run even once**. The
question is new, the answer is unknown here, and the bounds below are fixed
while it still is.

---

## The question

Every engine in this space answers one question: *is this a transcode?* Neither
answers *how many times?* If the idempotence fixed point is a fixed point in the
ordinary sense, then re-encoding converges — and the distance to it should fall
monotonically with each generation. That would make **generation counting** a
readable quantity rather than a rhetorical one.

The ingredients already exist here and are not new work:

* `ml/mp3_idem_probe.py` — the shipped libmp3lame CBR-320 round-trip, files
  never pipes, returning R (the idem ratio) and d1.
* `ml/idem_phase_probe.py` — Provir's grid lock, adopted 2026-08-22: the fixed
  point has **period 576 samples and zero tolerance**, so any number read at the
  file's native phase is meaningless unless the phase is searched. Every
  generation past the first lands wherever its decoder left it.

So the instrument is: build chains of 1, 2, 3, 4 generations from a genuine
master, and read R at the **best phase**, never at phase 0.

## What is being measured

For each of 24 genuine 60-second excerpts from `audit_corpus/authentic`, five
files: the master (generation 0) and four chains where generation *n* is the
decoded output of generation *n-1* re-encoded at the same setting. Two ladders,
because a result that only holds for one encoder is an encoder's habit and not a
property of transcoding:

    ladder L — libmp3lame CBR 320, the probe's own codec (self-pairing)
    ladder A — ffmpeg AAC 256, a different filterbank the probe does not share

120 measurements per ladder plus 24 masters. Read: R at best canonical phase
{0, 529, 47} and the phase that produced it.

## The predictions, registered before the first run

| # | prediction | bound |
|---|---|---|
| **G1** | **Monotonicity, per file.** On ladder L, R falls (or is flat) with each generation | at least **18 of 24** files monotone non-increasing across generations 1→4 |
| **G2** | **Separation, 1 vs 2.** A single-generation transcode reads higher than a double | median R(gen 1) − median R(gen 2) ≥ **0.15**, and AUC(gen 1 vs gen 2) ≥ **0.75** |
| **G3** | **The master stays out.** Genuine masters read above every generation | median R(gen 0) > median R(gen 1), with **0 of 24** masters below the gen-1 median |
| **G4** | **Cross-codec.** The ordering survives on ladder A, where the probe's filterbank does not match the chain's | AUC(gen 1 vs gen 2) ≥ **0.65** — deliberately weaker; the probe is MP3 and the chain is AAC |
| **G5** | **The phase moves.** Generations past the first do not sit at phase 0 | fewer than **50 %** of gen-2+ files read best at phase 0, against ~100 % at gen 1 (which is a decode of our own encode, phase 0 by construction) |

**G1 or G2 failing means generation counting does not work on this instrument**,
and that is a publishable null: the fixed point converges but not readably, and
the honest statement is that R measures *whether* a chain exists and not *how
long* it is.

**G3 failing is the serious one** — it would mean generations can read as more
lossless than the master, which would put the existing idem numbers in question,
not just this experiment.

**G5 is the control, not a finding.** If gen-2 files still read best at phase 0,
the ladder was built wrong (each generation must be decoded and re-encoded, not
re-encoded from the same source) and the whole run is void regardless of G1-G4.

Results are appended below in a section dated after the fact. Nothing above may
be edited once the first number exists.

---

# RESULTS — appended 2026-08-30, criteria unedited above

216 measurements, 24 sources, `ml/generation_probe.csv`.

| # | bound | measured | |
|---|---|---|---|
| G1 monotone per file, ladder L | ≥ 18/24 | **11/24** | failed |
| G2 gen 1 vs gen 2 | Δ ≥ 0.15 **and** AUC ≥ 0.75 | Δ **+0.391**, AUC **0.644** | failed on the AUC half |
| G3 the master stays out | 0 masters below the gen-1 median | median 3.067 vs 0.877, **0 below** | **held** |
| G4 cross-codec, ladder A | AUC ≥ 0.65 | **0.493** | failed |
| G5 the phase moves past gen 1 | < 50 % at phase 0 | **100 %** | failed — see below |

    median R by generation
      master              3.067
      L (libmp3lame 320)  gen1 0.877   gen2 0.486   gen3 0.311   gen4 0.227
      A (ffmpeg aac 256)  gen1 3.269   gen2 3.305   gen3 3.346   gen4 3.337

## G5 was mis-specified, and the ladder is sound

G5 said that if generations past the first still read best at phase 0, the
ladder was built wrong and the run was void. **The ladder is right and the
criterion was wrong.** A clean re-encode chain never leaves phase 0: each decode
is delay-trimmed back to the original start, so the grid does not drift. Phase
drift comes from *editing* — a wild transcode that was cropped or re-assembled —
which is exactly the population Provir's grid lock was about, and it is not this
ladder.

The internal check that settles it: if the ladder were not a chain (each
generation re-encoded from the same master instead of from its predecessor), R
would be **constant** across generations. It falls by a factor of four,
0.877 → 0.227, monotonically in the median. The ladder is a chain.

So G1-G4 stand as measured, and G5 is withdrawn as a criterion. It is recorded
here rather than deleted, because a registration that quietly loses the
prediction it failed is worth nothing.

## What the numbers say, stated as narrowly as they deserve

Post-hoc separations, labelled post-hoc, from the same run:

    master vs gen1   AUC 0.986      detection, already known
    gen1 vs gen2     AUC 0.644      one generation apart: NOT readable
    gen1 vs gen3     AUC 0.807
    gen1 vs gen4     AUC 0.835      two or more apart: readable
    gen2 vs gen3     AUC 0.720
    gen3 vs gen4     AUC 0.609

**Generation counting does not work at one-generation resolution and does work
at two or more**, on MP3, with this probe. Per file the monotonicity is noisy
(11 of 24 strict, 15 of 24 within 0.05); in the population the median converges
cleanly at every step. That is a real effect measured against a bound it did not
clear, which is the honest way to describe it: the fixed point converges, and
the convergence is visible in a population and not reliable in one file.

**Ladder A is flat.** ffmpeg's AAC chain reads 3.27, 3.31, 3.35, 3.34 — no
convergence at all under an MP3 probe, AUC 0.493, chance. Read beside the
attribution run of the same day, which found self-pairing perfect for MP3 and
Opus and absent for AAC and Vorbis, the same boundary appears twice in one day
from two directions: **some codecs have a re-encode fixed point that another
pass can find, and ffmpeg's AAC does not.**

## What would be needed to make counting usable

A per-file read, not a population median: R at the best phase over the full 576
search rather than the three canonical phases, and a second instrument beside it
(the residual floor already discriminates generations in principle). Both are
one experiment and it gets its own registration. Nothing here may be quoted as
"the engine counts generations" — on one file, at one generation, it does not.
