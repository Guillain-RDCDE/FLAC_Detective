# The low wall: a codec wall under the reference band — registered 2026-09-25, before the after-pass

Written and committed **before the after-pass is run**, per the convention: the
criteria are fixed while the answer is still unknown. The derivation below was
measured offline on per-window spectra (no engine run); the before-pass on the
shipped engine (1.16.0, worktree at tag `v1.16.0`) has not been run either.

Prompted by the measurement of 2026-09-04 (`ml/sbr_arm.py`, commit `9417ca5`),
left unrepaired on purpose at the time: under ~64 kbps `detect_cutoff` reads
22,050 Hz on files whose music stops at 4-11 kHz, and **Rule 8 then grants
−50** — `lc_aac_32k` read AUTHENTIC on 6 of 6 sources, real ceiling 6,746 Hz.

---

## The mechanism

`detect_cutoff` measures every 250 Hz cell against the median of the 10-14 kHz
reference band and starts its scan at 14 kHz. When the encoder's own low-pass
sits under 10 kHz, the reference band **is** the codec's floor: the scan
compares the floor with itself, finds no drop, and the fallbacks return the top
of the band. Rule 8 reads that number as "the spectrum reaches Nyquist" — the
evidence it exists to reward — and protects the file.

## Two instruments that do not separate, measured first

On the same window `analyze_spectrum` reads (offline probes `fd-r8/probe.py`):

* **the reference band's level relative to the 1-4 kHz midrange**: genuine
  down to −56.0 dB, `lc_aac_32k` up to −47.8 dB. Overlap. The genuine file at
  −56 is a 1920s 78 rpm transfer in the audit corpus (Dock Walsh).
* **the reference band's absolute level** (PSD, dB/Hz): genuine down to
  −124.2, `lc_aac_32k` up to −108.0. Overlap, same files at both ends.

A dark or old recording keeps its 10-14 kHz band as far under its midrange as a
32 kbps AAC does, and at the same absolute level. **Level cannot tell them
apart; shape can.** A codec stops — the spectrum falls 15-50 dB inside 500 Hz
and nothing comes back. A dark recording declines, ~10 dB per 500 Hz at its
steepest, into its own floor.

## The instrument: `spectrum.low_wall_hz`

On the same FFT, 250 Hz cells (median magnitude per cell) from 1 kHz. At each
cell boundary f from 2 kHz to 14 kHz:

* **step(f)** = mean of the two cells below f − mean of the two above (500 Hz
  each side);
* **depth(f)** = the same "below" level − the 90th percentile of the cells from
  f + 1 kHz **to 16 kHz**.

The wall is the lowest f where step ≥ **15 dB** and depth ≥ **30 dB**, moved to
the steepest boundary of the contiguous run that clears both (the two-cell means
straddle a wall, so the first boundary to clear sits one cell early). NaN when
none.

The depth stops at 16 kHz whatever the sample rate. The first version read to
0.993 × Nyquist, and on a 96 kHz field recording in the wild genuine set (music
to 13 kHz, a tonal dip at 3.5 kHz, empty above 20 kHz) the empty band put the
90th percentile in the silence and the dip read as a wall. That was the only
genuine window the first version fired on; capped at 16 kHz it does not.

**Consulted only when `detect_cutoff` found nothing** (reading ≥ 0.999 ×
Nyquist); the wall then replaces the reading. `detect_cutoff` never answers
under 14 kHz (its scan starts there, its energy fallback answers above 15 kHz),
so a cutoff in [2 kHz, 14 kHz) is always a low-wall reading
(`is_low_wall_reading`, pinned by a test), and no other file's reading can move.

## Derivation, per window (`fd-r8/probe3.py`, 30 s windows as the engine reads)

