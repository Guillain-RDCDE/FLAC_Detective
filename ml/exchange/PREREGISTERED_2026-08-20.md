# Pre-registered prediction — Provir's wild set, before we receive it

Written **2026-08-20**, before any of Jamie Dodd's 53 wild files have been sent,
seen, or hashed. Committed on the same day it was written so the timestamp is in
git rather than in a claim. Nothing below may be edited after the files arrive; a
correction goes in a new section dated after the fact.

The convention comes from Provir and both sides now hold to it: predictions are
published before measurement, because the two times this project got a prediction
wrong taught it more than the six times it got one right.

---

## What we are predicting on

Jamie's ledger splits 34 owner-ruled lossy files by how each was **settled**:

| basis | n |
|---|---|
| `owner-eye` — the spectrogram was decisive | 16 |
| `ear+eye` — he had to listen; the picture alone was ambiguous | 9 |
| `fake_registry` — a known scene fake, identified by release | 4 |
| `eye` | 2 |
| `owner+provenance` | 1 |
| `identity` — byte identity to a known lossy source | 1 |
| `owner-eye+windowed-anatomy` | 1 |

Six of the 34 rest on something other than his eyes or ears. He says so himself,
unprompted, and calls n=6 too small to score a spectral axis against.

His engine's own split is the reason this document exists:

    owner-eye files    14 of 16 convicted    88 %
    ear+eye files       0 of  9 convicted     0 %

Where he could see it, his engine agrees with him almost always. Where he needed
his ears, it convicts none.

## Why the 9 `ear+eye` files are the test that matters to us

Provir's conviction path is band-edge-led. So is our `spectral` family. If that
were all either engine had, both would post the same shape: high where the eye
already knew, zero where it didn't.

But this engine's other four families do not look at the band edge:

- `mdct` (Rule 13) — MDCT alignment and hole density, KBD α=4 and Vorbis windows
- `stereo` (Rule 15) — dead runs in the side channel, above 10 kHz
- `temporal` (Rule 14) — per-bin variance drop over time
- `cnn` (Rule 12) — learned, on a spectrogram but not on its edge

Those 9 files are the only population available anywhere that was **selected by
the ear and survived the eye**. That makes them the cleanest available test of
whether our non-spectral families are genuinely independent instruments or
elaborate re-derivations of the same band edge.

This test can go against us, and that is the point of writing it down first.

## The predictions

Registered as five bounds. All are on the 9 `ear+eye` files.

**P1 — Flag rate.** At least **4 of 9** are flagged (verdict not `AUTHENTIC`).

**P2 — Conviction rate.** At least **2 of 9** reach `FAKE_CERTAIN`. Provir reads
0 of 9. A result of 0/9 for us as well is a failure of this prediction and should
be read as evidence that our extra families do not reach past the eye.

**P3 — Provenance of the convictions, and the one that actually matters.** Of the
files we convict, **more than half draw at least one of their two corroborating
families from `mdct`, `stereo`, `temporal` or `cnn`** — not two `spectral`-derived
sources. If we convict these files on band-edge evidence alone, we have not beaten
the eye; we have found a louder way to be it, and P2 succeeding on those terms
should be reported as a failure of P3 rather than a success.

**P4 — The stereo family carries more of them than any other single non-spectral
family.** It is our strongest independent observable on Opus, Vorbis and
high-bitrate MP3 (92 %, 93 %, 92 % witness rates), and MP3-320 is what Jamie's
wild section mostly holds.

**P5 — No false conviction on his referee-grade genuine rows**, whatever their
count. This is not a performance prediction, it is the project's standing
constraint; a failure here outranks every other result in this document.

## What we will NOT do with the rest of the set

Per his own instruction, and because it is right:

- The 16 `owner-eye` and 2 `eye` rows are **selection evidence, not ground truth**
  for anything spectral. Any band-edge measure scored against them will read better
  than it is, in whichever direction the test runs.
