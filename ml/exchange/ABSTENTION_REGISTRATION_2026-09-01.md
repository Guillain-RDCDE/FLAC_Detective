# An abstention on the transcode axis — registered 2026-09-01, before any measurement

Written and committed before the first number. Results appended in a dated
section. A criterion that fails is recorded as failed; one that is mis-specified
is withdrawn in writing.

## Where this came from

Jamie Dodd built an ATRAC3+ arm into exchange set B and described it as an
abstain test: "the question is whether an engine says CLEAN when it should say
UNREADABLE — a false negative wearing a pass."

Checking before answering him: `src/flac_detective/analysis/new_scoring/verdict.py`
has exactly three outputs on the transcode axis — `AUTHENTIC`, `SUSPICIOUS`,
`FAKE_CERTAIN`, plus `WARNING`. There is no abstention. `AUTHENTIC` is returned
whenever the score fell below the warning tier, which merges two different
statements:

* the instruments ran and found nothing, and
* **the instruments could not run at all.**

The second is not a finding. It is the absence of one, and the engine currently
reports it in the same word it uses for a clean bill of health. This is the same
defect as the typed-absence work of v1.13.1 — an absence rendered as a value —
one level up, at the verdict rather than at a float.

The lesson is already proven inside this codebase: the family-attribution layer
failed all five of its registered predictions until it was given a null per probe
**and the right to abstain**, after which all five held. This registration asks
whether the same right belongs at the verdict.

## What is NOT claimed

This does not give the engine an ATRAC instrument, and it will not make set B's
ATRAC arm read correctly. A file that has been through a codec we cannot measure
will still have every rule run and find nothing. **That case is a genuine limit
and stays a limit**; the letter of 1 September says so in those words. Anything
here that appears to close it would be overclaiming.

What is in scope is narrower and real: files where the accusing instruments were
never able to speak.

## The mechanism under test

A fourth verdict, `NOT_ASSESSED`, returned when the accusing instruments could not
run on this file. Candidate trigger conditions, each of which must be *nameable in
the report* (a bare abstention is worse than a wrong answer):

* the spectrum is unanalysable, so `cutoff_freq` is unknown (NaN) — the spectral
  family, which every other rule leans on, has no input;
* the file is mono or too short for the frame-based witnesses, so the stereo and
  temporal families cannot testify by construction.

## Populations

| id | what | source |
|----|------|--------|
| Q1 | 80 authentic files | `audit_corpus/authentic` |
| Q2 | the 13 arms now present | `audit_corpus/fake/*` |
| Q3 | set A's 288 shipped files | `fd-exchange-v3-setA-r2` |
| Q4 | deliberately unreadable inputs built for this: mono, 3-second, 8 kHz-sampled, and a silent file | built here |

Q4 is built **before** the trigger conditions are fixed, and is the only
population expected to abstain.

## Criteria

* **B1 — nothing that convicts stops convicting.** Zero files across Q1–Q3 move
  from `FAKE_CERTAIN` to `NOT_ASSESSED`. A conviction is evidence that the
  instruments ran.
* **B2 — the abstention is rare on real material.** At most 1 % of Q1 ∪ Q2 ∪ Q3
  abstains. Above that, the trigger is too broad and the mechanism is refused.
* **B3 — the abstention is right where it is expected.** Every file in Q4
  abstains.
* **B4 — every abstention names its reason** in the report string, and the reason
  is one of the declared trigger conditions. An abstention with a generic message
  fails this criterion.
* **B5 — measured first, shipped second.** If the count of Q1 ∪ Q2 ∪ Q3 files that
  would abstain is **zero**, the mechanism is still shipped — Q4 shows it is not
  vacuous — but the registration records in writing that it changed nothing on
  real material, so no future document may cite it as a repair of an observed
  failure.

**Refusal clause.** If B1 or B2 fails, `NOT_ASSESSED` is not shipped and the
conflation stays documented and open.

## Amendment, 1 September 2026 — Q4 was mis-specified, found by Q4 itself

Building Q4 and running the trigger conditions over it, before the real
measurement, three of its four files did **not** abstain. That is a defect in this
document, not in the engine, and it is recorded rather than quietly repaired.

* **`mono` is withdrawn from Q4.** A mono file loses the stereo and temporal
  witnesses, but the spectral family, the CNN and the MDCT statistic all run on it
  normally. It is assessable, with fewer witnesses — which the corroboration
  barrier already handles by requiring two families. Listing it as unreadable was
  wrong. **B3 as originally written cannot be met and is amended, not deleted.**
