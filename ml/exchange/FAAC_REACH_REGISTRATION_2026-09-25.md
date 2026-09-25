# A reach measurement: AAC through FAAC — registered 2026-09-25, before any file is scored

Written and committed **before the arms are scored**, per the convention. No
engine change is attached to this document: it measures the shipped engine
(1.16.0, worktree at tag `v1.16.0`) on an encoder it has never seen, so the
numbers exist before anyone else's do.

---

## Why now

Every AAC arm this project has built comes from two encoders: ffmpeg's native
`aac` (`aac_ff128/256/320`) and MediaFoundation (`aacmf_256`). The CNN, the
MDCT statistic (Rule 13) and the depth instruments were all calibrated or
measured on those two. An AAC file in the wild is as likely to come from
FAAC, Nero, Apple or fdk, and a detector that has learned an encoder rather
than a codec reads the next one as clean. The other side of the exchange
reported on 2026-09-19 that an AAC encoded by FAAC is a known blind spot of
theirs; we have never looked at ours.

## The arms

The 80 sources of `audit_corpus/authentic`, each decoded to 16-bit PCM WAV at
its own rate, encoded by **FAAC 1.40** (`faac.exe` from the encoder collection
received for the exchange, SHA-256 `93ddae1f…74d1f`, verified against that
collection's `SHA256SUMS.txt` before the first run and re-checked by the build
script before every run), then decoded back to FLAC s16 at the source rate by
ffmpeg, metadata stripped. Three average bitrates, FAAC's own ABR mode:

* `faac_128` — `-b 128`
* `faac_192` — `-b 192`
* `faac_256` — `-b 256`

Control, same run: the first 40 files of the existing `fake/aac_ff128` arm (the
ffmpeg encoder at the lowest AAC rate this project has).

Builder: `fd-r8/build.py` (off Dropbox). The FAAC path is not
`build_audit_corpus.transcode` because FAAC is not an ffmpeg encoder; the
decode leg reproduces that function's (source rate forced back, FLAC s16,
`-map_metadata -1`).

## The engine

1.16.0 at tag `v1.16.0` (detached worktree `C:\Users\loutr\fd-v1160`),
`--deep`, torch 2.14.0 live (Rule 12 runs), `--sample-duration 30`,
`--workers 2`. `--deep` because at 192 and 256 kbps an AAC file leaves the
heuristics silent and only the CNN and Rule 13 can speak — the configuration
of the Vorbis q10 reach measurement of 2026-09-21.

## Predictions

| # | prediction | bound |
|---|---|---|
| **F1** | the ffmpeg control is signalled (`WARNING`+) — the contrast; without it the arms prove nothing | ≥ 50 % of 40 |
| **F2** | `faac_128` is read about as well as the ffmpeg encoder at the same rate: a low-pass is a low-pass | signalled ≥ F1's rate − 20 points |
| **F3** | `faac_256` is mostly missed | signalled ≤ 30 % of 80 |
| **F4** | the rate orders the reach | signalled(128) ≥ signalled(192) ≥ signalled(256) |
| **F5** | among signalled `faac_192` + `faac_256` files, the CNN or Rule 13 carries the evidence rather than the cutoff rules | ≥ 50 % carry `cnn` or `mdct` |
| **F6** | no file of any arm leaves as `ERROR` or `NOT_ASSESSED` | 0 |

Basis: FAAC's ABR mode applies a bandwidth that falls with the bitrate, as the
ffmpeg encoder does, so the cutoff rules should see the 128 kbps arm; above
that the question is whether the learned and frame-grid instruments generalise
across encoders. F5 is the prediction that matters most, and the one most
likely to fail: Rule 13 reads the frame grid of a transform codec, and the CNN
was trained on encoders that are not FAAC.

What a failure would mean. F2 failing LOW: the cutoff rules key on ffmpeg's
particular low-pass, not on a low-pass — an encoder-shaped hole below 192
kbps. F5 failing: at high rates FAAC is read, if at all, by the spectral
family, and the two instruments meant for high-rate AAC have learned ffmpeg.

No repair follows from this document. Results are appended below, after the
runs, in a section dated after the fact.

---

## RESULTS — appended 2026-09-25 after the runs

Engine 1.16.0 at tag `v1.16.0` (worktree `fd-v1160`, `b17b9f8`, import path
checked to resolve there), `--deep`, torch live. Arms built by `fd-r8/build.py`
(FAAC binary re-hashed before the run, 240/240 encodes), scored by
`fd-r8/bench_faac.cmd`, summarised by `fd-r8/summ_faac.py`. Four runs, exit 0,
every file read.

| arm | files | signalled | convicted | ERROR / NOT_ASSESSED | median cutoff |
|---|---|---|---|---|---|
| `aac_ff128`, first 40 (control) | 40 | 35 — **88 %** | 19 — 48 % | 0 | 17,250 Hz |
| `faac_128` | 80 | 53 — **66 %** | 23 — 29 % | 0 | 19,500 Hz |
| `faac_192` | 80 | 48 — **60 %** | 25 — 31 % | 0 | 19,500 Hz |
| `faac_256` | 80 | 43 — **54 %** | 22 — 28 % | 0 | 19,500 Hz |

| # | prediction | bound | result |
|---|---|---|---|
| F1 | control signalled | ≥ 50 % | **88 % — held** |
| F2 | `faac_128` ≥ control − 20 points | ≥ 68 % | **66 % — FAILED by 2 points** |
| F3 | `faac_256` mostly missed | ≤ 30 % | **54 % — FAILED**, in the good direction, and reported as a failed prediction all the same |
| F4 | rate orders the reach | 128 ≥ 192 ≥ 256 | **66 ≥ 60 ≥ 54 — held** |
| F5 | `cnn` or `mdct` among signalled 192 + 256 | ≥ 50 % | **59 of 91, 65 % — held**, and all of it is `cnn`: see below |
| F6 | no ERROR / NOT_ASSESSED | 0 | **0 — held** |

Read plainly.

**FAAC does not low-pass by bitrate.** Its ABR mode puts the edge at
19,500 Hz at 128, 192 and 256 kbps alike (62-64 of 80 files in that cell on
every arm). The basis written for F2 and F3 — "a bandwidth that falls with the
bitrate, as the ffmpeg encoder does" — was wrong. That is why F3 failed high:
the 256 kbps arm carries the same 19.5 kHz edge as the 128 kbps arm, and the
spectral family reads it on 20 of the 43 signalled 256 kbps files
(`spectral|stereo|temporal`). And it is why F2 failed low: at 128 kbps the
ffmpeg encoder's 17 kHz wall is easier to read than FAAC's 19.5 kHz one.

**Rule 13 is blind to FAAC.** It ran on 234 of the 240 FAAC files and scored
on **none**; on the ffmpeg control it ran on 4 (the other 36 sit under its
cutoff gate) and scored on all 4. Rule 13 tests two window hypotheses, the KBD
window of the ffmpeg encoder and the Vorbis window; neither gives a reading on
FAAC's output. Why — window shape, quantiser, or something else — is not
measured here. The instrument built as "the only rule that reads
high-bitrate AAC" reads one AAC encoder. Recorded; no repair in this document.

**The CNN carries the high rates.** Every `cnn`-or-`mdct` file in F5 is `cnn`.
At 256 kbps half the signalled files rest on the spectral family instead.

What this means for the other side's FAAC blind spot: this engine does not
share it at the rates measured — 54-66 % signalled, 28-31 % convicted — but it
reaches FAAC through the edge and the CNN, not through the frame grid that
reads ffmpeg's AAC.