- We will publish a rate on the 6 referee-grade rows separately and never averaged
  into a headline. Averaging the eye-chosen population with the one it could not
  see produces a number with no referent — Provir's headline carried that defect
  until they broke it out, and ours would too.
- `ml/wild_fake_ledger.py` gained a `selection` field and a `referee` flag on
  2026-08-20, before any file arrived, and its `status` command now prints the
  cross-tabulation unasked. A split nobody prints is a split nobody can see is
  wrong.

## Scoring protocol

1. Hash every file on arrival; record the manifest hash here before analysis.
2. Run the shipped release, not a working tree. Record the version.
3. Score P1–P5 exactly as stated, with Wilson bounds on every clean line — a 0/9
   reads as "up to **29.9 %**", not as zero, and even a successful 2/9 only bounds
   us to [6.3 %, 54.7 %]. n=9 cannot settle this; it can only refute a strong
   claim, which is precisely what P2 and P3 are for.
4. Publish the result whether or not it flatters us, in a section appended below.

---

*No result section exists yet. Its absence is the evidence that this document
preceded the data.*

---

# AMENDMENT — 2026-08-20, still before any file has been sent

Appended, not edited. The original text above is unchanged; a pre-registration that
gets rewritten when it turns out to be inconvenient is not one. What follows says
what was wrong with it and what replaces it.

## The tier does not mean what this document assumed

Jamie corrected it unprompted, and in time. We wrote that the 9 `ear+eye` rows were
*"selected by the ear and survived the eye"*. They are not. His tier means:

> I had to listen; the picture alone was ambiguous.

**The eye did not confirm those files — it failed to decide.** That is a different
population and it tests a different thing.

He also corrected a second error of ours: *Goodbye My Friend* is **not** in that
group. It is `owner+provenance` — a referee row. We had been treating it as the
exemplar of the tier.

## What that changes

The original P2/P3 were built on "the eye confirmed these, the ear found them", i.e.
a population where two independent senses agreed. What actually exists is a
population where **one sense abstained**. Those are not interchangeable:

- Under the original reading, a 0/9 from our engine would have meant our families
  cannot reach what two senses jointly established.
- Under the correct reading, a 0/9 means our families cannot reach what the eye
  found *undecidable* — which is a weaker claim about us, because an
  eye-undecidable file may be undecidable for a band-edge instrument by construction
  rather than by any failure of architecture.

The test is still worth running, and it is still the sharpest population available.
But it can no longer carry the sentence "this answers whether our non-spectral
families are independent of the eye". It answers a narrower question: **can any of
our families decide a file that a competent spectrogram reading could not?**

He was explicit that if we want ear-selected-and-eye-confirmed, he is not sure such
a population exists on his side. We are not asking him to manufacture one.

## Amended predictions

P1, P4 and P5 stand as written — they do not depend on the misreading.

**P2 (amended).** At least **2 of 9** reach `FAKE_CERTAIN`. Unchanged as a number,
changed in what it means: it is now a claim that our engine can decide files a
spectrogram could not, not a claim about surviving joint confirmation. Provir reads
0 of 9 and he confirms that reproduces on their current build, with all nine
currently at SUSPECT.

**P3 (amended, and this is the one that matters).** Of the files we convict, more
than half must draw at least one corroborating family from `mdct`, `stereo`,
`temporal` or `cnn`. **Unchanged, and now doing more work than before**: since the
eye could not settle these files, a conviction carried by two band-edge-derived
sources would be our engine claiming certainty exactly where the most direct
instrument abstained. That should read as a warning about our thresholds, not as a
success — and it is scored as a failure of P3 either way.

**P6 (new).** On the 6 referee-grade rows, no false conviction, and any rate we
publish for them is published separately and never averaged into a headline with the
25 eye- or ear-chosen rows. This was already our stated intent above; it is promoted
to a scored prediction because an intent is not a bound.

## Why this is being written before the data and not after

