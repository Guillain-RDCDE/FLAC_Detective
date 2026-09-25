# The stereo witness reads the whole file — registered 2026-09-25, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. The derivation below is an offline probe of the statistic alone;
no verdict has been computed on either tree.

---

## The defect

Two halves of the same transcode disagreed on 4 of 12 tracks on 2026-09-03
(`ml/read_position_halves.csv`), and the fixed-window offset grid of
2026-09-04 (`ml/read_offset_fixed_window.py`) found the engine at its worst
at offset 0, with "`stereo` absent at offset 0" named among the causes. That
was recorded as a question of *which* audio gets read, and left there.

The mechanism is in `stereo_image._spectra`: it takes `MAX_FRAMES` (200)
**contiguous frames from sample 0** — the first ~4.7 s at 44.1 kHz — of
whatever it is handed, and the engine hands Rule 15 the whole file. On a full
track the stereo witness reads the intro. Every other instrument samples
several places (the spectral cutoff three 30 s windows, the CNN three 10 s
windows, Rule 13 frames spread over the excerpt) or everything (Rule 14).

Rule 15 scores no points; it is a witness, and a witness is what decides
between `SUSPICIOUS` and `FAKE_CERTAIN` (`CONVICTION_MIN_FAMILIES = 2`) and
whether a file may short-circuit. So an intro can decide a conviction.

## The repair

The same 200 frames, **spread evenly over the signal**: stride
`max(HOP, (usable // MAX_FRAMES) // HOP * HOP)`, the rounding Rule 13 uses.
Below `MAX_FRAMES` hops the stride is `HOP` and the frames are exactly the
1.16.0 frames. Nothing else changes: same statistic, same `RUN_BAR = 2.0`,
same gates.

## Derivation (`fd-r15/probe_r15.py`, the statistic alone, whole files as the engine hands them)

| population | files measurable | fires at 2.0, start (1.16.0) | fires, spread | p95 start | p95 spread |
|---|---|---|---|---|---|
| audit authentic | 74 | 8.1 % | 9.5 % | 2.71 | 2.87 |
| wild genuine (the purged 146) | 132 | 9.1 % | **3.8 %** | 3.03 | 1.46 |
| **all genuine** | 206 | **8.7 %** | **5.8 %** | 3.03 | 2.38 |
| 12 full-length genuine | 12 | 0 % | 0 % | 1.65 | 1.00 |
| 8 full-length transcodes (`TR320_*`, `TRVORB_*`) | 8 | 12.5 % | **37.5 %** | | |
| 24 full-length LAME 128/192 | 24 | 100 % | 100 % | | |
| opus_256 / vorbis_q8 / mp3_320 | 74 / 77 / 74 | 94.6 / 93.5 / 94.6 % | 94.6 / 93.5 / 95.9 % | | |
| mp3_V0 / aacmf_256 / aac_ff320 | 74 / 74 / 76 | 85.1 / 82.4 / 19.7 % | 86.5 / 86.5 / 18.4 % | | |

Read plainly: on genuine material the spread witness speaks less (8.7 % →
5.8 %), on the 60 s arms it speaks as much, and on full-length transcodes —
the population the defect was about — it speaks three times as often.

**A finding that is not repaired here.** `RUN_BAR = 2.0` was last re-verified
on 2026-08-21 (`ml/recal_clean228.py`) at a clean-genuine p95 of 1.94. That
calibration read the first 30 s of each file, and `_restore` normalises by the
peak of what it is handed; the engine hands it the whole file, whose peak is
higher. On whole files, as the engine actually reads them, the genuine p95 is
**3.03** with the shipped sampling and **2.38** spread. The bar has been
sitting under the p95 it was meant to sit above, on full-length files, since
August. The repair moves the statistic toward its calibration and does not
close the gap; re-deriving the bar is a separate registration, because a bar
fitted to one aggregate is meaningless against another (the rule's own
docstring). Stated here so it is not discovered later.

## Criteria, registered before the passes run

Before = 1.16.0 (worktree `fd-v1160` at `b17b9f8`); after = the same tree with
`stereo_image._spectra` replaced and nothing else (`fd-r15/after_src`). Same
files, same order, `--sample-duration 30`, `--workers 2`, **torch live**,
default mode (no `--deep`): the CNN is the other family the halves flipped on,
and the default mode is what a user runs.

Corpora: `audit_corpus/authentic` (whole folder), the wild genuine 146, v2
genuine (59), the 12 full-length genuine, the received files (whole folder);
the first 40 of `fake/opus_256`, `vorbis_q8`, `mp3_320`, `mp3_V0`,
`aacmf_256`, `aac_ff320`; and **the halves**: the 12 full-length genuine, the 8
full-length transcodes and the 24 full-length LAME tracks each cut into first
and second half (ffmpeg, FLAC), 88 files.

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`), any corpus, halves included | **0** |
| **A2** | every mover changes through the `stereo` family (a witness gained or lost, or what that did to a short-circuit) — any other mover withdraws this document | all |
| **P1** | tracks whose two halves disagree on the verdict, of the 44 | after ≤ before |
| **P2** | convictions on the 32 full-length transcodes (whole files) | after ≥ before |
| **P3** | convictions on the 240 arm files | after ≥ before − 3 |
| **E1** | transcodes losing a conviction, all corpora | ≤ 3, each listed |

A1 or A2 breached: does not ship. P1 missed: the repair is reported as not
reaching the position defect, and ships only if A1, A2, P2 and P3 hold.

Results are appended below, after the runs, in a section dated after the fact.
