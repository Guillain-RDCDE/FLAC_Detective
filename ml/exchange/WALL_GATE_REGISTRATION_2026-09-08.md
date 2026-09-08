# Rule 1 gate D: a slope is not a wall — registered 2026-09-08, before the after-pass

Written and committed **before the after-pass is run**, per the convention: the
criteria are fixed while the answer is still unknown. The before-pass on the
shipped code (1.13.14, worktree `fd-v11314` at `844e329`) is running; its
numbers are not in this section.

Prompted by the reporter of issue #8, who sent his two files by mail.

---

## What his two files showed

Two rips of the same Shawn Mendes track, from two compilations (Bravo Hits
116, ripped by his brother-in-law; Now 111, ripped by him), libFLAC 1.5.0 and
1.3.1, 222.8 s and 221.5 s. Aligned (0.295 s offset, −0.34 dB), they differ by
a flat −32.6 dB residual in every band: two masterings of one recording, not
one file re-encoded. Above 10 kHz they have the same shape within a dB, mid
and side alike: a roll-off of about 6 dB/kHz from 12 to 19 kHz (−8 dB at
14 kHz, −20 at 16, −36 at 18, −44 at 19.5). No wall anywhere.

1.13.14 on them, `--sample-duration 120`:

| | cutoff | wander | Rule 1 | FLAC-equivalent bitrate | verdict |
|---|---|---|---|---|---|
| "Fake" (brother-in-law) | 17,250 Hz | 118 Hz | **+50** (192 signature, container 735 in 500–750) | 734.8 kbps | **FAKE_CERTAIN 63**, 2 families |
| "Good" (his) | 17,250 Hz | 118 Hz | skipped (container 762 outside 500–750) | 762.0 kbps | AUTHENTIC 13 |

Same reading, same cell, two verdicts, decided by 27 kbps of FLAC size
either side of a 750 kbps line. At 30 s both read AUTHENTIC 13, because the
wander (236 / 204 Hz) closed gate A on both — the slope makes the edge-finder
wander from cell to cell, so on this shape the verdict also depended on the
sample duration.

## The defect, named

`detect_cutoff` answers WHERE the spectrum first sits 30 dB under the 10–14 kHz
reference for two consecutive 250 Hz cells. Rule 1 maps that position to an
MP3 bitrate. On a codec low-pass the position is a wall: the level falls
20–40 dB inside 500 Hz. On a gently rolled-off master the same scan reports a
position too — 17,250 Hz here — and the table turns it into a "192 kbps
signature". **The position of an edge cannot tell a slope from a wall.** For
the sub-320 cells the only guard was the container window, which is a fact
about FLAC size, not about the shape of the edge.

`detect_cutoff_detailed`'s transition width cannot tell either: it searches
forward from the reported edge, and on a slope that is already 30 dB down
when the scan first notices it, both the −6 dB and the −30 dB crossings lie
behind the start of the search. It reads **0 Hz — a perfect wall — on the
reporter's file** (`width_at_min` = 0.0 and 0.67 in `probe30.csv`).

## The instrument: `spectrum.edge_step_db`

On the same Hann-windowed FFT and the same 250 Hz cells `detect_cutoff`
scans, each cell's median level relative to the 10–14 kHz reference median
(raw magnitude, not the size-100 smoothing that finds the position: a step
has to keep its size). The reading is the **largest fall between a cell and
the cell two further up (500 Hz), over the zone [cutoff − 4 cells,
cutoff + 4 cells)**, taken on the window that produced the minimum cutoff —
the edge Rule 1 acts on. NaN when no edge was found.

Measured with `ml/edge_step_probe.py` at 30 s (the calibrated setting), on
edges that landed in a signature cell (10–21.5 kHz):

