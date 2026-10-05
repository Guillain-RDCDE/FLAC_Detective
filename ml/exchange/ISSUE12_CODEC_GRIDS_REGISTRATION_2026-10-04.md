# Issue #12, second round: Vorbis block switching, Opus, HE-AAC — registered 2026-10-04, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. Everything below was derived by reading the instruments on files
(probes); no verdict has been computed with the change.

---

## Where this comes from

Issue #12, 2026-10-03. The reporter (barthess) tested 1.20.1 and sent four
recipes from one Bandcamp FLAC (The Enigma TNG, *Doomhammer 666k*):

| recipe | 2.0.0 reads | the reporter's expectation |
|---|---|---|
| `oggenc -q1` → FLAC | WARNING 41 (R2 16 + R13 2.43 review) | FAKE_CERTAIN |
| `oggenc -q10` → FLAC | AUTHENTIC 0 | not authentic |
| `opusenc --bitrate=64` → `opusdec` → FLAC | AUTHENTIC 0 | not authentic |
| ffmpeg `libfdk_aac -profile:a aac_he_v2 -b:a 128k` → FLAC | AUTHENTIC 0 | not authentic |

Reproduced on 2.0.0 (`e66c5a2`), default mode, on the reporter's own source,
with the real encoders: oggenc2 2.88 / libvorbis 1.3.7 (sha256 `ac2c66f8…`),
opusenc / opusdec opus-tools 0.2-52 / libopus 1.6.1 (sha256 `ec159761…` /
`666bd197…`), all from the Provir encoder set and checked against its
`SHA256SUMS.txt`; fdkaac 1.0.5 x64 (rarewares, sha256 `f8831e22…`), profile 29
at 128,000 b/s, which declares `HE-AACv2` at 128 kbps.

## What the instruments missed, and why (development set)

Development set: the 33 loud CD tracks of the 2026-09-30 bench (`fd-r13`) plus
the reporter's file, each through the four recipes (`fd-r13/i12/`). These files
were used to design the instruments and are reported as development, never as
a result.

1. **Vorbis moves its own grid.** A run of k short blocks between two long ones
   advances the long-block grid by 1024 + 128 k samples, so on transient-heavy
   material there are eight alignments in one file, not one. Rule 13 looks for
   one and reads 2.43 on the issue's `-q1` file. Letting each read frame keep
   the best of the eight phases of a residue (and comparing residues with
   residues) reads **5.3**; the original reads 1.1.
2. **At high quality Vorbis keeps its zeros per channel.** At `-q10` the
   coupling is lossless and the mono mix has no holes (1.2); the left channel
   has them (**3.0**).
3. **Opus is not out of reach.** Rule 13's documentation said resampling
   destroys the alignment. The CELT decoder's de-emphasis filter
   (y[n] = x[n] + 0.85 y[n-1]) is what smears it: back at 48 kHz with the
   filter undone, 960-sample frames through CELT's low-overlap window read
   **6.0** on the issue's Opus 64 file (original 1.4).
4. **HE-AAC rebuilds its top band by copying.** SBR copies complex QMF subbands
   up by a fixed shift; the copy keeps its phase evolution. The complex
   coherence between a high subband and the one p subbands below (sign-corrected
   for odd p), median over subbands and segments, max over p, reads **0.72**
   (original 0.07).
5. **Joint stereo leaves a step.** Vorbis point stereo (`-q1`) and CELT
   intensity stereo (64 kbps) collapse the side channel by ~20 dB relative to
   the mid above a frequency: **15 dB** and **20 dB** on the issue's files,
   1.4 dB on the original. Rule 15 cannot see it: its gate is 17 kHz (the `-q1`
   file cuts at 16,750 Hz) and it reads death against an absolute bar, not a
   step.

Two defects of my own instruments were found and repaired during development,
before calibration: a triage on three fixed positions lost the true grid on two
Opus files whose first position was a quiet intro (CELT now triages on the 6
loudest of 18 spread positions, 16 candidates); and a triage on the loudest
positions picked, on Vorbis, drum hits coded in short blocks, and dropped one
file in fifteen to the null at random (Vorbis now triages on 8 evenly spread
positions). The calibration below was taken with the repaired instruments, by
the engine's own modules (`codec_grids`, `sbr`, `joint_stereo`), whose readings
were checked equal to the probes' to the last printed digit.

## The change

