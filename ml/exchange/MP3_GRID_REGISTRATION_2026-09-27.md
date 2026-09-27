# Rule 16, the MP3 granule grid — registered 2026-09-27, before the engine runs

Written and committed **before the before- and after-passes run**. The
instrument was built and measured offline on the statistic alone
(`fd-mp3grid/`, then `src/.../mp3_grid.py`, checked identical to the probe to
the fourth decimal on three files); no verdict has been computed with it.

---

## Why

The halves of full-length transcodes disagree 13 times in 44, and the three
repairs left after 1.18.0 were refused on their derivation
(`POSITION_REMAINDER_REFUSED_2026-09-26.md`): on everything this engine reads,
some MP3s and some genuine files are one reading apart. What was missing is a
second instrument, independent of the cutoff. For MP3 the project's own record
named it and did not build it (`ml/README.md`, "MP3 geometry: a negative
result"): a plain MDCT at MP3's period reads MP3 at the null, "the real MPEG-1
Layer III analysis filterbank remains the only way in".

## The instrument (`analysis/new_scoring/mp3_grid.py`)

The encoder's own analysis bank, applied to the decoded audio: 32-band
polyphase with the ISO/IEC 11172-3 window, then per subband an 18-point MDCT
over 36 samples (sine window), the encoder's frequency inversion of odd
subbands and its alias-reduction butterflies — 576 lines per granule. At each
of the 576 granule alignments, the share of lines 40 dB under their local
median (Rule 13's hole, `REF_SIZE` 33), over 48 granules spread through the
central 30 s. Statistic: the best alignment's hole share over the median across
alignments. A genuine recording has no preferred alignment; an MP3 decode has
one, where the encoder's zero-quantised lines come back as holes.

Prior art, public since 2000: Herre & Schug, "Analysis of Decompressed Audio —
The Inverse Decoder" (AES 109); Moehrs, Herre & Geiger (AES 112, 2002). This
derivation uses those papers and the ISO window, and nothing received from the
other side of the exchange.

**Control before any corpus**: one genuine source, LAME 128 and 320 through
ffmpeg — peak ratio 5.47 and 1.53 at alignment 528 (the decoder delay), the
genuine 1.18 at a random alignment. A libsndfile MP3 round trip of synthetic
audio: 14.6; the same audio uncompressed: 1.26.

## Derivation

Audit corpus, 80 genuine and 80 per arm, split by source into a development
half (even) and a held-out half (odd); depths 20/30/40 dB tried on the
development half only.

| held-out half, 40 dB | AUC vs genuine |
|---|---|
| mp3_128 | 1.00 |
| mp3_192 | 0.99 |
| mp3_320 | 0.96 |
| mp3_V0 | 0.98 |
| aac_ff256 | 0.38 (chance: it reads MP3 only) |
| vorbis_q8 | 0.44 |

All 79 of the 80 arm files per MP3 arm peak at the same alignment (276): the
grid is real, and the encoder's.

Then 291 further labelled genuine files (wild, v2 genuine, attested CDs,
full-length, received, the 24 genuine halves): median 1.26, p95 1.32, and every
file under **1.50** except three. **`GRID_BAR = 1.6`.** At that bar: the 28 +
28 full-length LAME 128 / 256 transcodes of the attested CDs 56 of 56, the 64
transcode halves 56 of 64, audit mp3_320 76 of 80 (at 1.5), aac and vorbis 0.

**Four genuine-labelled files read a grid as strong as a real MP3**, named here
before any verdict is computed:

| file | set | peak ratio (40 dB) | what else this engine already reads on it |
|---|---|---|---|
| Mondkopf, *Summer afternoon on the Caribbean sea* | audit authentic | 8.09 | a hard 19,000 Hz wall (DEPTH_GATE, REACH registrations) |
| pachy 2025-07-31 d1t01 | wild | 8.57 | an 18,750 Hz wall at 566 kbps, the size of a LAME 192 decode (POSITION_REMAINDER document) |
| pachy 2025-07-31 d1t02 | wild | 8.33 | — |
| v2 `fd-exchange-v2-2026-08-0386` | v2 genuine | 5.39 | — (the v2 key was found wrong 3 times in 59 in August) |

They may be MP3-sourced masters in genuine clothing, as three earlier files of
these corpora turned out to be; this document does not decide it, and every
count below keeps them genuine.

## The rule (`rules/mp3_grid.py`)

**A witness with zero points**, family `mp3grid`, like Rules 14 and 15: it can
complete a corroboration for a file already at `CONVICTION_MIN_SCORE`, and can
move no file toward that bar. **It runs only where it can change a verdict**:
score ≥ `CONVICTION_MIN_SCORE` with fewer than `CONVICTION_MIN_FAMILIES`
families, after every other rule. Everywhere else it is not computed.

## Criteria, registered before the passes run

Before = 1.18.0 (worktree at `v1.18.0`); after = 1.18.0 plus Rule 16 only. Torch
live, default mode, `--sample-duration 30`, `--workers 2`.

Corpora: audit authentic, v2 genuine, wild, attested CDs, full-length genuine,
received folder; the 88 halves; the 84 attested-CD transcodes; `long_mp3`; the
8 full-length transcodes; the first 40 of audit `mp3_128`, `mp3_192`,
`mp3_320`, `mp3_V0`, `aac_ff256`, `vorbis_q8`; and the 1,726-track library
sample (unlabelled). By construction Rule 16 can only move a file that is
`SUSPICIOUS` on one family in the before-pass; the after-pass is run on every
labelled corpus in full and, for the library, on the files the before-pass left
`SUSPICIOUS` on one family (every other library file cannot move).

| # | criterion | bound |
|---|---|---|
| **A1** | labelled genuine files newly convicted, the four named above included | **0** |
| **A2** | every mover goes `SUSPICIOUS` → `FAKE_CERTAIN` by gaining `mp3grid` and nothing else | all |
| **A3** | library movers | listed by name with their grid reading; shipping decided on that list, in writing |
| **N1** | movers on `aac_ff256` and `vorbis_q8` | 0 |
| **P1** | halves in disagreement, of 44 | after ≤ before |
| **P2** | convictions on the MP3 arms + full-length MP3 transcodes | after > before |
| **E1** | transcodes losing a conviction or a signal | 0 |

A1, A2 or E1 breached: does not ship in this form.

Results are appended below, after the runs, in a section dated after the fact.

---

## RESULTS — appended 2026-09-27 after the runs

Before = 1.18.0 (worktree at `v1.18.0`, `fda788c`); after = 1.18.0 plus the
eight Rule 16 files and nothing else (`fd-mp3grid/after_src`, checked with
`git diff --no-index --ignore-cr-at-eol`, refreshed after `black` so the
measured code is the shipped code). Runner `fd-mp3grid/bench_run.py`
(`FLACAnalyzer.analyze_file`, the engine the CLI wraps), torch live, default
mode, 30 s, 2 workers. Before-pass on 2,519 files; after-pass on the 793
labelled ones (one worker crashed at 779 and the run was resumed; 793 of 793
read). Four errors in the before-pass, none from the engine: the two wild
`bdmagoo` files that no reader opens, and two library entries (one path
corrupted by a byte-order mark in the list file, one decode failure).

**The population the rule can reach.** In the whole before-pass, **5 files**
sit at `CONVICTION_MIN_SCORE` or above on a single family: two audit arm files,
one half, one `long_mp3` track and one Beatport AIFF. **0 of the 1,726 library
tracks** — so by construction no library file can move, and none was re-run.

| # | criterion | bound | result |
|---|---|---|---|
| A1 | labelled genuine newly convicted, the four named files included | 0 | **0 — held** (none of the four reaches the bar on one family, so the rule never runs on them) |
| A2 | every mover `SUSPICIOUS` → `FAKE_CERTAIN` by `mp3grid` alone | all | **4 of 4 — held**: Eve 192 (half A), Wolf Drawn LAME 128 (full length), Kat Onoma mp3_128, Jon Hassell mp3_192; scores unchanged |
| A3 | library movers | listed | **none possible** (0 candidates) |
| N1 | movers on aac_ff256 / vorbis_q8 | 0 | **0 — held** |
| P1 | halves in disagreement | after ≤ before | **13 → 12 — held** (Eve 192: both halves now convicted) |
| P2 | convictions on MP3 arms + full-length MP3 | after > before | **held**: arms 65 → 67, `long_mp3` 17 → 18, halves 34 → 35 |
| E1 | transcodes losing a conviction or a signal | 0 | **0 — held** |

The fifth candidate, the Beatport AIFF of DJ Hein (SUSPICIOUS 68 on the depth
gate), reads no MP3 grid — consistent with the other side's finding that its
codec is neither MP3 nor WMA.

**Ships in 1.19.0**, said for what it is: a second instrument, independent of
the cutoff, that reads MP3 at AUC 0.96-1.00 and nothing else; wired as a
zero-point witness it is safe by construction and, on these corpora, it
decides four files. Most of what still separates the halves is points, not
families, and a witness does not give points. Giving it points would put the
four genuine-labelled files that read a grid — Mondkopf, pachy ×2, v2 0386 —
at WARNING or above, and that is exactly the decision this project does not
take on a detector's word: their provenance has to be settled first.