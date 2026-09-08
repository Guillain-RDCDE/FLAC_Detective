# TEST 11D is removed: a 250 Hz grid cannot measure wow and flutter — registered 2026-09-08, before measurement

Written and committed **before the after-pass is run**, per the convention: the
criteria are fixed while the answer is still unknown. The before-pass on the
shipped code (1.13.13) is already running; its numbers are not in this section.

Prompted by the reporter of issue #8, who sent the two screenshots asked of him.

---

## What his screenshots showed, and what my reply had claimed

My reply of 2026-09-07 told him his verdict flipped between 30 s and 120 s
because a longer window read different audio and the cutoff reading crossed a
signature cell. **On his file that is false.** Both screenshots read
`Cutoff 17.2 kHz`. Same reading, same cell. What differs is the per-rule
list:

| | 30 s | 120 s |
|---|---|---|
| R11B roll-off (−5.6 dB/kHz) | +20 cassette | +20 cassette |
| R11D "natural cutoff variation (236 Hz, wow/flutter)" | **+15 cassette** | — |
| cassette evidence vs gate 25 | 35 → **protected, −40, Rule 1 disabled** | 20 → not protected |
| Rule 1 (192 kbps signature) | cancelled | +50 |
| verdict | `Authentic 0` | `Fake 63`, 2 families (spectral, stereo) |

At 30 s the three spectral windows sit 30 s wide at a quarter, a half and
three quarters of the track, and their three cutoff readings land in cells
that differ by two — the wander reads 235.7 Hz, the "one window two cells
away" value the grid can produce. At 120 s the windows touch and cover the
whole track, the three readings agree, the wander reads 0, and the cassette
protection lapses. The setting never touched the reading; it touched a
statistic that a cassette rule was reading as tape flutter.

## Why 11D cannot measure what it claims

Wow and flutter are frequency modulation of a few tenths of a percent at
rates of roughly 0.5 to 10 Hz. At a 17 kHz edge that is a movement of a few
tens of hertz, at a rate no three-window sample spaced a minute apart can
resolve, on a grid whose cell is 250 Hz. The statistic 11D reads is "did the
edge-finder land in different cells in three windows of different music". It
did, and so it does on ordinary digital material: the twelve-window probe of
2026-09-07 (`SAMPLE_DURATION_MEASUREMENT_2026-09-07.md`) found the per-window
spread of the reading to have the **same distribution on genuine CD rips and
on MP3-192 transcodes** (median 0, upper quartile 500–750 Hz, tails to
5 kHz). A statistic distributed identically on both populations is evidence of
nothing, whatever it is named.

The 30/08 repair narrowed the band so that one cell of wander no longer
counted, on the argument that "two cells or more is movement the grid cannot
manufacture". The grid cannot; the music can, and does. The 30/08 test
(`test_11d_real_wander_still_reads_as_flutter`) pinned that argument and is
withdrawn with it.

## The consequence, derived from the weights rather than guessed

The other tests contribute 11A +30 (hiss) and 11B +20 / −20 (roll-off), gate
25. With 11D's +15 available, the cassette score S takes values
{−20, 0, 10, 15, 20, 30, 35, 45, 50, 65}. Without it:

| profile | with 11D | ≥ 25 ? | without 11D | ≥ 25 ? |
|---|---|---|---|---|
| 11B alone + 11D (roll-off, wandering edge) | 35 | **yes** | 20 | **no** |
| 11A alone + 11D | 45 | yes | 30 | yes |
| 11A + 11B + 11D | 65 | yes | 50 | yes |
| any profile without 11D firing | unchanged | — | unchanged | — |

So exactly one population moves, and it moves **toward conviction**: files
whose only cassette evidence is a progressive roll-off, on which the edge
reading wandered two cells or more across the three windows. They lose the
−40 and Rule 1 is re-enabled on them. Nothing else can move.

Who is in that population: only files longer than 90 s (a shorter file has
one window and a NaN wander, so 11D never fired on it — which is why **every
measurement corpus this project has, all in 60 s excerpts, is blind to this
test**, and why it took a user with a full-length track to see it), with a
cutoff below 19 kHz (Rule 11 does not run above), a roll-off between −6 and
−3 dB/kHz across 12–18 kHz, and no tape hiss.

## The repair

1. `cassette.py`: TEST 11D contributes nothing for any value of the wander.
   The reading is still logged. The band constants stay where they are for
   Rule 1's gate A, which reads the same statistic for a different purpose
   (skip Rule 1 on a variable spectrum) and is not touched here.
2. `CASSETTE_THRESHOLD` is **not** touched. The 30/08 registration moved a
   phantom constant into the gate because it had applied to every file; this
   +15 applied to a population, and compensating it would preserve the
   acquittals it was handing out.
3. The −40 cassette protection is credited to `Rule11CassetteDetection` in
   `score_breakdown` instead of to `_calculator`. His screenshot's `Why:` line
   read "offset by _calculator −40", which names nothing. Presentation only.

## Criteria, registered before the after-pass runs

Corpora, before-pass on 1.13.13 and after-pass on the repaired code, same
files, same order, `--sample-duration 30` (the calibrated setting) and 120:

