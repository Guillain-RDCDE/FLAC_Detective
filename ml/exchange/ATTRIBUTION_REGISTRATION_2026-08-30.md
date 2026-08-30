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

---

# RESULTS — appended 2026-08-30, criteria unedited above

**All five predictions failed.** 72 files, 360 probe reads,
`ml/attribution_probe.csv`.

| # | bound | measured | |
|---|---|---|---|
| A1 self-pairing on mp3_320 | ≥ 9/12 | **7/12** | failed |
| A2 all families | ≥ 60 % | **37 %** (22/60, chance 20 %) | failed |
| A3 codec not encoder | ≤ 20 pts apart | aac_ff **67 %** vs aacmf **8 %**, 58 pts | failed |
| A4 masters abstain | ≥ 8/12 tight | **5/12** | failed |
| A5 no accidental Layer II | ≤ 2/60 | **22/60** | failed |

A5 explains much of the rest: the twolame probe won 22 of 60 lossy files and 6
of 12 genuine ones. It is not recognising Layer II; it is a **sink**. Its R is
systematically lower than the others' because its own round-trip is less
idempotent, and the design compared raw R across probes as though one scale fit
all five. That is the defect, and it is mine: **R is not comparable across
families without calibration.**

## Post-hoc, and labelled as post-hoc — the idea survives, narrowed

Not registered, computed after the failure, and therefore evidence of a
hypothesis worth testing rather than a result. Each probe's R is centred on its
own median over the twelve genuine files and scaled by its own spread there, and
the file is attributed to the lowest z:

    probe median R on genuine:  mp3 3.03   aac 2.03   vorbis 1.94   opus 8.96   mp2 1.89
    probe spread on genuine:    mp3 0.74   aac 4.19   vorbis 1.12   opus 1.72   mp2 1.70

    attributed correctly: 28/60 = 47 % against 20 % chance

and it is not spread evenly, which is the whole finding:

    mp3_320    12/12   perfect
    opus_256   12/12   perfect
    aac_ff256   2/12
    vorbis_q8   2/12
    aacmf_256   0/12

**Self-pairing is real for MP3 and for Opus and absent for AAC and Vorbis** —
and not for want of an encoder match: the aac_ff256 arm was made by the very
encoder its probe uses, same bitrate, and still reads at chance. MP3 and Opus
converge to a fixed point that a re-encode can find; ffmpeg's AAC and libvorbis,
on this instrument, do not.

## What does NOT change, and it is the important half

**A4 failed, and A4 was the safety criterion.** Genuine masters are attributed
confidently — post-hoc they scatter 2/0/4/4/2 across the five families rather
than abstaining. So the instrument invents provenance on a file that has none,
and **no number from it may be put on a wild file, in either direction.** That
bar was registered before the run precisely so it could not be argued away
afterwards.

## What the next layer needs

Not more probes: a calibrated per-probe null, measured on genuine material, and
an abstention rule with a real bar under it — "no family unless the best z is
below X and the runner-up is above Y". Both are one experiment, and it gets its
own registration. Provir's encoder collection (LAME by era, Fraunhofer ACM,
l3enc) is the layer after that, and nothing from it has been executed here yet.
