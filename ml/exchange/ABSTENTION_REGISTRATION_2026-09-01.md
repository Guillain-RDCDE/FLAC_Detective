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

## Results

*(to be appended, dated, after the measurement runs)*