* **long_mp3**: the 12 genuine full-length album tracks of
  `fd-pistes-completes/` transcoded with LAME at 192 and at 128 kbps and
  decoded back to 44.1/16 FLAC — 24 full-length transcodes with walls below
  19 kHz, the population 11D can acquit;
* **fd-pistes-completes**: the 12 genuine full-length tracks;
* **audit_corpus** `authentic/` (80) and `fake/mp3_192/` (80), 60 s excerpts;
* the reporter's track is not available and is **reported, not counted**.

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`) on any corpus | **0** — safety, no tolerance |
| **A2** | genuine files newly signalled (`WARNING`+) on any corpus | **0** |
| **A3** | any verdict moving on a 60 s corpus | **0** — by construction; one moving means the mechanism above is wrong |
| **A4** | files that move at all | must have reasons {R11B, R11D} and no R11A before, cutoff < 19,000 Hz, duration > 90 s — any mover outside that profile withdraws this document |
| **E1** | full-length transcodes acquitted by the cassette protection before, and signalled or convicted after | reported — this is what the repair is for |
| **E2** | full-length transcodes still acquitted after (11B alone, 20 < 25, Rule 1 live but not enough) | reported |

A1 or A2 breached means the repair does not ship in this form and the
population that broke it gets its own registration. A3 or A4 breached means
the derivation is wrong and the repair is withdrawn until it is understood.

Results are appended below, after the run, in a section dated after the fact.

---

# RESULTS — appended 2026-09-08, after the passes, criteria unedited above

Before = worktree at `dd4445f` (1.13.13). After = the repaired tree. Both
with the ML rule absent. Reports and scripts in `fd-issue8\dur\`
(`r11d_bench.cmd`, `before_*`, `after_*`, `cmpdur.py`).

## The criteria

| # | criterion | bound | measured |
|---|---|---|---|
| A1 | genuine files newly convicted | 0 | **0** — 12 full-length genuine tracks at 30 s and at 120 s, 80 genuine 60 s excerpts at 30 s: no verdict moved |
| A2 | genuine files newly signalled | 0 | **0** |
| A3 | any verdict moving on a 60 s corpus | 0 | **0** — 80 genuine, 80 MP3-192 |
| A4 | movers outside the {R11B, R11D}, no R11A, cutoff < 19 kHz, > 90 s profile | 0 | **0** — the only files whose report changed at all lost an R11D line and nothing else: `First Snow mp3_128` at 30 s (11D alone, 15 < 25, never decisive) and `Eve mp3_128` at 120 s (same) |
| E1 | full-length transcodes acquitted by the cassette protection before, signalled after | reported | **0 of 24** — on this corpus the protection never fired before either |
| E2 | full-length transcodes still acquitted after | reported | 6 of 24 at 30 s (`Eve 128`, `First Snow 128/192`, `Wolf Drawn 192`, `Lionheart 128/192`), none of them by Rule 11: Rule 1 was live and did not reach the score |

So on every corpus this project owns, the repair changes **no verdict and no
score**. That is the expected shape, not a disappointment: the population it
removes an acquittal from is "roll-off read as natural + edge reading in
different cells across the three windows", and LAME leaves a sharp wall, so
its transcodes rarely present the first half. The reporter's file did, and it
is the only member of the population anyone has produced. Three of the 24
LAME-192 transcodes here (`Eve`, `With Rainy Eyes`, `Good Knight`) **do**
carry 11B's "natural roll-off" +20; each of them was one wandering window
away from the same acquittal, and at 120 s `Eve 192` does wander
(readings 16,750 / 17,500 / 18,750 Hz). That is the exposure this repair
closes, measured on our side as three files that could have flipped and
did not happen to.

## What the before-pass showed about the same statistic, outside this scope

`Eve mp3_192` reads `FAKE_CERTAIN 56` at 30 s and `AUTHENTIC 16` at 120 s
on 1.13.13, **and still does after this repair**: at 120 s its wander is
~830 Hz, above 300, so 11D was never involved — it is **Rule 1's gate A**
("skip on a variable spectrum", `cutoff_std > 130`) that acquits it. Gate A
reads the same statistic this document has just shown to be distributed
identically on genuine and transcoded material. It is left untouched here,
as registered, and it gets its own registration: the question there is
whether gate A protects any genuine population at all, which needs
full-length genuine tracks with walls below 19 kHz, a corpus this project
does not yet have.

Also seen, and not chased: one genuine 60 s excerpt (`022-17 Michel Legrand`)
read a cutoff of 21,750 Hz in yesterday's pass and 22,050 Hz in today's, on
unchanged spectral code, same verdict (`AUTHENTIC 0`). Two further runs read
22,050. A one-cell run-to-run difference on one file out of 160; recorded so
that a later determinism check has a starting point.

## Recall on full-length transcodes, recorded for the next registration

The before-pass is the first time this engine has been run on full-length
LAME transcodes with the ML rule absent. At 30 s: 8 of 24 `FAKE_CERTAIN`,
4 `SUSPICIOUS`, 6 `WARNING`, **6 `AUTHENTIC`** — two of them 128 kbps files
with a 16 kHz wall read as `AUTHENTIC 20`. That is not this document's
subject and no number here is changed by it; it is written down because it
was measured, and because a 128 kbps transcode reading as genuine is a
larger defect than the one repaired above.
