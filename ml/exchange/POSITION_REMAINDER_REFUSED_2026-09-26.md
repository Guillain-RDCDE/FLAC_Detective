# Three repairs refused on their derivation: gate A over shallow floors, the 256 kbps container window, and more CNN windows — 2026-09-26

**Nothing here was registered and then run.** All three candidates were priced
offline, on the engine's own readings, before any registration could be
written, and all three failed the one criterion every registration in this folder
carries first: no genuine file may move toward accusation. They are recorded so
that nobody spends the same afternoon again, and so the numbers exist.

Context: after 1.18.0 (`GATE_A_DEPTH_REGISTRATION_2026-09-26.md`) the halves of
full-length transcodes still disagree 13 times in 44. Three causes were left
open: gate A over floors shallower than −58 dB, the container window, and the
CNN. This document closes all three as "not repairable with the instruments this
engine has".

Tool: `ml/rule1_gate_trace.py` (Rule 1's exits, gate by gate, on the engine's
readings; the `now` order checked against `apply_rule_1_mp3_bitrate` itself).
Populations: the 60 s corpora (`audit_corpus`, v2 genuine, eleven arms), the
full-length labelled genuine (28 attested CD tracks, 12 full-length, the
received folder, the wild 148), the unlabelled full-length library sample
(1,726, one track per album of the direction's library), Dust-to-Digital
(1,896), Awesome Tapes From Africa (304), and the full-length transcodes (the
88 halves, 84 attested-CD transcodes, 24 `long_mp3`, 8 `TR320`/`TRVORB`).

---

## 1. Gate A over a shallow floor: "a hard wall read unevenly is still a wall"

After 1.18.0, 290 files still exit Rule 1 at gate A (wander > 130 Hz, floor
above −58 dB). Their step across the edge (`edge_step_db`):

| population | files | step min / median / max |
|---|---|---|
| labelled genuine | 35 | 0.9 / 3.2 / **13.0** |
| transcodes | 15 | **16.1** / 24.7 / 41.6 |
| unlabelled (library, 78 rpm, cassettes) | 240 | 0.6 / 7.1 / 43.9 |

On the labelled files the step separates cleanly. The candidate — gate A also
yields when the step is at least 15 dB — then gives, on the full rule:

| population | new Rule 1 +50 |
|---|---|
| labelled genuine | 0 of 35 |
| transcodes | 10 of 15 |
| **unlabelled** | **7 of 240** |

The seven, read one by one: Martin Denny, *Exotica* (1958, two tracks, steps
30.5 and 40.8 dB), Ali Farka Touré, *Dit Farka* (1979, 16.6 dB), a
Dust-to-Digital 78 rpm transfer (15.0 dB), Leftfield (17.2 dB), Manu Chao
(42.4 dB) and Fabiano do Nascimento (26.6 dB). Old masters with hard edges are
exactly what the unlabelled set is there to show; raising the bar does not
separate them either, since the transcodes' steps (16-42 dB) cover the same
range. **Refused.** The labelled population was too small to see what the
library shows at once.

## 2. The container window of the 256 kbps cell

Three of the nine half-swings of 2026-09-25 are LAME 192 walls read at
18,750 Hz, in Rule 1's 256 kbps cell (18,500-19,500 Hz), whose container window
is 600-850 kbps; those halves compress to 560-580 kbps and exit under the
window. The candidate is the window's lower bound.

On the cell's window exits, all populations:

| | under the window | over the window |
|---|---|---|
| labelled genuine | **566 kbps** (wild, *pachy* 2025-07-31, 18,750 Hz) | 870, 921 |
| unlabelled | 581 (a Dust-to-Digital speech) | 878-1,593 |
| transcodes | 423-599 (the four halves at 560-580) | 862-1,066 |

The genuine file sits at the same cutoff and the same size as the four halves
(560, 572, 577, 579 kbps). Any lower bound that admits the halves admits it.
Over the window the populations overlap the same way (genuine 870-921 against
transcodes from 862), which is the container-window cliff the WALL_GATE
registration named. What differs is the floor above the edge (genuine −32.0 dB,
the halves −41.6 to −53.1), but genuine hard walls under 19.5 kHz reach
−55.2 dB (DEPTH_GATE derivation), so a floor bar between them is not
available either. **Refused.**

## 3. More CNN windows

The CNN (Rule 12) averages its calibrated probability over three 10 s windows
centred at 25/50/75 % of the file; on 9 of the 13 disagreeing tracks its +30
fell in one half only. The candidate is more windows, which should average the
music out. `ml/cnn_windows_probe.py` ran the shipped inference at 3, 5 and 7
windows (same model, same calibration, same rolloff gate) on the 88 halves,
the labelled genuine (attested, full-length, wild, audit, v2) and four arms.

| | 3 (shipped) | 5 | 7 |
|---|---|---|---|
| halves where the CNN scores in one half only, of 44 | 12 | **6** | 11 |
| mean score gap between halves | 7.8 | 4.2 | 6.4 |
| genuine halves scoring | 0 of 24 | 0 | 0 |
| labelled genuine newly scoring, against 3 | — | **2** | 2 |

Two reasons to refuse, either sufficient. **It does not converge**: if more
music settled the reading, 7 windows would do at least as well as 5; they do
nearly as badly as 3. Choosing 5 because it wins on this bench would be fitting
the window placement to these 44 tracks. **And it accuses genuine files**: two
labelled genuine files that the rolloff gate set aside at 3 windows (it reads
the MEDIAN rolloff of the windows, and different windows move that median)
score at 5 — a wild keyboard solo (bt 2026-08-11) 0 → +30 at p 0.943, above
the 0.90 at which the WARNING floor can lift a silent file, and a v2 genuine
file 0 → +30 at p 0.983 (a third loses its +14). **Refused.**

## What stays true

The halves' disagreement is, for the first two mechanisms, a statement about the
information in the file: a 192 kbps LAME wall at 18.75 kHz over a −42 dB floor
and a genuine taper recording at 18.75 kHz over a −32 dB floor, both compressing
to ~570 kbps, are one reading apart, and that reading is not one this engine
takes. A second instrument, independent of the cutoff, is what it would take.
