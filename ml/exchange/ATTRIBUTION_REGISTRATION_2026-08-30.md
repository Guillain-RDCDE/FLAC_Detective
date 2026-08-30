# Encoder attribution — registered 2026-08-30, before the measurement

Written and committed **before `ml/attribution_probe.py` is run once**. Layer one
of the question this project has never asked.

---

## The question, and why it is not the usual one

Every tool in this space answers *is this a transcode?*. None answers **by
what?** — and the ingredients for the second question are already here:

* Provir's **family lock** (his bench, adopted 2026-08-22): a LAME file drops
  under the LAME probe at its true phase, while Fraunhofer arms stay high at
  every phase. A probe is not just a detector; **it is a probe of one family.**
* Provir's **grid lock**: the fixed point has period 576 samples and zero
  tolerance, so a phase-0 read of anything is meaningless unless the phase is
  searched. Every number below is at the best canonical phase.
* The idem instrument (`ml/mp3_idem_probe.py`), and an ffmpeg with libmp3lame,
  ffmpeg-aac, MediaFoundation aac, libopus, libvorbis and libtwolame.

So the design is a **bank of probes, one per family**, each a round-trip through
that family's encoder, and the file is attributed to whichever probe it falls
furthest under. If a transcode really carries its encoder's filterbank, the
matching probe should be the one that cannot make it worse.

This layer is **family** attribution — MP3 vs AAC vs Vorbis vs Opus vs Layer II.
Build-and-era attribution (LAME 3.90.3 against 3.92 against Fraunhofer ACM, from
Provir's 335-entry encoder collection) is the next layer and gets its own
registration; nothing from that collection has been executed here yet.

## The instrument

For each file, five probes: `libmp3lame -b:a 320k`, ffmpeg `aac -b:a 256k`,
`libvorbis -q:a 8`, `libopus -b:a 256k`, `libtwolame -b:a 256k`. Each probe is
the same two-round-trip R the MP3 probe already computes, read at the best of the
canonical phases {0, 529, 47} and never at phase 0 alone. Attribution = the
family whose probe returns the **lowest** R.

Populations, from `audit_corpus`, 12 sources each so no arm can win on sample
size: `genuine`, `mp3_320`, `aac_ff256`, `aacmf_256`, `opus_256`, `vorbis_q8`.
72 files, 360 probe reads.

## The predictions

| # | prediction | bound |
|---|---|---|
| **A1** | **Self-pairing exists.** For `mp3_320`, the MP3 probe returns the lowest R | ≥ **9 of 12** files |
| **A2** | **It generalises past MP3.** Across the four lossy arms, the matching family wins | ≥ **60 %** of 48 files (chance is 20 %) |
| **A3** | **Codec, not encoder.** `aacmf_256` (MediaFoundation) is attributed to AAC by the ffmpeg-AAC probe as often as `aac_ff256` is | the two rates within **20 points** of each other |
| **A4** | **The genuine files abstain.** A master has no filterbank to match, so no probe should dominate | on ≥ **8 of 12** genuine files the spread between best and second-best probe R is **< 0.5**, against ≥ 0.5 on the majority of lossy files |
| **A5** | **Nothing is attributed to Layer II by accident.** The twolame probe wins on none of the MP3/AAC/Vorbis/Opus arms | ≤ **2 of 48** |

**A1 failing means the family lock does not reproduce on our instrument**, and
the whole idea stops there — that is the result, and it gets published as one.
**A2 failing with A1 holding** means self-pairing is an MP3 property rather than
a general one: still a finding, and a narrower claim than the one being tested.
**A4 is the safety criterion.** If genuine masters are confidently attributed to
an encoder, the instrument invents provenance, and no number from it may be used
on a wild file.

Results are appended below, dated after the fact. Nothing above may be edited
once the first number exists.