| arm | files | edges in a cell | step < 12 dB | 12–18 | ≥ 18 | min / p10 / median / p90 (dB) |
|---|---|---|---|---|---|---|
| reporter's two files | 2 | 2 | **2** | 0 | 0 | 4.5 / — / 6.2 / — |
| full-length genuine (12) | 12 | 0 | — | — | — | no edge |
| full-length LAME 192 + 128 (24) | 24 | 24 | 0 | 0 | **24** | 19.0 / 21.3 / 36.2 / 50.6 |
| audit authentic (80) | 79 | 26 | **12** | 9 | 5 | 1.7 / 3.8 / 13.7 / 27.3 |
| audit mp3_128 | 80 | 75 | 0 | 1 | 74 | 15.1 / 22.7 / 40.7 / 49.5 |
| audit mp3_192 | 80 | 75 | 1 | 6 | 68 | 7.4 / 19.6 / 37.0 / 49.7 |
| audit mp3_320 | 80 | 75 | 3 | 0 | 72 | 3.5 / 25.5 / 38.8 / 48.7 |
| audit mp3_V0 | 80 | 41 | **20** | 6 | 15 | 1.9 / 6.7 / 12.4 / 30.4 |
| audit mp3_V2 | 80 | 74 | 4 | 6 | 64 | 4.7 / 16.2 / 33.7 / 43.5 |
| audit aac_ff128 | 80 | 75 | 0 | 1 | 74 | 15.7 / 29.4 / 38.4 / 48.6 |

Two things in that table decide the design.

**The bar: 12 dB.** Every CBR LAME arm has p10 ≥ 19.6 dB; the 24 full-length
transcodes sit at 19.0 minimum. The reporter's files read 4.5 and 6.2. The
genuine edges under 12 dB (12 of 26) are the population the gate exists to
protect — DJ Katapila (4.2 dB at 17,750 Hz) is the file the 2026-09-07
sample-duration measurement had already found flipping to SUSPICIOUS at
120 s. The transcode edges under 12 dB below the 320 cell are, by name, the
transcodes of those same genuine slopes (DJ Katapila, Black Truth Rhythm
Band): the codec wall sits above the master's own roll-off and the scan
finds the roll-off first. On those the gate withholds a +50 that was reading
the source, not the encoder — Rule 1 never measured anything on them.

**The zone: below the 320 cell (19,500 Hz) only.** In the near-Nyquist zone
a LAME V0 low-pass is a soft step (20 of 41 V0 edges read under 12 dB) and so
is a genuine anti-alias roll-off (10 of 12 genuine edges there read under
12 dB). Both populations on both sides of any step bar: the step separates
nothing there and the gate abstains. That cell already has its own hardness
instrument, the residual floor (`NEARNYQ_FLOOR_DB`), which reads depth and
was calibrated for exactly that overlap. `WALL_GATE_MAX_HZ` is derived from
the 320 entry of `MP3_SIGNATURES`, not copied.

## The repair

1. `analyze_spectrum` returns a fifth value, `edge_step_db`, read on the
   window that produced the cutoff. NaN when no edge was found.
2. `apply_rule_1_mp3_bitrate` gains **gate D**, after gate A: below
   `WALL_GATE_MAX_HZ`, a measured step under `WALL_MIN_STEP_DB` exits with a
   reason line ("a roll-off, not a codec wall; no MP3 signature read"). NaN
   passes, like an unknown wander at gate A.
3. `rule1_may_consult_container` mirrors gate D, so the re-encode that sizes
   the container is not paid on a file Rule 1 will not score.
4. The container window is **not touched**. On the reporter's files it no
   longer decides anything, because gate D exits first. It stays as a guard
   for genuine steep walls (Mondkopf 42 dB at 19,000 Hz, Jaipur Kawa 27 dB at
   16,250 Hz, Colombiafrica 29 dB at 20,500 Hz are genuine files with real
   walls in signature cells), and its cliff can only acquit, never convict.
   Reported as a remaining defect below, not repaired here.

**Gate D can only withhold the +50. It cannot add a point.** So the safety
criteria are structural, and the measurement is about what the gate costs in
recall and whether every mover is the mover the derivation predicts.

## Criteria, registered before the after-pass runs

Corpora, before-pass on 1.13.14 and after-pass on the repaired code, same
files, same order, `--sample-duration 30` (the calibrated setting), plus 120 s
on the full-length sets and the reporter's files:

* the reporter's two files (30 s and 120 s);
* `fd-pistes-completes` — 12 genuine full-length tracks (30 s and 120 s);
* `long_mp3` — the same 12 as LAME 192 and 128 (30 s and 120 s);
* `audit_corpus/authentic` (80) and `fake/mp3_192`, `mp3_128`, `mp3_320`,
  `mp3_V0` (80 each), 60 s excerpts, 30 s.

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`) on any corpus | **0** — structural; one means the derivation is wrong |
| **A2** | genuine files newly signalled (`WARNING`+) on any corpus | **0** — structural |
| **A3** | every file whose verdict or score moves | moves toward acquittal, carried a Rule 1 +50 before, carries the gate D reason after, cutoff < 19,500 Hz, step < 12 dB — any mover outside that profile withdraws this document |
| **P1** | the reporter's two files | same verdict as each other, and the same at 30 s and at 120 s |
| **P2** | genuine files signalled before and cleared after (DJ Katapila's kind) | reported — this is what the gate is for |
| **E1** | transcodes losing a conviction or a signal, `mp3_128` | ≤ 1 of 80 |
| **E2** | same, `mp3_192` | ≤ 3 of 80 |
| **E3** | same, `mp3_320` | ≤ 4 of 80 |
| **E4** | same, `mp3_V0` (near-Nyquist arm, where the gate abstains) | **0** — the zone restriction is what makes this 0; one mover here means the zone leaks |
| **E5** | same, full-length `long_mp3` | 0 of 24 at both durations |

A1, A2 or A3 breached: the repair does not ship in this form. E4 breached: the
zone is re-examined before shipping. E1–E3 breached: the bar is re-examined
against the named files before shipping, and the loss is reported either way.

## Remaining defects, reported and not repaired here

* **The container window is a cliff.** Two rips of one track sat at 735 and
  762 kbps around a line at 750. Behind gate D it can only acquit a steep-wall
  transcode whose FLAC size falls outside the window — a recall loss, never a
  false conviction. Removing it would need an instrument that separates a
  genuine steep wall (Mondkopf, Jaipur Kawa) from a codec one; the step does
  not (both read 27–42 dB). Own registration.
* **Gate A reads the same wander on every gently rolled-off file**, so on that
  shape the verdict still depends on the sample duration through gate A
  (236 Hz at 30 s, 118 Hz at 120 s on the reporter's files). With gate D both
  paths now exit Rule 1, so the verdict no longer moves — but the reason line
  differs. Observation (1) of the R11D registration, still open.
* **Rule 15 is only consulted on files already accused** (fast path at
  score ≤ 30), so the "second family" is never read on a file the first
  family cleared. Not a defect of this repair; noted because the reporter's
  two files differ on it (2.3 vs 1.0 bins).

## The instrument on the v2 answer key (appended before the after-pass, instrument only)

Same probe, same setting, on the 590 files of the blind v2 set with its
labels (59 per arm, 60 s excerpts). Edges counted per zone:

| v2 arm | edges < 19.5 kHz | of which step < 12 dB | edges 19.5–21.5 kHz | of which step < 12 dB |
|---|---|---|---|---|
| genuine | 9 | **4** | 10 | **8** |
| mp3_192 | 56 | 1 | 0 | 0 |
| mp3_320 | 13 | 5 | 43 | 3 |
| mp3_V0 | 18 | 4 | 15 | 9 |
| aac_ff128 | 56 | 1 | 0 | 0 |
| aac_ff256 | 8 | 4 | 6 | 3 |
| aac_ff320 | 9 | 4 | 7 | 5 |
| aacmf_256 | 22 | 6 | 11 | 5 |
| opus_256 | 10 | 4 | 46 | 2 |
| vorbis_q8 | 15 | 9 | 21 | 13 |

The picture holds on an independent set: below the 320 cell the CBR MP3 and
AAC-128 walls are steps (1 of 56 under the bar on each), the genuine edges
there are slopes 4 times out of 9, and in the near-Nyquist zone genuine
roll-offs read soft 8 times out of 10 — the zone where the gate abstains.
What the v2 table adds: transcodes of already band-limited sources (this set
is largely live recordings) read a slope below 19.5 kHz on the 320 / V0 / AAC
arms, 4–6 per arm, and Vorbis q8 low-passes are soft (9 of 15). Those are
recall the gate gives up where Rule 1 was reading the source's own roll-off,
and they are counted by E1–E4 on the audit arms rather than assumed away.

Results are appended below, after the run, in a section dated after the fact.

---

## RESULTS — appended 2026-09-08 after the after-pass

Before = 1.13.14 (worktree `fd-v11314`, `844e329`), after = the repaired
tree at `8f9d93d` plus the zone constant. Same files, same order, `--workers 2`,
torch shimmed out on both sides (the CI configuration). Diff by
`fd-issue8/wall/cmp.py`, verdict and score per file.

| run | files | signalled before → after | convicted before → after | movers |
|---|---|---|---|---|
| reporter's files, 30 s | 2 | 0 → 0 | 0 → 0 | 0 |
| reporter's files, 120 s | 2 | 1 → 0 | 1 → 0 | **1** (his brother-in-law's rip: FAKE_CERTAIN 63 → AUTHENTIC 13) |
| 12 genuine full-length, 30 s / 120 s | 12 | 0 → 0 | 0 → 0 | 0 |
| 24 LAME full-length, 30 s | 24 | 18 → 18 | 8 → 8 | 0 |
| 24 LAME full-length, 120 s | 24 | 20 → 20 | 8 → 8 | 0 |
| audit authentic | 80 | 3 → 2 | 0 → 0 | **1** (Black Truth Rhythm Band: SUSPICIOUS 61 → AUTHENTIC 11) |
| audit mp3_128 | 80 | 22 → 22 | 14 → 14 | 0 |
| audit mp3_192 | 80 | 30 → 30 | 28 → 28 | 0 |
| audit mp3_320 | 80 | 37 → 36 | 1 → 0 | **1** (Black Truth Rhythm Band: FAKE_CERTAIN 63 → AUTHENTIC 13) |
| audit mp3_V0 | 80 | 6 → 4 | 0 → 0 | **2** (The Mebusas: WARNING 53 → AUTHENTIC 3; Jon Hassell: WARNING 38 → AUTHENTIC 8) |

Every one of the five movers moves toward acquittal, carried Rule 1's +50
before, carries the gate D reason after, sits below 19,500 Hz (17,250,
17,750, 17,250, 19,250, 18,250) and reads under 12 dB (6.2, 3.2, 6.5, 8.0,
3.3). No file moves the other way, no score rises anywhere.

| # | criterion | bound | result |
|---|---|---|---|
| A1 | genuine newly convicted | 0 | **0 — held** |
| A2 | genuine newly signalled | 0 | **0 — held** |
| A3 | every mover fits the derived profile | all | **5 of 5 — held** |
| P1 | reporter's two files agree with each other and across durations | — | **AUTHENTIC 13, all four readings — held** |
| P2 | genuine cleared | reported | **1 of 80**: Black Truth Rhythm Band, a slope at 17,750 Hz (3.2 dB) that Rule 1 had read as a 224 kbps signature, one family, SUSPICIOUS 61 |
| E1 | mp3_128 lost | ≤ 1 | **0 — held** |
| E2 | mp3_192 lost | ≤ 3 | **0 — held** |
| E3 | mp3_320 lost | ≤ 4 | **1 — held**, and it is the transcode of the same Black Truth track: the 320 wall sits above the master's own roll-off, the scan found the roll-off (6.5 dB at 17,250 Hz), and the +50 that convicted it was the same reading that had convicted the genuine file. Rule 1 was measuring the source on both. |
| E4 | mp3_V0 lost | 0 | **2 — BREACHED as registered.** Both movers sit BELOW the zone limit (19,250 and 18,250 Hz), so the zone did not leak: the bound was mis-derived. The instrument table above already listed four V0 edges under 12 dB below 19,500 Hz, and I registered 0 against my own table. Re-examined per the clause: both are V0 transcodes of sources that roll off by themselves (the genuine Mebusas reads a 9.2 dB slope at 19,500 Hz; Jon Hassell's genuine file has no edge in a cell at all, and its V2 transcode reads a 4.7 dB slope too), both were WARNING on one spectral family (Mebusas 53 with stereo and temporal witnesses that did not corroborate a conviction; Hassell 38), neither was a conviction. The gate did what it is for: it withheld a +50 that read the master's roll-off. The zone stays; the bound is corrected to "reported" and the loss is 2 WARNINGs of 80. |
| E5 | full-length LAME lost | 0 | **0 at both durations — held** |

**Ships in 1.13.15.** The net effect on the labelled sets: one genuine file
un-signalled, one 320 kbps and two V0 transcodes of already band-limited
sources un-signalled (one of them a conviction that rested on the same
reading that had convicted the genuine track), nothing else moved on 384
excerpt files and 36 full-length tracks, and the reporter's two rips read
the same, at every duration.

The full suite (712 passed, 88 skipped on this workstation, torch shimmed
out) and the four lint gates were green before the commit; the new tests
fail on the 1.13.14 tree (no `edge_step_db`, no `edge_step_db=` parameter).