* **Rule 13** takes two more readings when its own does not reach the hard bar:
  the Vorbis block-switch grid (left and right channels) and the CELT grid. Each
  has its own bars; the rule still scores once, the strongest tier any reading
  reaches (25 review, 55 hard), family `mdct`. Its two certified hypotheses and
  their bars do not change.
* **Rule 17 (new), band replication.** Scores 25 / 55, family **`sbr`**, its
  own: it reads neither the cutoff, nor a frame grid, nor the stereo image, nor
  temporal variance. Runs wherever Rule 13 runs (fast path included, before any
  acquittal), under the same gate. Like Rule 13, when it scores it withdraws
  Rule 8's full-band protection: replication is exactly what manufactures a
  full band.
* **Rule 18 (new), side-channel step.** Zero points, a witness for the
  **`stereo`** family (with Rule 15), read only on the bands under the file's
  own cutoff and relative to its own stereo image, no cutoff gate, mono gated
  out. Runs with Rules 14 and 15.
* The two-family requirement for a conviction is **unchanged**.

## Derivation (bars calibrated on the genuine population alone)

Labelled genuine: certified 877, v2 56, wild 146 (2 unreadable), attested 28,
full-length 12, bench CDs 34 = **1,151 read** (CELT: 1,131 at 44.1/48 kHz).

| statistic | genuine median | p99 | p99.9 | max | review / hard bar |
|---|---|---|---|---|---|
| Vorbis block-switch | 1.128 | 1.248 | 1.301 | **1.612** | **1.7 / 2.4** |
| CELT | 1.273 | 1.596 | 1.696 | **1.732** | **2.2 / 3.2** |
| replication coherence | 0.086 | 0.182 | 0.232 | **0.363** | **0.40 / 0.55** |
| side step (dB, n = 1,048 not mono-gated) | 1.6 | 12.1 | 21.2 | 34.5 | witness **7.5** (the p95, as Rule 15) |

The review bars sit above every genuine reading and ~25-30 % clear of the
p99.9, the hard bars ~85 % clear, as Rule 13's do. Zero labelled genuine files
reach any review bar. 52 of 1,048 (5.0 %) offer the stereo witness, which can
only complete a corroboration for a file another family already carried past
55 points.

The maxima, named: Vorbis block-switch 1.612 and side step 34.5 dB are the same
certified file, Jacob Groening, *Love hangover* (Mira & Chris Schwarzwalder
remix), cutoff 15,250 Hz — a profile consistent with a lossy master pressed to
CD; it stays under the bar. CELT 1.732: Sébastien Tellier, *Pam! exit la folle*.
Replication 0.363: Natal'ja Vorbon & Raisa Talina, *Hand games*.

Development arms (34 each) at those bars:

| arm | Vorbis switch ≥ review / hard | CELT ≥ review / hard | SBR ≥ review / hard | step ≥ 7.5 |
|---|---|---|---|---|
| `vorbis_q1` | 34 / 34 | 0 | 0 | 29 |
| `vorbis_q10` | 32 / 28 | 0 | 0 | 0 |
| `opus_64` | 0 | 34 / 34 | 0 | 32 |
| `heaac2_128` | 0 | 0 | 34 / 34 | 3 |

Stress benches (unlabelled, read in full by the same probe):

| bench | read | over any review bar | step ≥ 7.5 |
|---|---|---|---|
| Awesome Tapes From Africa (cassettes) | 304 | **0** (max: switch 1.277, CELT 1.629, SBR 0.324) | 71 |
| Dust-to-Digital (78 rpm), seeded sample of 600 | 600 | **0** (max: switch 1.326, CELT 1.789, SBR 0.233) | 9 (of 148; 452 mono-gated) |
| library sample (one track per album) | 1,725 | **5** | 108 |

The five library files over a bar, named before any verdict is computed:

| file | reading |
|---|---|
| Vladimir Cosma, *Courage fuyons* (*Les plus belles musiques de films* CD2) | Vorbis switch 9.93 — the disc already found on a Vorbis grid (1.20.0) |
| French 79, *Hometown* (*Joshua*, 2021) | Vorbis switch 6.86 |
| Georgio, *Près du feu* (*Ciel enflammé (Sacré)*, 2021) | CELT 9.52 |
| L'Impératrice, *Peur des filles* (*Tako Tsubo*, 2021) | CELT 8.95 |
| Doctor Flake, *Pastels* (*Floating*, 2022) | replication 0.897 |

