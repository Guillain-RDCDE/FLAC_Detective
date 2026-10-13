# Rule 17 above 48 kHz, and a low wall seen in one window — registered 2026-10-13, before the passes

Written and committed **before the before- and after-passes run**, per the
convention. The derivation below was measured on development readings
(instrument-level probes, no verdict compared between engines); the criteria
are fixed while the verdict movement is still unknown.

---

## Where this comes from

A purchased 24/192 solo-piano album (26 tracks, a label download; privately
held, not redistributed, not in this repository) was read by 2.4.1 on
2026-10-13: **26 of 26 flagged** — 22 SUSPICIOUS, 4 FAKE_CERTAIN. Rule 17 fired
on 26, Rule 2 read a "wall at 2,000 Hz" on one, Rule 13 a review-tier MDCT
structure on one, the stereo witness on two. Every reading but Rule 13's
disappears when the same audio is resampled to 48 kHz. The hi-res axis reads
all 26 `GENUINE_HIRES`; above 20 kHz they hold a flat converter floor near
−85 dB rising to −77 dB toward 60-96 kHz, and no music.

## What the code says, and what was measured to see it

**1. Rule 17 reads its geometry at the file's own rate.** `sbr.py` takes a
128-point STFT, 64 subbands of fs/128 Hz, the QMF geometry of an SBR decoder
— at the decoder's rate. At 192 kHz each subband is 1.5 kHz wide; on a quiet
recording the band from 5.5 kHz holds nothing but the leakage of the low
notes, which is phase-locked across subbands (the module already documents a
four-sine chord reading 0.713 for that reason). Same audio, mono, track 1:
**0.812 at 192 kHz, 0.412 at 96, 0.088 at 48, 0.074 at 44.1** (genuine
calibration: median 0.086, maximum 0.363; bars 0.40 / 0.55). Four tracks
resampled to 48 kHz and run through the whole engine read AUTHENTIC 0.

The library's 52 hi-res files (46 at 96 kHz, 6 at 192) never fired Rule 17 in
2.2.0: their high band carries content. The defect needs a hi-res rate **and**
a nearly empty high band.

**2. The low wall believes one window.** `analyze_spectrum` reads up to three
windows and keeps the **lowest** cutoff, so one window with a low-wall reading
decides the file. Track 13's middle window read a step of 16.2 dB at 2,000 Hz
(bar 15) with depth 37.7 (bar 30); 500 Hz past the "wall" the spectrum was
still 15.4 dB above its own floor and falling: a dark passage, not a stop.
The other two windows read nothing.

## The change

* **Rule 17, above 48 kHz:** the mono mix is brought down (polyphase) to
  44.1 kHz and to 48 kHz, the reading is taken at both, and the higher is kept.
  The copy an SBR decoder makes is a whole number of subbands only at the
  decoder's own output rate, 44.1 or 48 kHz in practice, which a resampled file
  does not declare. At 48 kHz and below nothing changes (same code path).
* **Low wall, several windows:** when more than one window is read, a low wall
  read in fewer than **2** of them is not believed, and that window is read
  again without the instrument. A one-window file (≤ 90 s) keeps its reading.
* Nothing else. Rule 13's reading on one track at 192 kHz (review tier, 25
  points, no signal) is **not** addressed here: one file, no population; it is
  reported in the results.

## Derivation (instrument level, before any verdict comparison)

**Rule 17 on HE-AAC decodes resampled upward.** The issue-12 test arms
(`fd-r13/i12t`, 40 sources each, decoded at the source rate) resampled with
soxr to 96 and 192 kHz, 24-bit (`D:/fd-r8b/build_heaac_up.py`), read by the new
`replication_coherence` (`D:/fd-hires/r17_up.py`):

| arm | native: hard / review | up 96: hard / review | up 192: hard / review |
|---|---|---|---|
| HE-AAC v2 128 (fdkaac) | 37 / 40 | 37 / 40 | 37 / 40 |
| HE-AAC v1 64 (fdkaac) | 1 / 1 | 1 / 1 | 1 / 1 |
| HE-AAC 64 (MediaFoundation) | 1 / 2 | 1 / 2 | 1 / 2 |

HE-AAC v1 is not read at its own rate either (known limit, issue-12
registration); the resampling loses nothing.

**Low wall, windows that read it** (`D:/fd-hires/lw_probe.py`, wrapping the
engine's own `low_wall_hz` inside `analyze_spectrum`; "k/n" = wall read in k of
the n windows that consulted the instrument):

