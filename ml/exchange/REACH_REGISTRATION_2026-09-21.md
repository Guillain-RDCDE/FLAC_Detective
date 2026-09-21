# Two reach measurements: Vorbis q10, and the re-mastered arm at low bitrates — registered 2026-09-21, before any file is scored

Written and committed **before the arms are scored**, per the convention. No
engine change is attached to this document: both experiments measure the
shipped engine (1.16.0) on arms it has never seen, so that the numbers exist
before anyone else's do.

---

## V — Vorbis at -q 10

**Why now.** Vorbis at its highest quality setting has no low-pass to read
and is the hardest lossy source to tell from lossless. On the Set B half of
the v3 exchange (35 files, built by the other side) 1.13.6 read `vorbis_q10`
at 0 %. That is the only number this project has on q10, it is on someone
else's corpus, and the engine has moved since. A blind q10 set has been
offered by the other side; this measures our own hole first, on our own arm,
so the prediction below is on record before that set exists.

**The arm.** The 80 sources of `audit_corpus/authentic`, round-tripped with
the corpus's own `build_audit_corpus.transcode` (metadata stripped, source
rate forced back, FLAC s16) through `libvorbis -q:a 10`. Control, same run:
the first 40 files of the existing `fake/vorbis_q8` arm.

**The engine.** 1.16.0 working tree, `--deep`, torch 2.14.0 live (Rule 12
runs), `--sample-duration 30`, `--workers 2`.

| # | prediction | bound |
|---|---|---|
| **V1** | the q8 control is signalled (`WARNING`+) — the contrast; without it the arm proves nothing | ≥ 60 % of 40 |
| **V2** | q10 signalled | ≤ 25 % of 80 |
| **V3** | q10 convicted (`FAKE_CERTAIN`) | ≤ 5 % of 80 |
| **V4** | of the q10 files that are signalled, those whose only evidence family is `cnn` | ≥ 80 % |

Basis: the Set B zero, and the fact that every heuristic family here reads an
MDCT codec through a low-pass, a frame grid or a killed side channel, none of
which Vorbis at q10 is known to leave. V2 failing HIGH would be good news and
is reported as a failed prediction all the same.

---

## R — the re-mastered arm below the 320 cell

**Why now.** Three store files in one week — two Beatport AIFFs with a 16 kHz
ceiling (DEPTH_GATE registration) and one 2006 Beatport AIFF in Set B re-keyed
by its builder from genuine to lossy — are the same species: a lossy decode
that went through a delivery or mastering chain afterwards. `remaster_arm.py`
(2026-08-21) built that species at 320 kbps, in the cell where the depth gate
abstains. The depth gate (1.13.16) was derived on two files. This measures
whether it reads the species or only those two files.

**The arms.** Chains v1 and v2 of `ml/remaster_arm.py`, verbatim and
unchanged (v1: two EQ moves, `dynaudnorm`, `alimiter`, FLAC s16; v2: v1 after
adding decorrelated −72 dBFS stereo noise), applied to the first 40 files of
`fake/mp3_128` and of `fake/mp3_192`. Four new arms of 40. Controls, same
run: those same 40 + 40 direct transcodes.