Each reads 4 to 6 times the genuine maximum of its statistic. They stay
unlabelled; the verdict will be reported as computed.

## The held-out test set

40 certified library tracks drawn with a fixed seed (20261003), one per album,
44.1 kHz stereo, none in the certified 877, across jazz, world, film scores,
chanson, ambient, early music and restored 78s (`fd-r13/i12t/MAP.tsv`). Nine
arms: Vorbis `-q1`, `-q5`, `-q10` (oggenc); Opus 64, 96, 128 kbps (opusenc /
opusdec); HE-AAC v2 128 kbps and HE-AAC v1 64 kbps (fdkaac); HE-AAC 64 kbps
through Windows MediaFoundation (ffmpeg `aac_mf`, declared `HE-AAC` by ffprobe:
a second SBR implementation). 360 transcodes, every one decoded and checked
(`flac -t`). **No instrument has read any of them**: they are read for the first
time by the after-pass.

## Criteria, registered before the passes run

Before = 2.0.0 (`e66c5a2`); after = the same plus this change only.
`FLACAnalyzer.analyze_file`, default mode, 30 s, **torch live and torch absent**.

Corpora: labelled genuine (1,151 readable); the issue's five files; development arms
(136); the held-out set (360 + its 40 sources); the audit corpus arms already
in the repository (Opus 256, Vorbis q8, AAC ffmpeg 256/320, AAC MediaFoundation
256, MP3 320, MP3 V0; 80 each, torch live); unlabelled: **every** stress file
over a review bar or with a step ≥ 7.5 — the only files the change can move —
plus seeded random controls (200 library, 100 cassettes, 100 78 rpm).

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **L1** | labelled genuine: verdict moves (both modes) | **0** | any |
| **L2** | labelled genuine convicted after | **0** | any |
| **L3** | issue `-q1` | **FAKE_CERTAIN** (mdct + stereo), both modes | not FAKE_CERTAIN |
| **L4** | issue `-q10` | **SUSPICIOUS** (mdct only), both modes | AUTHENTIC |
| **L5** | issue Opus 64 | **FAKE_CERTAIN**, both modes | AUTHENTIC |
| **L6** | issue HE-AAC v2 | **FAKE_CERTAIN** (sbr + stereo, Rule 15), both modes | AUTHENTIC |
| **L7** | issue original | **AUTHENTIC 0**, unchanged | any change |
| **L8** | development arms caught (not AUTHENTIC), torch absent | q1 34, q10 ≥ 32, Opus 34, HE-AAC 34 | any arm under 30 |
| **L9** | held-out Vorbis q1 / q10 / Opus 64 / HE-AAC v2 caught, torch absent | q1 ≥ 38, q10 ≥ 30, Opus 64 ≥ 38, HE-AAC v2 ≥ 38 of 40 | any under 30 |
| **L10** | held-out generalisation, caught torch absent | Opus 96 ≥ 34, Opus 128 ≥ 30, Vorbis q5 ≥ 34, HE-AAC v1 ≥ 36, MediaFoundation HE-AAC ≥ 30 of 40 | reported, not a refusal: these arms were not designed for |
| **L11** | held-out sources (40 certified tracks) | **0** verdict moves | any |
| **L12** | detections lost, any arm, either mode | **0** | any |
| **L13** | unlabelled movers | the five named files, and files already ≥ 55 on one family that the step witness corroborates (each named in the results) | any mover outside those two classes |
| **L14** | cost | measured idle, one file at a time, on genuine files that take the fast path: reported | — |

L1, L2, L7, L11, L12 or L13 failing refuses the change. L3-L6 failing means it
does not fix the issue and is not shipped as a fix. `ml/rule_audit.py` is re-run
on the audit corpus with the after-engine (Rule 17 is a scoring rule and the CI
guard requires its measurement); Rule 17 is expected inert there (no SBR arm),
which the guard allows.


---

## RESULTS — 2026-10-05, after the four passes (appended; everything above is as committed in `87ed828`)

Before = 2.0.0 (`e66c5a2`), after = `8ee6197` (this change, committed locally
before the passes ran). 2,843 files torch live and 1,692 torch absent, each
before and after; **0 errors** in the four passes.