Because he gave us the chance, and because a registration spent on the wrong
population is worse than none: it produces a confident answer to a question nobody
asked. The correction costs nothing today. After the files land it would have cost
the whole exercise.

*Still no result section. Its absence remains the evidence that this document
precedes the data.*

---

# AMENDMENT 2 — 2026-08-20, after a delivery that is not the pre-registered population

Appended, not edited. The 53 arrived — as `provir-wild53-feature-ledger.csv` and
`provir-wild53-note.txt` in this directory (receipt sha256 `2345a7baac8e666d…` and
`a19f0bdf51a24048…`) — and **this pre-registration cannot be scored against them.**
Recording why, before anyone is tempted to score it against something adjacent.

## What was delivered vs what was registered

The delivery is a **feature ledger, no audio, no byte-binding** (every sha field
empty — his own note names that gap). Scoring protocol step 1 ("hash every file on
arrival") cannot run, and neither can the engine.

The delivered basis taxonomy is **not the one this document predicted on**: 53
tracks of one commercial compilation (three DJ-mix discs, one master per disc),
split `owner-knowledge` 34 (CD1+CD2) + `eye` 19 (CD3). The tiers P1–P4 and P6 are
written against — `ear+eye` (9), `owner-eye` (16), the 6 referee-grade rows — do
not appear in the delivered ledger at all, and every row is ruled lossy, so P5's
population (referee-grade *genuine* rows) does not exist here either. Whether the
earlier 34-file taxonomy is a different cut of these same discs or a different set
entirely is not decidable from what we hold, and has been asked.

## Status: unspent, not scored, not voided

P1–P6 remain registered and unscored. They spend only when (a) audio arrives with
hashes, and (b) rows exist carrying the tiers they name. A prediction scored
against an adjacent population is worse than one never scored.

## What the delivery DID test — the thing he said it would

"A test of your taxonomy, never a shared benchmark." The schema failed three ways
before a single row was entered, all three now repaired and pinned by
`tests/test_wild_fake_ledger.py`: no basis for an owner's attestation
(`owner_attestation` added, referee-grade), no way to record a ruling made **by
extension** (CD3: 5 tracks examined, 19 ruled — `scope=group` added, note
required), and no way to record a selection **pipeline** (CD3: a metric shortlisted
and an eye ruled — `+`-chained selections added, a chain tainted by its most
sensory link). His CD3 circularity warning is honored as written: the 19 eye rows
are selection evidence for any band-edge statistic, never ground truth.

---

# AMENDMENT 3 — 2026-08-21, before the audio is downloaded

Appended, not edited. Two things his 2026-08-21 reply settled, and one new
registration that must exist before any byte of the 53 lands here.

## The two 34s are different sets, and P1–P6 never spend on this delivery

Confirmed by him: the wild53 ledger's 34 is Nu Breed CD1+CD2, single tier,
`owner-knowledge`, no detector involved — and he cannot find the
16-owner-eye/9-ear-eye split *for this set* anywhere in his records. The split
this document's P1–P6 were written against came from his **corpus-wide** fake
taxonomy (his 2026-08-20 message: 34 fakes, 16 `owner-eye`, 9 `ear+eye`, 6 on
neither eyes nor ears), which is a different population that happens to also
number 34. **P1–P6 therefore stay unspent on the Nu Breed 53 even with audio in
hand**; they spend if and only if the corpus-wide `ear+eye` and referee rows
ever ship. Two 34s colliding is this week's 750-shares-every-third-rung lesson
in census form: an exact numeric agreement between two lists is evidence of
nothing until both lists are named.

## Registered for the Nu Breed 53, before download — the W-series

The audio is en route with a regenerated ledger carrying sha256 + pcm_sha256
per row. **This is not a blind test and is not scored as one**: his labels and
his engine's verdicts are already known here. What the discipline still buys is
predictions about OUR engine committed before it runs. Protocol: hash-verify
every file against his regenerated ledger first; run the shipped release
(v1.11.4) with `--deep`; Wilson bounds on every clean line; CD3 reported
separately everywhere.

    W1  Zero FAKE_CERTAIN across all 53. (His engine convicts none in any
        configuration; our conviction gate needs two independent families, and
        a CD master cut from MP3 decodes is exactly the blunted-tell chain the
        gate was priced for. A conviction here would be MORE alarming than
        impressive, and W1 failing triggers a manual audit of the convicting
        families before anything is celebrated.)
    W2  The signaled rate (verdict ≠ AUTHENTIC) on CD1+CD2 (owner-knowledge,
        n=34) EXCEEDS the rate on CD3 (eye, n=19). Direction only — matching
        the direction his engine reads (32 % vs 5 %), for the stated reason:
        CD3 is HF-poor early-90s material, and our spectral instruments read
        less where there is less to read.
    W3  At least 40 % of CD1+CD2 signaled. First recall claim on an
        owner-attested wild 320 population; the lab arm reads far higher, and
        the gap between lab and wild is precisely what this measures.
    W4  The MP3_IDEM instrument (measured, not a rule): R ≤ 1.68 (our genuine
        p5 bar) on at least 50 % of CD1+CD2. These files are MP3-320-sourced —
        the exact fixed point the probe re-encodes toward — but the mastering
        chain between the MP3 and the disc (level moves, crossfades, re-rip)
        adds distance back, and how much is the question this number answers.
    W5  CD3 is never averaged into any headline with CD1+CD2, in anything we
        publish from this set. A constraint, scored as a prediction, because an
        intent is not a bound.

Being wrong on W2 would matter most: it would say our engine's agreement with
an owner's knowledge does not survive leaving the lab, or that it reads the
eye-chosen disc BETTER than the attested ones — either way something worth a
week. His purchase condition is adopted as written: if any of this music turns
out essential to our binary, buy the disc.

## W-SERIES RESULTS — 2026-08-21, scored on verified bytes

Hash gate: **53/53 verified against his regenerated ledger, 0 missing, 0
divergent** (`ml/score_wild53.py`, per-row output in `ml/wild53_scores.csv`).
Engine: v1.11.4, deep, CNN available; working tree engine-identical to the tag
(diff since: docstrings, comments, one unused constant).

    W1  HELD    0/53 FAKE_CERTAIN (Wilson up to 6.8 %)
    W2  HELD    direction only, as registered: owner-knowledge 3/34 = 8.8 %
                signaled vs eye 0/19 = 0.0 % — Wilson intervals overlap
                ([3.0, 23.0] vs [0.0, 16.8]), so the direction is real and the
                margin is not demonstrated
    W3  FAILED  3/34 = 8.8 % of CD1+CD2 signaled, against a registered >= 40 %
    W4  FAILED  0/34 CD1+CD2 at or under the MP3_IDEM bar (median R 3.18,
                genuine corpus median 2.73 — indistinguishable)
    W5  HELD    by construction of the report

**The failures are the finding.** This is the first measured lab-to-wild gap of
the project: on lab-made direct transcodes the engine signals 68–100 % per arm;
on owner-attested wild 320s that passed through a mastering chain (MP3 decode →
DJ mix, crossfades, levels → CD press → rip) it signals 8.8 % and clears 31 of
34. Provir's engine reads the same tier at 32 % — 3.6× ours, on the population
his flag families were built for. And W4 says WHY: the mastering chain pushes
the audio clean off the MP3 fixed point (R median 3.18 ≈ genuine), so the same
chain plausibly destroys the alignment and side-channel tells our families
read. The lab benchmark measures direct transcodes; the wild sells re-mastered
ones; those are different populations and every published rate now needs to say
which one it is about.

W1 is the half that survives with honour: whatever the recall gap, the engine
convicted nothing — on 53 files whose owner rules them all lossy, zero false
*certainty* in either direction of the argument. The conviction gate priced for
exactly this.