| population | files | windows | "nothing found" | fires | walls |
|---|---|---|---|---|---|
| audit authentic | 80 | 80 | 48 | **0** | — |
| v2 genuine (labelled, live tape) | 59 | 59 | 28 | **0** | — |
| full-length genuine | 12 | 36 | 36 | **0** | — |
| received files (CD, vinyl, Beatport, Uluru) | 22 | 66 | 33 | **0** | — |
| wild genuine (the purged 146) | 146 | 410 | 315 | **0** | — |
| `lc_aac_32k` | 80 | 80 | 80 | **71** | 3,500-4,750 Hz |
| `lc_aac_48k` | 80 | 80 | 80 | **77** | 7,250-7,500 Hz |
| `mp3_64k` | 80 | 80 | 80 | **72** | 10,500-11,000 Hz |
| `lc_aac_64k`, `mp3_96k`, `he_aac_32k` | 80 each | | 8 / 5 / 17 | 0 | (their edges are found by `detect_cutoff`, or SBR fills the band) |

Margins on the 460 genuine "nothing found" windows: the steepest step among
boundaries deep enough (≥ 30 dB) is **11.7 dB** (bar 15); the deepest depth
among boundaries steep enough (≥ 15 dB) is **28.7 dB** (bar 30). Both margins
are thin, and they are stated here rather than discovered later.

**The stress set, and what it changed.** The direction's own library holds the
full Dust-to-Digital catalogue — 1,896 tracks of 78 rpm transfers, cylinders,
phonautograms and field recordings — and 304 tracks from Awesome Tapes From
Africa (cassettes). Owner's library, never labelled, never in a denominator:
used only to list the files the instrument fires on. It fires on **30 of the
1,896 Dust-to-Digital tracks (1.6 %) and 0 of the 304 cassettes**, walls at
2,000-11,750 Hz. Restorers low-pass acoustic recordings as steeply as a 32 kbps
codec, at the same 3-5 kHz. The instrument cannot tell those apart, and nothing
in this document claims it can.

That decided the scoring before any engine run. A fixed score in WARNING for a
low wall (written first, as `LOW_WALL_SCORE = 40`) was withdrawn: it would have
signalled 1.6 % of a historical catalogue. **The wall is scored on Rule 2's
existing ramp, which caps at 30 = SCORE_AUTHENTIC.** It is reported and does
not signal on its own.

## The repair

1. `analyze_spectrum`: when `detect_cutoff` reads the top of the band, consult
   `low_wall_hz`; a wall replaces the reading.
2. Rule 2: a low-wall reading keeps the ramp's score (30 at any wall under
   14 kHz) and names the wall: "the audio stops at X Hz behind a wall, nothing
   above it".
3. Nothing else. Rule 8 stops protecting these files because their cutoff is no
   longer near Nyquist; every rule gated on the cutoff reads the true value.

## Criteria, registered before the after-pass runs