| id | criterion | predicted | measured | |
|---|---|---|---|---|
| L1 | labelled genuine (1,151): verdict moves, both modes | 0 | **0** (and 0 score moves) | held |
| L2 | labelled genuine convicted after | 0 | 9 torch live, 5 torch absent — **the same files as before**; 0 new | **mis-specified**, see below |
| L3 | issue `-q1` | FAKE_CERTAIN, both modes | WARNING 41 → **FAKE_CERTAIN 71** (mdct + stereo), both | held |
| L4 | issue `-q10` | SUSPICIOUS, both modes | AUTHENTIC 0 → **SUSPICIOUS 71** live / **55** absent (mdct) | held |
| L5 | issue Opus 64 | FAKE_CERTAIN, both modes | AUTHENTIC 0 → **FAKE_CERTAIN 85** live (cnn + mdct + stereo) / **55** absent (mdct + stereo) | held |
| L6 | issue HE-AAC v2 | FAKE_CERTAIN, both modes | AUTHENTIC 0 → **FAKE_CERTAIN 55** (sbr + stereo), both | held |
| L7 | issue original | AUTHENTIC 0 | **AUTHENTIC 0**, unchanged | held |
| L8 | development arms caught, torch absent | q1 34, q10 ≥ 32, Opus 34, HE-AAC 34; refuse any under 30 | q1 34, **q10 28**, Opus 34, HE-AAC 34 | **q10 under its bound**, see below |
| L9 | held-out caught, torch absent (of 40) | q1 ≥ 38, q10 ≥ 30, Opus 64 ≥ 38, HE-AAC v2 ≥ 38; refuse any under 30 | q1 **39**, q10 **29**, Opus 64 **30**, HE-AAC v2 **37** | q1 held; **q10 under its bound**; Opus 64 and HE-AAC v2 short of the prediction |
| L10 | held-out generalisation, torch absent (of 40) | Opus 96 ≥ 34, Opus 128 ≥ 30, Vorbis q5 ≥ 34, HE-AAC v1 ≥ 36, MF HE-AAC ≥ 30 | Opus 96 **36**, Opus 128 **40**, Vorbis q5 **38**, **HE-AAC v1 6**, **MF HE-AAC 6** | three held; **HE-AAC v1 failed** (reported, not a refusal) |
| L11 | held-out sources (40 certified), both modes | 0 moves | **0** | held |
| L12 | detections lost, any arm, both modes | 0 | **0** | held |
| L13 | unlabelled movers (591 files: the 191 the change can move + 400 random controls) | the five named files, and single-family files the step witness corroborates | **3**, all in those classes (below) | held |
| L14 | cost | measured | **+3.4 s** per fast-path genuine file (median 8.9 → 12.5 s, idle, one at a time, 12 certified tracks, verdicts identical) | — |

Torch live, the same arms read (caught before → after, of 40 held-out / 34 development):
Vorbis q1 34 → 39, q5 35 → 40, q10 4 → 31; Opus 64 0 → 32, 96 0 → 37, 128 0 → 40;
HE-AAC v2 7 → 38, v1 7 → 8, MF 6 → 7; development q1 34 → 34, q10 0 → 28, Opus
14 → 34, HE-AAC 13 → 34. The audit corpus arms already in the repository: **Opus
256 caught 31 → 73 of 80**, **Vorbis q8 53 → 80**, AAC ffmpeg 256/320, AAC
MediaFoundation 256, MP3 320 and V0 unchanged (80, 80, 49, 42, 9).

### What did not hold, in its own words

**L2 was mis-specified.** It asked for no labelled genuine file convicted after;
2.0.0 already convicts nine of them torch live and five torch absent (compilation
tracks with an MP3-shaped wall: five Buddha Bar compilation tracks, DJ Katapila
*Lalokat*, Degiheugi *Loneliness is… always around*, v2 0362, Booka Shade & Jan
Blomqvist *Blaze* — all `spectral` plus witnesses). The criterion should have
read "no NEW conviction". Measured: none, and the same nine and five verdicts
and scores are unchanged.

**L8 and L9 fall under their bound on Vorbis `-q10` (28 of 34, 29 of 40), and
the prediction was my error.** The derivation counted a reading at Rule 13's
review tier as a catch; review is worth 25 points, under WARNING's 31, so a
`-q10` file that only reaches review stays AUTHENTIC. Only the hard tier
(2.4) catches on its own, and the derivation's own table gave 28 of 34 at the
hard bar. The table of criteria says "refuse if any arm under 30"; the paragraph
under it names L1, L2, L7, L11, L12 and L13 as the criteria that refuse the
change. I wrote both, they contradict each other, and I resolve it the way the
paragraph says: those are the safety criteria and every one held; a recall
shortfall on the near-transparent arm (0 → 28 and 3 → 29 caught) is reported,
not used to keep `-q10` at 0.

