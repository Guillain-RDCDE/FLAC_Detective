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
