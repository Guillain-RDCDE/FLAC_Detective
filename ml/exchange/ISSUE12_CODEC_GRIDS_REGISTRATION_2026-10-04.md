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
