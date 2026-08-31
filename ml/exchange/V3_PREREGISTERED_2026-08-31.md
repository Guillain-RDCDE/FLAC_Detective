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