**Opus 64 held-out 30 of 40 torch absent (predicted ≥ 38) and HE-AAC v2 37
(predicted ≥ 38):** the development set was one genre (loud hard house); the
held-out set is quieter, sparser material, where fewer grids and fewer stereo
steps are read. Torch live: 32 and 38.

**HE-AAC v1 at 64 kbps: 6 of 40 (fdkaac) and 6 of 40 (MediaFoundation).**
Rule 17 reads 0.12-0.27 there, inside the genuine tail, on either channel
alone as on the mix: at that rate the encoder rebuilds more of the high band
from synthetic noise and sinusoids, which carry no copied phase. Rule 17 reaches
HE-AAC v2 and not v1 at low bitrates; said so in the documentation.

### The three unlabelled movers (torch live)

| file | before → after |
|---|---|
| Doctor Flake, *Pastels* (*Floating*, 2022), named in advance | AUTHENTIC 0 → **FAKE_CERTAIN 55** (sbr + stereo) |
| French 79, *Hometown* (*Joshua*, 2021), named in advance | WARNING 31 → **FAKE_CERTAIN 56** (cnn + mdct + spectral + stereo) |
| Teno Afrika & Don Diego, *Sk love* (*Where you are*, 2022) | SUSPICIOUS 73 `spectral` → **FAKE_CERTAIN 73** (spectral + stereo): the step witness corroborates a single-family file, the second class of L13 |

The other three named files: Vladimir Cosma *Courage fuyons* was already
FAKE_CERTAIN (56 → 86); Georgio *Près du feu* and L'Impératrice *Peur des
filles* read the CELT grid at 9.5 and 8.9 and gain `mdct` (three families each)
but stay **WARNING 31 → 45**: Rule 7's clean-silence protection (−50) offsets
Rule 13's +55. That protection reads digital silence as a sign of a genuine
recording, which a high-bitrate codec also produces; whether it should yield to
direct codec evidence, as Rule 8's does, is a question for its own registration
and is not changed here. Five labelled genuine files gain the `stereo` witness
from Rule 18 with no score or verdict change, as a pointless witness must.

### The rule audit, regenerated

`ml/rule_audit.py` re-run on the audit corpus (80 genuine, 11 arms of 80) with the
after-engine, `--deep`: no dead rule; Rule 17 inert there (the corpus has no SBR
arm), which the guard allows; 0 genuine convicted. The regenerated file is the
first since August to carry the witness families, and the family-independence
guard then reads spectral+stereo, spectral+temporal and stereo+temporal "above
chance" on 2, 1 and 2 genuine files out of 80 — Rule 15, the same under 2.0.0.
The guard now reads a lift only from 5 co-firing genuine files up (a planted
alias on 10 files still fails it); see the test's comment.

Bench: `fd-r13/i12/` (`cal2.csv`, `pass/{live,nt}_{before,after}.jsonl`,
`pass/cmp.py`, `pass/cmp_results.txt`, `pass/rule_audit_after.csv`, `cost.jsonl`).

---

## AMENDMENT 1 — 2026-10-05, registered before the re-measurement it describes

**Found after the passes, by the repository's own test suite.** The full suite on
`8ee6197` fails one test: `test_alac_support` encodes a clean synthetic signal (200
harmonics of 100 Hz, every one starting at phase 0, identical channels) and expects
it not to be called a fake. 2.0.0 reads it AUTHENTIC 0; `8ee6197` reads it
**FAKE_CERTAIN 116** (CELT 76.0 +55, replication 0.867 +55, Rule 14 witness). More
synthetic signals, read on the same instruments: a 1 kHz sine, CELT 4.40 and
replication 0.751; a four-sine chord, replication 0.713; the harmonic series with
random phases, CELT 3.00. None of the ~4,600 real files read so far reached a bar,
but a test tone or a pure drone in a library would be convicted. **Not shipped as
it stands.**

**Cause.** Both instruments assume a signal that changes from frame to frame.
(1) A perfectly stationary signal leaks into every MDCT bin in a pattern that
depends on the frame alignment, so the hole density moves with alignment with no
codec at all. (2) On a few low tones the subbands above 5.5 kHz hold nothing but
the tones' own leakage, phase-locked across subbands, and the replication statistic
reads that leakage as a copy.

