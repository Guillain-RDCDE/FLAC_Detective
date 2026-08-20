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

# AMENDMENT — 2026-08-21, still before any file has been sent

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