| population | files | files with a wall | of which in 1 window of ≥ 2 |
|---|---|---|---|
| the piano album | 26 | 1 | **1** (track 13, 1/3) |
| labelled genuine (`fd-r13/i12/pass/genuine.txt`) | 1,151 | 1 | 1 (a Dust-to-Digital 78, 1/3) |
| library non-CD | 172 | 0 | 0 |
| Awesome Tapes From Africa | 304 | 0 | 0 |
| Dust-to-Digital, whole catalogue | 1,896 | 30 | **18** (17 × 1/3, 1 × 1/2) |
| full-length `lc_aac_32k` (45 attested tracks) | 45 | 44 | **2** (1/3) |
| full-length `lc_aac_48k` | 45 | 45 | 0 (45 × 3/3) |
| full-length `mp3_64k` | 45 | 45 | 0 |
| excerpt arms of 2026-09-25 (8 × 80, 30 s) | 640 | 220 | 0 (one window each) |

The full-length arms are new (`D:/fd-r8b/build_full.py`): the 2026-09-25 arms
are 30 s excerpts, read in one window, and cannot test this rule. Sources: the
28 September attested tracks and the 17 Tidy F.C. Annual 2002 First Half tracks
(owner-ripped, AccurateRip-verified). Cost on the codec side: 2 of 134 walls
(1.5 %). On the genuine side: 19 of 31 walls read on genuine recordings go.

## Corpora and passes

Before = `d2fa5be` (`main`, worktree `D:/fd-base`); after = the same plus this
change only. `FLACAnalyzer.analyze_file`, default mode, torch live,
`D:/fd-hires/probe.py`, temporary files on D:.

| corpus | files | why |
|---|---|---|
| labelled genuine | 1,151 | A-criteria; ≤ 48 kHz files without a one-window wall are unchanged by construction, and are run anyway |
| library non-CD | 172 | genuine hi-res, unlabelled |
| the piano album | 26 | the defect |
| the other hi-res of the same private set | 6 | 4 × 24/96 classical, 1 × 24/96 rock, 1 × 24/48 dance |
| Dust-to-Digital files with a wall | 30 | the stress files the low-wall change can move (listed from the census; every D2D file is 44.1 kHz) |
| Awesome Tapes From Africa at 96 kHz | 7 | the stress files the Rule 17 change can move (the other 297 are 44.1 kHz and read no wall) |
| upsampled-CD arms (2026-10-07) | 196 | lossless audio at 96/192 kHz with an empty band above 22 kHz |
| HE-AAC native + up 96 + up 192 | 360 | Rule 17 detection |
| excerpt low-rate arms | 640 | unchanged by construction |
| full-length low-rate arms + their sources | 180 | the low wall's detection |

## Criteria, registered before the passes run

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **A1** | labelled genuine 1,151: newly signalled (WARNING+) / newly convicted | **0 / 0** | any |
| **A2** | library non-CD 172 and the 6 other private hi-res: verdict moves | **0** | any newly signalled |
| **A3** | Dust-to-Digital 30 and ATFA 96 kHz 7: newly signalled / convicted | **0 / 0** | any |
| **A4** | upsampled-CD arms 196: signalled after vs before | after ≤ before | after > before |
| **H1** | the piano album: AUTHENTIC after | **26 / 26** (before: 0 / 26) | under 26 |
| **H2** | the piano album: Rule 17 at review tier or above, after | **0** | any |
| **H3** | track 13: low-wall reading after | **none** | a low wall |
| **D1** | HE-AAC native arms: verdict moves | **0** (same code path) | any |
| **D2** | HE-AAC up 96 / up 192: Rule 17 hard-tier readings after, per arm | **= native** (37, 1, 1) | below native − 1 in any arm |
| **D3** | HE-AAC up 96 / up 192: signalled after | ≥ native signalled − 2, per arm | below |
| **D4** | excerpt low-rate arms 640: verdict moves | **0** (one window each) | any |
| **D5** | full-length low-rate arms: transcodes losing a signal or a conviction | **0** | any |
| **D6** | full-length arms: low wall read after | `lc_aac_32k` ≥ 42 / 45, `lc_aac_48k` 45, `mp3_64k` 45 | below |
| **T1** | full test suite, ruff check, ruff format, mypy, Sphinx `-W` | green | any red |
| **C1** | cost | reported: Rule 17 resamples twice above 48 kHz; the low wall re-reads only a refused window | — |

A1-A4, H1, D1, D4, D5 or T1 failing refuses the change in this form. H2, H3,
D2, D3, D6 missed are reported with their reason. Results are appended below
after the passes, everything above left as committed.

---
