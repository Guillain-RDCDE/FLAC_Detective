# fd-exchange-v3 — predictions, registered 2026-08-31, before set B exists

Written and committed **before Provir's set B has been built, named, hashed or
sent**, and before a single file of it has been seen. The protocol we both
signed says predictions are registered before the key is opened and the scoring
script is committed before the set arrives, so that the analysis cannot drift
toward the answer. This is that document; `ml/score_v3_return.py` is that
script, committed in the same action.

Set A is with him (288 files, self-hash `1cbe0edb…`), so from here the honest
window for writing this closes the moment his manifest lands.

---

## The two halves, and what each is worth

**Set B, his half, scored blind by us.** This is the evidence. We have not seen
the files, the sources, the composition or the count.

**Set A, our half, scored by us.** This is a diagnostic and nothing else — no
number produced on a set we chose and keyed is evidence about our engine. It is
reported so that his numbers on set A have something to sit beside, and because
the band-limited stratum is ours to be embarrassed by first.

## Operating point, declared here and binding

* a **conviction** is `FAKE_CERTAIN`
* **signaled** is `WARNING` or above
* both are reported; the conviction number is the one that counts
* engine version and commit SHA travel inside the verdict-file hash

## Predictions on SET B — his half, blind

| # | prediction | bound |
|---|---|---|
| **K1** | **False convictions.** Genuine files we convict | **≤ 2 %** of his genuine rows, and never more than 3 files whatever the count |
| **K2** | **The band-limited stratum is where we are hurt.** Our false-conviction *rate* on his band-limited genuine rows is higher than on his full-band genuine rows | **stated as a direction, not a bound** — if it is not higher, the R11D repair did more than we think and that is worth knowing |
| **K3** | **Layer II.** If his half carries an MP2 arm, we convict **fewer than 30 %** of it — both engines were blind to that filterbank in v2 and one release has not fixed it |
| **K4** | **Recall ordering.** Conviction rate is highest on the MP3 arms, lowest on the high-rate AAC arm, with Opus and Vorbis between — the ordering v2 measured, on a set we did not build |
| **K5** | **Agreement on the easy end.** On rows where his engine and ours both convict, the key agrees with both | **≥ 95 %** |

**K1 is the safety criterion.** Breaching it means the engine convicts honest
files on somebody else's terrain, and no efficacy number in the same run may be
quoted without it attached.

## Predictions on SET A — our half, diagnostics only

| # | prediction | bound |
|---|---|---|
| **A-i** | We convict **0** of our own 36 genuine rows, band-limited included | 0 — a set we built, at a threshold we chose; anything else is a defect, not a result |
| **A-ii** | Our conviction rate on `mp2_256` is **below** our rate on `mp3_320` | direction only — the Layer II arm exists to measure a blind spot, not to be passed |
| **A-iii** | The 12 `band_limited_synthetic` genuine rows are signaled **more often** than the 24 full-band genuine rows | direction only, and if it holds it is a cost of the R11D repair, disclosed |

## What is NOT predicted, deliberately

His engine's numbers on set A. We hold that key; predicting his score against
our own answers would be the circular exercise this whole exchange exists to
avoid. They are reported when they arrive and adjudicated at the mechanism.

## Method, fixed now

1. His manifest arrives; we verify it against the audio **at read time**, not at
   copy time, and we do not touch a file before the manifest verifies.
2. We score set B with the engine at a named commit, producing one verdict CSV.
3. We post the **SHA-256 of that verdict file** — with the engine version and
   commit SHA inside it — before either key moves.
4. Keys are exchanged in the same message that follows.
5. `ml/score_v3_return.py` runs, unedited, against his key and ours. Any change
   to the script after his manifest arrives is recorded as an amendment with its
   reason, in a section dated after the fact.

Results appended below, dated after the fact. Nothing above may be edited once
his manifest is in hand.

---

# SET A, OUR OWN HALF — scored 2026-08-31, diagnostics only, criteria unedited above

Run before his set B arrived, deliberately: a defect on our own half is worth
finding now rather than during his. 288 files, engine 1.13.2 @ `e176d103`,
manifest verified at read time (288 of 288), verdict file SHA-256
`a7b798b53c1a300c472dc1202c9713db1519be6305c6c6704c2279c370ed8e91`.

| # | prediction | measured | |
|---|---|---|---|
| **A-i** | 0 false convictions on our own genuine | **1 of 36** | **FAILED** |
| **A-ii** | mp2_256 convicted below mp3_320 | **47 % against 11 %** | failed, and in the opposite direction |
| **A-iii** | band-limited genuine signalled more than full-band | **33.3 % against 4.2 %** | as predicted |

    conviction rate by arm
      mp2_256 47 %   aacmf_256 42 %   vorbis_q8 36 %   aac_ff256 11 %
      mp3_320 11 %   opus_256 8 %     mp3_V0 6 %

## A-ii failed in the informative direction

Layer II was added as the arm both engines were blind to, and it is the arm this
engine convicts **most**. The v2 blindness was in the MP3-family *idem and MDCT*
instruments, which look for a filterbank Layer II does not have; conviction
overall is another matter, and mp2_256 band-limits hard enough that the spectral
rules do the work. The prediction was right about the mechanism and wrong about
what it implies for the verdict, which is worth more than being right.

## A-i failed, and it opened the worst finding of the round

The convicted file is one of the twelve `band_limited_synthetic` sources, on
`spectral+stereo` — two evidence families, which is what the corroboration gate
asks for. Four of the five signalled genuine files are from the same stratum.

Chasing it produced a measurement on material that is **not in the shipped set**:
44 parked genuine sources, all AUTHENTIC, given a 14 kHz roll-off and nothing
else — **15 convicted, 22 signalled**. Full write-up, the mechanism, a repair that
was implemented and then **refused by its own preliminary check**, and what comes
next: `ml/exchange/R15_BANDLIMIT_REGISTRATION_2026-08-31.md`.

**This is the stratum earning its place before the round has even started.**
Provir named band-limited genuine material as the hardest false positives in this
space; the stratum had to be constructed because it could not be found; and the
first thing it did was convict our own engine of a third of it.