**The engine.** 1.16.0 working tree, torch shimmed out (the CI configuration,
and the configuration of the depth gate's own bench), `--sample-duration 30`,
`--workers 2`.

| # | prediction | bound |
|---|---|---|
| **R1** | the direct controls are signalled — the contrast | ≥ 45 % of 40 on each bitrate |
| **R2** | chain v1 (digital only: EQ, level rides, limiter) keeps the depth gate's reach | v1 signalled ≥ direct − 10 points on each bitrate, and the depth reason ("digital silence") on ≥ half of the v1 files that are signalled |
| **R3** | chain v2 (an analogue-style noise floor) defeats it: the band above the edge is no longer silence | depth reason on ≤ 10 % of v2 files, and v2 signalled ≤ half of the direct rate, on each bitrate |
| **R4** | no bitrate signals more under v2 than under v1 | — |

What each failure would mean. R2 failing: a purely digital remaster is NOT
generally read, and the two Hein files were read by luck of their level; the
CHANGELOG claim for 1.13.16 would need a caveat. R3 failing LOW (the depth
reason survives the noise): the bar is more robust than its derivation
suggests, and the 320-cell abstention becomes the next question. R3 holding
is the expected, uncomfortable result: a store file that went through a
console is out of reach of every instrument this engine has, as the wild 53
already said at 320 kbps.

No repair follows from either experiment in this document. Results are
appended below, after the runs, in a section dated after the fact.

---

## RESULTS — appended 2026-09-21 after the runs

Engine 1.16.0 (`326cab7` tree), arms built by `fd-reach/build.py` from the
registered recipes, scored by `fd-reach/bench.cmd`, summarised by
`fd-reach/summarize.py`. All eight runs exit 0, 40/40 and 80/80 files read.

### V — Vorbis q10

| arm | files | signalled | convicted |
|---|---|---|---|
| vorbis_q8 (control, first 40) | 40 | 31 — **78 %** | 24 — 60 % |
| **vorbis_q10** | 80 | 6 — **8 %** | 1 — 1 % |

| # | prediction | bound | result |
|---|---|---|---|
| V1 | q8 control signalled | ≥ 60 % | **78 % — held** |
| V2 | q10 signalled | ≤ 25 % | **8 % — held** |
| V3 | q10 convicted | ≤ 5 % | **1 of 80 — held** |
| V4 | q10 signalled files whose only family is `cnn` | ≥ 80 % | **3 of 6 — FAILED**, and the failure is the finding |

The six, read against the verdict their genuine source gets from the same
rules (depth gate bench, `after2_auth_30`):

| file | as q10 | as genuine | what fired |
|---|---|---|---|
| Bag-o-wire | WARNING 31 | AUTHENTIC 0 | `cnn` alone, p = 0.98 |
| Keletigui | WARNING 31 | AUTHENTIC 0 | `cnn` alone, p = 1.00 |
| Vanilla Fudge | WARNING 31 | AUTHENTIC 0 | `cnn` alone, p = 0.98 |
| **Mondkopf** | **FAKE_CERTAIN 55** | AUTHENTIC 5 | the depth gate: edge at 19,000 Hz in both, but "the band above 19000 Hz sits at −61 dB" only after q10, plus the stereo witness |
| **Alpha Blondy** | WARNING 50 | AUTHENTIC 0 | Rule 1's near-Nyquist residual floor: same 20,500 Hz edge in both, the floor above it falls under the bar only after q10, plus the stereo witness |
| The Mebusas | WARNING 52 | **WARNING 52** | inherited: the genuine source reads the same verdict, same score. Not a q10 detection |

So the codec accounts for 5 of 80 (6 %), not 6. And two of the five are read
by no CNN at all: **Vorbis at q10 has no low-pass of its own, but it does not
encode what is not there — where the source has its own edge, q10 turns the
noise above that edge into silence, and both depth instruments read that.**
The mechanism the depth gate was built on for one species (a store file with
a codec ceiling) reads a second one it was never pointed at. It is a narrow
door: it needs a source with an edge below Nyquist, which most full-band
masters do not have.

What the number means for the blind q10 set offered by the other side: this
engine goes in expecting single digits, and says so beforehand.

Caveat on the genuine column: it comes from the 1.13.16 bench (torch shimmed
out); 1.13.17 → 1.16.0 changed texts, progress events and the quality stage's
file reads, each with zero verdicts moved on its own bench. The Rule 12
column of the three `cnn` files has no genuine counterpart in that run; the
published deep-mode cost on genuine files stands at its registered figure.

### R — the re-mastered chain below the 320 cell

| arm (40 files each) | signalled | convicted | depth reason | depth among signalled |
|---|---|---|---|---|
| mp3_128 direct | 22 — 55 % | 14 | 14 | 14 / 22 |
| mp3_128 chain v1 (digital) | 19 — 48 % | 10 | 13 | 13 / 19 |
| mp3_128 chain v2 (+ noise floor) | **1 — 2 %** | 0 | **0** | 0 / 1 |
| mp3_192 direct | 21 — 52 % | 18 | 17 | 16 / 21 |
| mp3_192 chain v1 (digital) | 27 — **68 %** | 23 | 17 | 17 / 27 |
| mp3_192 chain v2 (+ noise floor) | **5 — 12 %** | 0 | **0** | 0 / 5 |

| # | prediction | bound | result |
|---|---|---|---|
| R1 | direct controls signalled | ≥ 45 % each | **55 % and 52 % — held** |
| R2 | chain v1 keeps the reach; depth reason on ≥ half of v1's signalled | ≥ direct − 10 pts | **48 vs 55 (−7) and 68 vs 52 (+16); 13/19 and 17/27 — held** |
| R3 | chain v2 defeats it | depth on ≤ 10 % of files; signalled ≤ half of direct | **0 of 40 twice; 2 % and 12 % — held** |
| R4 | v2 never above v1 | — | **held** |

Read plainly. A purely digital remaster — EQ, level rides, a limiter, a
16-bit requantisation — does not hide a low-bitrate source from this engine:
the depth gate carries two thirds of what is signalled, and at 192 kbps the
chain even raises the rate (the level rides lift quiet programme, so the
relative floor reads deeper; the limitation registered on 2026-09-15 —
"relative to the programme level" — working in the other direction). The two
Beatport files were not luck: they are this species.

And one ingredient ends it. A decorrelated noise floor at −72 dBFS, which any
console, tape or vinyl stage adds for free, takes the depth reason from 13
and 17 files to **zero** and the signalled rate to 2 % and 12 %, with no
conviction left on either bitrate. The wild 53 said this at 320 kbps in
August; it holds at 128 and 192, and the depth gate changes nothing about it.
**A lossy source that went through an analogue-style stage is out of reach of
every instrument this engine has.** That is a statement about the engine, on
a simulated chain; whether real store files of that kind exist in number is a
question for a corpus nobody has yet.

