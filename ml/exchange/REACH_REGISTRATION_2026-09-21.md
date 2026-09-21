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
