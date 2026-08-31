# Era attribution — which LAME BUILD made this? Registered before the run

Written and committed **before `ml/era_attribution_probe.py` is run once**, and
before a single file has been encoded by any of Provir's binaries.

---

## The question nobody in this space asks

Every tool answers *is this a transcode?*. Layer one of attribution asked *by
what codec?* and answered: MP3 and Opus yes, AAC and Vorbis no. This asks the
next one down, and it is the one that would make the tool forensic rather than
diagnostic: **by which build?**

The ingredients are on this machine and none of them is ours:

* **Provir's encoder collection**, second delivery, 335 manifest entries — 61
  LAME builds from 3.20 to 3.100.1, plus Fraunhofer, Xing, Helix, BladeEnc,
  8hz, Gogo, Shine, Musepack and the rest. Archived on receipt 2026-08-22 and
  **never executed here until today**.
* **His fixed-point finding**: 20 of 34 wild files sitting exactly at the
  lame3.90.3 fixed point. That is already an attribution result; it has simply
  never been named as one.
* The idem instrument, and the grid lock that says any phase-0-only read of it
  is meaningless.

## Integrity first, because these are someone else's binaries

The five builds used here were verified byte-for-byte against his own
`SHA256SUMS.txt` before being run: **5 of 5 exact, 0 divergent, 0 outside the
manifest**. `lame3.92` reads `cb2cdfde7b170d90…`, byte-identical to the exhibit
key he pinned on 2026-08-21 and this repository archived the same day. They are
executed from his tree, on our own audio, into a scratch directory.

## The instrument

Five builds spanning the eras his register documents:

    lame3.90.3   the fixed point his wilds sit on
    lame3.92     near-sibling of 3.90.3 — same codebase generation
    lame3.96.1   mid era
    lame3.98.4   late era
    lame3.100    current

Six genuine 20-second excerpts, each encoded at CBR 320 by each build and
decoded back — 30 files whose build is known by construction. Each is then read
under **all five builds as probes**: R at the best of the canonical phases
{0, 529, 47}, the probe encoder being the build under test and the decoder held
constant (ffmpeg), so the only variable across probes is the encoder.

Attribution = argmin over the five probes. 150 probe reads.

## Predictions

| # | prediction | bound |
|---|---|---|
| **E1** | **Build-level self-pairing exists.** The matching build returns the lowest R | **≥ 20 of 30** (chance is 6 of 30) |
| **E2** | **3.90.3 and 3.92 are NOT separable from each other.** Files made by one are attributed to that pair (either member) far more often than to a distant build, but which member wins is near chance | pair-level hits ≥ 10 of 12, member-level hits ≤ 9 of 12 |
| **E3** | **Era separates even where build does not.** Grouping {3.90.3, 3.92, 3.96.1} against {3.98.4, 3.100}, the correct group wins | **≥ 24 of 30** |
| **E4** | **Masters stay out.** The six genuine excerpts read higher (less negative) under every probe than any encoded file does under its own build | **0 of 6** genuine files reads below the highest encoded self-pair R |

**E1 is the headline and E3 is the fallback.** If E1 fails and E3 holds, the
honest claim is era attribution, not build attribution, and that is still
something no published tool does.

**E4 is the safety criterion**, and it is the same one layer one failed. If a
genuine master reads like a build, the instrument invents a provenance and no
number from it may be attached to a wild file — the wild-fake ledger's `basis`
field exists precisely so that a machine's guess never becomes a label.

**E2 is a prediction of failure**, written to keep the result honest: 3.90.3 and
3.92 are one codebase generation apart, and an instrument that claims to
separate them should be disbelieved before it is celebrated.

Results appended below, dated after the fact.