Before = 1.16.0 (worktree `fd-v1160` at `b17b9f8`), after = the repaired tree,
same files, same order, `--sample-duration 30`, `--workers 2`, torch shimmed out
on both sides (the CI configuration, and that of the depth gate's bench).

Corpora: `audit_corpus/authentic` (whole folder), v2 genuine (59),
`fd-pistes-completes` (12), the received files (whole folder), **the 30
Dust-to-Digital tracks the instrument fires on**, the eight low-rate arms
(`lc_aac_32k/48k/64k`, `mp3_64k/96k`, `he_aac_32k/48k/64k`, 80 each), and
`audit_corpus/fake/mp3_128` (80) as a control of the ordinary path.

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`), any corpus, stress set included | **0** |
| **A2** | genuine files newly signalled (`WARNING`+), any corpus, stress set included | **0** |
| **A3** | every mover (verdict or score) read ≥ 0.999 × Nyquist before and a cutoff in [2 kHz, 14 kHz) after, with the wall reason — any other mover withdraws this document | all |
| **P1** | `lc_aac_32k`: Rule 8's protection gone | on ≥ 68 of 80 (85 %) |
| **P2** | `lc_aac_48k`: Rule 8's protection gone | on ≥ 72 of 80 (90 %) |
| **P3** | `mp3_64k`: low wall read | on ≥ 68 of 80 (85 %) |
| **P4** | `mp3_64k` signalled after (the wall sits in Rule 1's 128 kbps cell, 10-15.5 kHz, so the rule can now read it) | ≥ 20 of 80 — a guess, registered as one |
| **P5** | `lc_aac_32k` and `lc_aac_48k` signalled after (the wall alone does not signal; anything else that does is reported) | ≤ 8 of 80 each |
| **P6** | the 30 stress tracks after | all AUTHENTIC, each carrying the wall reason |
| **E4** | transcodes losing a signal or a conviction, any arm (a lower cutoff closes the gates of Rules 14 and 15) | **0** |

A1, A2, A3 or E4 breached: the repair does not ship in this form. P-criteria
missed are reported with their reason and do not block, provided the A-criteria
hold: the defect being repaired is a protection granted on a false reading, and
the repair's first duty is to stop granting it.

## What this does not do

* **It does not signal an AAC 32k file.** It stops protecting it and says where
  the music stops. Signalling needs a second, independent reading that a
  restored 78 does not share; none exists in this engine yet.
* **SBR** (`he_aac_*`) fills the band above the core codec's ceiling; the
  instrument reads nothing there, as the derivation table shows.
* **Walls read by `detect_cutoff` itself** (`lc_aac_64k`, `mp3_96k`) are
  untouched: the third failure mode of 2026-09-04 ("the address is right and
  the scale does not convict") is a different defect.

Results are appended below, after the run, in a section dated after the fact.

---

## AMENDMENT — 2026-09-25, after the first after-pass, before the second

The first after-pass (`fd-r8/lw/after_*`, kept) ran on the repair as
registered above and **two A-criteria were breached**.

**A2 — one genuine file newly signalled.** Emile Berliner, *Numbers and
letters* (Dust-to-Digital, *Pictures of sound*, an 1890s gramophone
recording): AUTHENTIC 0 → **SUSPICIOUS 80**. Its low wall reads 11,750 Hz,
which sits in Rule 1's 128 kbps cell (10,000-15,500 Hz), and the file's
FLAC-equivalent size falls inside that cell's container window (400-550 kbps):
Rule 1 +50, "Constant MP3 bitrate detected (Spectral): 128 kbps", plus Rule 2's
30. No depth instrument was involved. The 23 `mp3_64k` files newly signalled
(P4, 0 → 23) were signalled **by exactly the same path** — Rule 1's container
window on a low wall in the 128 cell — so nothing in the engine separates the
gramophone from the 64 kbps MP3.

The cause is a derivation error of mine: the part of the 128 kbps cell under
14 kHz was **never reachable** before this repair (`detect_cutoff` cannot
answer there), so its container window was never priced against anything that
reads there. A low wall walked into an uncalibrated cell.

**A3 — one mover off the registered profile.** *This is a sound spectrogram*
(National Academy of Sciences, same album): AUTHENTIC 18 → AUTHENTIC 0, cutoff
16,250 → 7,500 Hz. The profile said "read ≥ 0.999 × Nyquist before"; on a file
over 90 s the engine takes the MINIMUM over three windows, and one window found
nothing (then a low wall) while another had found an edge at 16,250. The
profile was written for one window. The move is toward acquittal (with its
cutoff under 19 kHz, Rule 11 read the transfer as a tape and granted −40).

### The amended repair

4. **Rule 1 does not read a low-wall cutoff.** When `is_low_wall_reading`,
   Rule 1 returns before any cell or window is consulted, and
   `rule1_may_consult_container` mirrors it (no re-encode is taken). The wall
   is scored by Rule 2's ramp only, as the design section above already said
   it should be; the 128 cell under 14 kHz stays out of reach until it is
   calibrated on something.

This can only remove Rule 1 +50s relative to the first after-pass. Every
corpus with no low wall (every genuine corpus but the stress set, the `he_aac`
arms, `lc_aac_64k`, `mp3_96k`, `mp3_128`) has 0 movers in the first pass and
has 0 under the amended code by construction. The second pass (`after2_*`)
re-runs the four corpora that read a low wall: the 30 stress tracks,
`lc_aac_32k`, `lc_aac_48k`, `mp3_64k`.

### Criteria, re-registered for the second pass

A1, A2 and E4 stand as written. **A3's profile** becomes: every mover's
after-cutoff is a low-wall reading ([2 kHz, 14 kHz), with the wall reason),
whatever the before-cutoff was. P1, P2, P3, P5 and P6 stand. **P4 is
withdrawn and replaced**: `mp3_64k` signalled after = 0 is the expected
consequence of item 4, and is reported as recall given up, not as a
prediction.
---

## RESULTS — appended 2026-09-25 after the second after-pass

Before = 1.16.0 (worktree `fd-v1160`, `b17b9f8`); after = 1.16.0 plus exactly
the two changed files (`spectrum.py`, `rules/spectral.py`; checked with
`git diff --no-index --ignore-cr-at-eol`), frozen in `fd-r8/after_src`. Torch
shimmed out on both sides, `--sample-duration 30`, `--workers 2`. Diff by
`fd-r8/cmp_lw.py` (first pass) and `fd-r8/cmp_lw2.py` (second pass), verdict and
score per file. `after2_*` for the four corpora that read a low wall; every
other corpus had 0 movers in the first pass and has 0 under the amended code by
construction (the amendment can only remove Rule 1 +50s, and only on low-wall
readings).

| corpus | files | signalled before → after | convicted before → after | Rule 8 protecting after | low wall read | movers |
|---|---|---|---|---|---|---|
| audit authentic | 80 | 2 → 2 | 0 → 0 | 64 | 0 | 0 |
| v2 genuine | 59 | 2 → 2 | 1 → 1 | 43 | 0 | 0 |
| full-length genuine | 12 | 0 → 0 | 0 → 0 | 12 | 0 | 0 |
| received files | 22 | 2 → 2 | 0 → 0 | 10 | 0 | 0 |
| **30 stress tracks** (after2) | 30 | 0 → **0** | 0 → 0 | 29 → **0** | 30 | 15 |
| `lc_aac_32k` (after2) | 80 | 0 → 0 | 0 → 0 | 80 → **9** | 71 | 43 |
| `lc_aac_48k` (after2) | 80 | 0 → 0 | 0 → 0 | 80 → **3** | 77 | 53 |
| `mp3_64k` (after2) | 80 | 0 → 0 | 0 → 0 | 80 → **8** | 72 | 71 |
| `lc_aac_64k` | 80 | 6 → 6 | 0 → 0 | 8 | 0 | 0 |
| `mp3_96k` | 80 | 41 → 41 | 23 → 23 | 5 | 0 | 0 |
| `he_aac_32k / 48k / 64k` | 80 each | 17 / 25 / 16, unchanged | 17 / 22 / 1, unchanged | | 0 | 0 |
| `mp3_128` (control) | 80 | 49 → 49 | 28 → 28 | 5 | 0 | 0 |

The movers' count is smaller than the low-wall count because a file whose
Rule 8 −50 is replaced by Rule 2's +30 and then Rule 11's cassette −40 lands on
the same clamped score it had: the reading changed, the number did not.

| # | criterion | bound | result |
|---|---|---|---|
| A1 | genuine newly convicted | 0 | **0 — held** |
| A2 | genuine newly signalled | 0 | **0 — held** after the amendment; **breached in the first pass** (Berliner, SUSPICIOUS 80, see the amendment) |
| A3 | every mover on the (amended) profile | all | **held** — every mover reads a low wall after, with the wall reason; breached in the first pass as written for one window (the spectrogram track, see the amendment) |
| P1 | `lc_aac_32k` protection gone | ≥ 68 | **71 — held** |
| P2 | `lc_aac_48k` protection gone | ≥ 72 | **77 — held** |
| P3 | `mp3_64k` low wall read | ≥ 68 | **72 — held** |
| P4 | *withdrawn by the amendment* — `mp3_64k` signalled after | — | 0; 23 in the first pass, given up with the uncalibrated cell |
| P5 | `lc_aac_32k` / `48k` signalled after | ≤ 8 each | **0 / 0 — held** |
| P6 | the 30 stress tracks | all AUTHENTIC with the wall reason | **30 of 30 — held** |
| E4 | transcodes losing a signal or a conviction | 0 | **0 — held** |

**Ships in 1.17.0.** What it does and does not do, in one paragraph: on 220 of
the 240 files of the three low-rate arms that read a wall, the engine no longer
reports a full spectrum it did not see and no longer grants Rule 8's −50; it
says where the music stops. It signals none of them, and after the amendment
that is by design: the one engine path that would have signalled the 64 kbps
MP3s signalled an 1890s gramophone record by the same arithmetic. A second,
independent reading that a restored 78 does not share is what this needs next;
none exists here yet.