# Rule 1's gate A yields to depth — registered 2026-09-26, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. The derivation below traces Rule 1's gates offline on the engine's
own readings (`fd-r1w/trace_r1.py`, engine 1.17.0); no verdict has been
computed with the repair.

---

## Where this comes from

The stereo-spread registration of 2026-09-25 found that the halves of one
track disagree through Rule 1's +50, present in one half only at an edge that
barely moves. Traced gate by gate on the 88 halves, the half that loses the
+50 loses it at **gate A on 6 of 9 tracks** and at the container window on the
other 3.

Gate A (`CUTOFF_VARIANCE_THRESHOLD = 130`): when the cutoff read in the three
30 s windows of a file over 90 s wanders by more than 130 Hz (standard
deviation), Rule 1 exits: "authentic FLACs often have variable cutoffs". On a
128 kbps LAME wall at 16 kHz the reading wanders by 250-500 Hz with the music of
each window (a quiet window reads the wall lower), so a real transcode walks
out through the gate meant for masters. The WALL_GATE registration named this
on 2026-09-08 (gate A acquitted a 192 kbps transcode at 120 s) and left it open
for want of **genuine full-length tracks with a cutoff under 19 kHz** — gate A
only acts on files over 90 s, so every 60 s corpus this project owns has NaN
wander and never reached it. That corpus now exists: 28 CD tracks ripped by
their owner (EAC, AccurateRip 16/16 on the 16 that carry a log), loud
1995-2002 masters, 8 of them passing through gate A today.

## The repair

**Gate A yields to depth**, as gate D and the container window already do
since 1.13.16: when the band above the edge is digital silence
(`floor_is_digital_silence`: floor ≤ `DEEP_FLOOR_DB` = −58 dB, edge under
19,500 Hz), the wander does not skip Rule 1. A codec low-pass leaves silence
above its wall whatever the music does to where the wall is read; a master's
own roll-off keeps an analogue or dither floor. Shallow or unknown floor: gate
A decides exactly as in 1.17.0. `rule1_may_consult_container` mirrors it.

Rejected on the same trace: removing gate A outright. It adds +50s on 10
tracks of the library sample and 1 of Dust-to-Digital that the depth variant
does not touch.

## Derivation (`fd-r1w/trace_r1.py`: Rule 1's exits on the engine's readings, three orders of the gates)

| population (full-length tracks) | files | exit at gate A today | Rule 1 +50 today | gate A removed | **gate A yields to depth** |
|---|---|---|---|---|---|
| attested CDs (owner rips) | 28 | 8 | 0 | 0 | **0** |
| full-length genuine | 12 | 0 | 0 | 0 | **0** |
| received files (FLAC) | 17 | 7 | 0 | 0 | **0** |
| wild genuine (the purged set) | 148 | 20 | 0 | 0 | **0** |
| **library sample** (one track per album, `D:\FLAC\Internal`, unlabelled) | 1,726 | 182 | 22 | 32 | **22** |
| **Dust-to-Digital** (78 rpm, cylinders, unlabelled) | 1,896 | 33 | 2 | 3 | **2** |
| **Awesome Tapes From Africa** (cassettes, unlabelled) | 304 | 31 | 10 | 16 | **16** |
| halves of 44 full-length tracks (32 transcodes) | 88 | 16 | 39 | 51 | **45** |
| attested CDs → LAME 128 / 192 / 256 (full length) | 84 | 15 | 58 | 73 | **73** |
| full-length LAME 128/192 (`long_mp3`) | 24 | 4 | 18 | 21 | **18** |
| full-length 320 / Vorbis (`TR320_*`, `TRVORB_*`) | 8 | 1 | 4 | 5 | **4** |

The six new Rule 1 +50s among the unlabelled cassettes: five tracks of one
album (Papé Nziengui, *Kadi yombo*, ATFA029) whose other five tracks Rule 1
already reads at a 15-15.5 kHz wall with digital silence above (−58 to −66 dB),
and one track of Teno Afrika, whose other ATFA album Rule 1 already reads at
18,750 Hz. Consistent with how the engine already reads those albums; not
evidence of anything, the files carry no label, and this document does not
claim them.

The trace's `now` column was checked against `apply_rule_1_mp3_bitrate` itself
on every file that reached a cell: 0 mismatches.

## Criteria, registered before the passes run

Before = 1.17.0 (worktree at tag `v1.17.0`); after = the same tree with the
repair only. Same files, same order, `--sample-duration 30`, `--workers 2`,
**torch live, default mode** (what a user runs). Corpora: the 28 attested CD
tracks, the 12 full-length genuine, the received folder, the wild genuine,
**every library / Dust-to-Digital / ATFA track that exits at gate A today**
(246 files — the only files the repair can reach among them), the 88 halves,
the 84 attested transcodes, `long_mp3` (24) and the 8 full-length transcodes.

| # | criterion | bound |
|---|---|---|
| **A1** | labelled genuine files (attested, full-length, received, wild) newly convicted | **0** |
| **A2** | labelled genuine files newly signalled (`WARNING`+) | **0** |
| **A3** | every mover gains Rule 1's +50 with a floor at or under −58 dB and a wander over 130 Hz, and nothing else in its breakdown changes except what that +50 does to the short-circuits — any other mover withdraws this document | all |
| **A4** | movers among the 246 unlabelled gate-A tracks | exactly the 6 cassette tracks named above, or fewer; any other name is reported and examined before shipping |
| **P1** | halves in disagreement, of 44 | after < 13 |
| **P2** | attested transcodes signalled | after ≥ before + 10 |
| **E1** | transcodes losing a signal or a conviction | **0** |

A1, A2, A3 or E1 breached: does not ship. A4 breached: each extra mover is
listed with its spectrum reading and the decision to ship is taken on that
list, in writing, in the results.

## What this does not touch

* The **container window** (the other 3 of the 9 halves: LAME 192 walls at
  18,750 Hz read in the 256 kbps cell, FLAC-equivalent 560-580 kbps against a
  600-850 window). Its own registration.
* The **CNN** swinging between halves (9 of 13): a different instrument on
  different 10 s windows; not addressed.

Results are appended below, after the runs, in a section dated after the fact.