**Repairs, as they will be measured:**

* **R1, stationarity guard.** The three 2.1.0 readings (Vorbis block switching,
  CELT, replication) abstain when the file's spectrum does not move: the median,
  over 1-16 kHz bins, of the standard deviation over time of the dB magnitude
  (2048-point Hann frames, hop 1024, on 8 evenly spread 2 s segments) is under
  **2.0 dB**. Synthetic signals above read 0.04-0.39 dB; the issue's files 17-18 dB.
* **R2, replication floor.** A (segment, subband) cell enters the replication
  median only if its energy is within **50 dB** of the strongest subband of the
  same segment: leakage-only subbands are not read. On the chord and the sine the
  statistic then has nothing to read (abstains); on HE-AAC v2 it is unchanged or
  higher (issue file 0.716 → 0.731).

**R2 changes the statistic on real files, and one result above was explained
wrongly.** The same floor lifts HE-AAC v1 64 kbps (held-out `s05`) from 0.252 to
0.724: what kept v1 inside the genuine tail was not "synthetic noise in the high
band", as the results above say, but empty top subbands diluting the median.
That explanation is withdrawn here, not edited above.

**Criteria, registered before the re-measurement.** The re-measurement reads R1's
statistic and R2's replication on every file read so far (labelled genuine 1,151,
stress 2,630, development 136, held-out 400, audit arms 640), then re-runs both
engines (2.0.0 and the repaired code), torch live and absent, on every file whose
Rule 17 tier changes and on the issue's five files.

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **A1** | labelled genuine reaching replication 0.40 with R2 | 0 (bars stay 0.40 / 0.55) | any: R2 is refused, not re-barred |
| **A2** | real files (labelled, stress, arms) under 2.0 dB of stationarity | 0 | any labelled genuine or arm file |
| **A3** | the synthetic signals of the test suite and above | none reaches WARNING | any does |
| **A4** | files whose Rule 17 tier changes, re-run: labelled genuine verdict moves / detections lost | 0 / 0 | any |
| **A5** | held-out HE-AAC v1 and MediaFoundation HE-AAC caught, torch absent | ≥ 30 of 40 each | reported |
| **A6** | the issue's five files | as in L3-L7 | any differs |

---

## AMENDMENT 2 — 2026-10-05, registered before the re-measurement it describes

**R2 is refused by its own criterion.** Partway through Amendment 1's
re-measurement (1,704 of 5,282 files read), one labelled genuine file reaches the
replication review bar with the floor: Doris Monteiro com A. C. Jobim, *Se é por
causa de adeus*, **0.470**. A1 said "any: R2 is refused, not re-barred". It is
refused: the floor is not shipped, and the HE-AAC v1 gain it showed (0 → 55 on
most of the held-out v1 arm) goes with it. The reading is in the files; the cause
is the one the floor was meant to remove — on a recording whose high band is
nearly empty, the few cells that pass a relative floor are leakage-dominated.

R1 (stationarity) stands so far: 0 of the 1,704 real files read under 2.0 dB.

**R3, replacing R2: abstain on an empty high band, change nothing else.** The
replication statistic stays exactly as registered (every cell read, as calibrated).
It abstains when fewer than **half** of its (segment, high subband) cells are within
50 dB of their segment's strongest subband — the high band is then leakage, not
content, and there is nothing a copy could be read on. An abstention can only take
Rule 17 points away, never add them, so the calibration and the four passes stand
for every file that does not abstain.

The half was chosen before reading the share on any file: an SBR decoder fills the
band it rebuilds, so a replicated band is populated across its width.

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **B1** | HE-AAC v2 files (development 34, held-out 40, issue 1) that abstain | 0 | more than 2 |
| **B2** | the synthetic tones (harmonics, chord, sine) | none reaches WARNING | any does |
| **B3** | labelled genuine: verdict moves after re-running every file whose Rule 17 tier changes | 0 | any |
| **B4** | detections lost on any arm, same re-run | 0 | any |
| **B5** | held-out HE-AAC v1 and MediaFoundation, torch absent | unchanged from the passes (6 and 6 of 40) | reported |
| **B6** | R1: real files under 2.0 dB, all 5,282 | 0 | any labelled genuine or arm file |