* **`rate8k` and `silent` should abstain and did not**, because the two trigger
  conditions declared above do not cover them. An 8 kHz file has a perfectly
  readable cutoff at 4 kHz; it is simply that every accusing instrument in this
  engine reads a band that does not exist in the file. A silent file likewise
  yields a cutoff without yielding anything to measure.

Two trigger conditions are therefore **added** here, before the measurement, with
their reasons:

* **sample rate below 32 kHz.** Below that there is no content above 16 kHz at
  all, which is the band every accusing rule reads. The floor is declared rather
  than swept: it is not a tuning parameter, it is the point below which the
  instruments have no domain.
* **no measurable signal** — a file whose energy is at or below the silence floor.
  There is nothing for any instrument to be right or wrong about.

Revised **B3**: every file in Q4 minus `mono` abstains, and `mono` does **not**.
That is a stricter test than the original, because it now requires the trigger to
be wrong in neither direction.

## Second amendment, 1 September 2026 — the duration floor was invented, and the existing tests caught it

The trigger "too short for the frame-based witnesses" shipped with a threshold of
**10 seconds**, which I chose because it sounded reasonable. It is not a measured
value and it should never have been written next to three conditions that are.

Two tests in `tests/test_wav_support.py` failed on it. They build **2-second**
synthetic WAVs and assert `AUTHENTIC`, and under the new verdict they abstained.
The tests were right. A 2-second file is read perfectly well by the spectral
family, by the CNN and by the MDCT statistic; nothing about it is unassessable.

The real floor is the frame witness's own arithmetic. Rule 15 needs `MIN_FRAMES`
(16) frames of a 2048-point STFT hopped by 1024:

    2048 + 1024 x 15 = 17,408 samples = 0.39 s at 44.1 kHz

Twenty-five times smaller than what I wrote. The constant is now **derived from
those three values in code** rather than stated, so it cannot drift from the
instrument it describes and cannot be quietly tuned, and it is applied in samples
rather than seconds so it stays correct at any sample rate.

Consequences, recorded rather than absorbed:

* Q4's `short` case was built at 3 seconds, which is **above** the real floor, so
  it should never have abstained either. It is rebuilt at 0.2 s. My original Q4
  was wrong about two of its four files, for the same underlying reason both
  times: I described the instruments from memory instead of reading them.
* **Revised B3, second time**: `rate8k`, `silent` and a genuinely sub-frame
  `short` abstain; `mono` and any file of ordinary length do not.
* B2's measurement is unaffected — every file in Q1–Q3 is a 30-second excerpt or
  longer, so neither the old threshold nor the new one was ever exercised on real
  material. That is stated plainly here so no later reading can treat the 0 % as
  evidence that this particular trigger is well calibrated. It is evidence about
  the other three.

## Results — 1 September 2026

1,248 real files: 80 authentic, 880 arms across 13 codec configurations, and the
288 of exchange set A.

| criterion | outcome |
|---|---|
| **B1** convictions untouched | **HELD** — by construction: only `AUTHENTIC` is ever downgraded, so no accusation can be withdrawn |
| **B2** abstention rare on real material | **HELD** — **0 of 1,248**, 0.00 % against a 1 % bound |
| **B3** right on the control population | **HELD** as twice amended — `rate8k`, `silent`, sub-frame `short` abstain; `mono` does not |
| **B4** every abstention names its reason | **HELD** — each is a specific sentence naming the condition and the measured value |
| **B5** measured first, shipped second | **APPLIES** — see below |

**B5 is the honest headline: this repairs nothing that was observed failing.**
Not one file in any shipped corpus abstains. The clause was written in advance
precisely so this outcome would be recorded rather than dressed up: no later
document may cite `NOT_ASSESSED` as the repair of a measured failure. What it
removes is a verdict the engine had no standing to issue — on files the corpora
happen not to contain and a user's disk certainly does.

One concrete case found while verifying: on the 8 kHz file, Rule 11's bandpass
design **raises** (`Digital filter critical frequencies must be 0 < Wn < fs/2`).
The exception is caught and logged, and the file then arrives at the verdict
looking clean. Before this change the engine answered `AUTHENTIC` to a file it
had just failed to analyse.

### Still not claimed

Nothing here gives the engine an instrument for a codec outside its panel. An
ATRAC3+ transcode has every rule run on it and every rule find nothing, and will
still read `AUTHENTIC`. That limit was stated to Provir in the letter of
1 September, before either half was scored, and it stands.
