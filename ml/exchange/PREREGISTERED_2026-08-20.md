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
