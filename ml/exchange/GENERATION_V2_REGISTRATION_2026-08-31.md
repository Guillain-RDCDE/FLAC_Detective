# Counting generations, layer two — a per-file read. Registered before the run

Written and committed **before `ml/generation_v2_probe.py` is run once**.

---

## What layer one measured

`GENERATION_COUNT_REGISTRATION_2026-08-30.md`: the median R falls cleanly at
every generation on a libmp3lame ladder (0.877, 0.486, 0.311, 0.227), no master
falls below the one-generation median (**G3 held**), and **per file it is
noisy** — 11 of 24 strictly monotone, and gen1 against gen2 at AUC 0.644 against
a registered 0.75. Counting reads at two generations apart and not at one.

The stated suspicion was that the per-file noise comes from the instrument
rather than from the files: layer one read R at three canonical phases
{0, 529, 47}, and the fixed point is grid-locked with period 576 and zero
tolerance. Three phases out of 576 is a coarse instrument. Layer two tests that
suspicion and nothing else.

## The change, and the only one

**The full phase search**, stepped: R is read at the best of 72 phases
(`range(0, 576, 8)`) instead of 3. Step 8 rather than 1 because 576 round-trips
a file is eight hours for this ladder and 72 is forty minutes — a compromise
stated here rather than discovered in the results. Everything else is identical
to layer one: same 24 sources, same libmp3lame-320 ladder, same four
generations, same R.

If the per-file noise is the phase grid, a finer grid must reduce it. If it does
not, the noise is in the files and generation counting stays a population
statistic, which is a result worth having and closes the question.

## Predictions

| # | prediction | bound |
|---|---|---|
| **H1** | **Monotonicity improves.** Files strictly monotone across generations 1→4 | **≥ 16 of 24**, against 11 at three phases |
| **H2** | **One generation becomes readable.** AUC(gen1 vs gen2) | **≥ 0.75**, the bound layer one missed at 0.644 |
| **H3** | **The medians do not move much.** The per-generation medians stay within **0.15** of layer one's (0.877, 0.486, 0.311, 0.227) | a control: a finer phase search should sharpen the reading, not relocate it |
| **H4** | **The search finds something to find.** The best phase is a phase other than 0 on **≥ 25 %** of reads | if it is always 0, the extra 69 phases bought nothing and H1/H2 cannot be attributed to them |

**H2 is the one that matters.** It is the bound layer one failed, re-run on a
better instrument. If it fails again, the honest sentence is that this engine
cannot tell one generation from two, and it goes in the changelog in those
words.

**H4 is the control.** Layer one found phase 0 best on 100 % of reads, which is
what a clean re-encode chain should do — each decode is delay-trimmed back to
the start. If that holds at 72 phases too, then H1 and H2, whatever they say,
say nothing about the phase grid, and the registration will have answered a
different question than it asked. That is worth knowing before the numbers
arrive rather than after.

Results appended below, dated after the fact.

---

# RESULTS — appended 2026-08-31, criteria unedited above

96 measurements, 24 sources, 72 phases per read instead of 3.
`ml/generation_v2_probe.csv`.

| # | bound | layer one | layer two | |
|---|---|---|---|---|
| H1 monotone per file | ≥ 16/24 | 11/24 | **11/24** | failed |
| H2 AUC(gen1 vs gen2) | ≥ 0.75 | 0.644 | **0.644** | failed |
| H3 medians stay put | ≤ 0.15 drift | — | **0.000 on all four** | held |
| H4 a non-zero phase is chosen | ≥ 25 % | 0 % | **0 of 96** | failed |

    median R by generation, layer two:  0.877  0.486  0.311  0.227
    median R by generation, layer one:  0.877  0.486  0.311  0.227

## The question is closed, and the control is what closes it

**Twenty-four times more phases and not one number moved.** The AUC is identical
to three decimals, the medians to three decimals, the monotone count to the file.

H4 is why, and it was written as the control precisely so this could not be
mistaken for something else: **the search chose phase 0 on 96 reads out of 96**.
The 69 extra phases had nothing to find. A clean re-encode chain never leaves the
grid — each decode is delay-trimmed back to the start — so the phase search is
answering a question this ladder does not pose. It is the right instrument for a
*wild* file, which sits wherever its editing left it; it is a no-op for a chain
built in a temp directory.

So the suspicion the registration was written to test is **refused**: the
per-file noise in generation counting is not the phase grid. It is in the files.

## What that leaves, stated as narrowly as it deserves

Generation counting on this instrument is a **population statistic**. The median
falls cleanly at every step and it will keep doing so; on a single file, one
generation against two reads AUC 0.644 and no amount of phase resolution will
improve it, because phase resolution was never the limit. Two generations apart
remains readable (0.807 and 0.835 from layer one).

Nothing here may be quoted as "the engine counts generations". What can be
quoted is that **the fixed point converges monotonically in a population, on
MP3, and that a per-file read needs a second instrument rather than a finer
version of this one** — the residual floor being the obvious candidate, and its
own registration the next step if it is ever worth taking.

Layer one asked whether the instrument was the limit. Layer two answered no, in
one run, and that is what a control is for.
