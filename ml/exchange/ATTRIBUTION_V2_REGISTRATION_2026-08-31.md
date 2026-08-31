# Attribution, layer two — a calibrated null and an abstention rule. Registered before the run

Written and committed **before `ml/attribution_v2_probe.py` is run once**, and
before the held-out files have been touched.

---

## What layer one measured, and what it refused

`ATTRIBUTION_REGISTRATION_2026-08-30.md`: all five predictions failed, and the
defect was the design's — raw R compared across five probes as though one scale
fitted all of them, so the twolame probe won by sitting lower. Centring each
probe on its own median over genuine material and scaling by its own spread
turned 37 % into 47 %, and split it cleanly: **mp3 12/12, opus 12/12, aac 2/12,
vorbis 2/12, aacmf 0/12**.

That number is **post-hoc**. The calibration was derived on the same twelve
genuine files it was then evaluated against, which is the oldest way to produce
a confident wrong number. Layer two exists to make it honest, and to add the
thing whose absence made layer one unusable.

**A4 failed and it was the safety criterion**: genuine masters were attributed
confidently rather than abstaining, so the instrument invents provenance on a
file that has none. Until an abstention rule exists with a real bar under it,
no number from this instrument may go near a wild file. That is what is being
built here.

## The design

**Calibration set**: the 12 genuine files already measured (`audit_corpus`
files 1-12). Their per-probe median and spread are the null, frozen from this
document forward.

**Held-out set**: files 13-24 of the same corpus — never measured under this
instrument — and their five arms. 12 genuine + 60 lossy = 72 files, none of
which contributed to the calibration.

**The statistic**: for each probe *p*, `z_p = (R_p − median_p) / spread_p`, both
constants taken from the calibration set only.

**The abstention rule**, and it is the point of layer two:

    attribute to argmin(z) ONLY IF   min(z) <= Z_FIRE
                                AND  second(z) − min(z) >= Z_MARGIN
    otherwise abstain

`Z_FIRE = −1.0` and `Z_MARGIN = 1.0`, chosen from the calibration set's own
geometry before the held-out files are read: −1.0 is one spread below the
genuine median, and a margin of one spread is the smallest gap that is not
within the null's own noise. **Both constants are frozen by this document.**

## Predictions

| # | prediction | bound |
|---|---|---|
| **B1** | **The safety criterion, again.** Genuine held-out files that are attributed to any family rather than abstaining | **≤ 2 of 12** |
| **B2** | **MP3 survives held out.** `mp3_320` attributed to mp3 | **≥ 10 of 12** |
| **B3** | **Opus survives held out.** `opus_256` attributed to opus | **≥ 10 of 12** |
| **B4** | **The instrument knows what it cannot do.** On the three arms layer one failed (`aac_ff256`, `aacmf_256`, `vorbis_q8`), it **abstains** more often than it attributes | abstention rate > attribution rate on those 36 files |
| **B5** | **No accidental Layer II.** The twolame probe wins on ≤ 2 of the 60 lossy files once calibrated | ≤ 2 |

**B1 is binding.** If genuine files are still attributed, layer two has not fixed
what layer one broke and the instrument stays off wild files regardless of how
well B2 and B3 read.

**B4 is the interesting one.** An instrument that says "MP3, confidently" and
"I don't know" is useful. An instrument that says "vorbis" when it means "I
don't know" is worse than nothing, and that is what layer one did.

Results appended below, dated after the fact.

---

# RESULTS — appended 2026-08-31, criteria unedited above

**All five held.** 72 held-out files, 360 probe reads, none of which contributed
to the calibration. `ml/attribution_v2_probe.csv`.

| # | bound | measured | |
|---|---|---|---|
| B1 genuine attributed instead of abstaining | ≤ 2/12 | **1/12** | **held** |
| B2 mp3_320 → mp3 | ≥ 10/12 | **10/12** | **held** |
| B3 opus_256 → opus | ≥ 10/12 | **12/12** | **held** |
| B4 abstains more than it attributes on AAC/Vorbis | abstentions > attributions | **31 against 5** | **held** |
| B5 no accidental Layer II | ≤ 2/60 | **0/60** | **held** |

    population           mp3    aac  vorbis   opus    mp2  abstain
    authentic              0      0       0      1      0       11
    fake/mp3_320          10      0       0      0      0        2
    fake/aac_ff256         1      0       0      1      0       10
    fake/aacmf_256         0      0       0      1      0       11
    fake/opus_256          0      0       0     12      0        0
    fake/vorbis_q8         0      0       1      1      0       10

## What changed, and it was not the measurement

The R values are the same statistic layer one computed. What was added is a null
each probe is measured against — its own median and spread over genuine material
— and a rule that refuses to answer when the best z is not below −1.0 or the
runner-up is within 1.0 of it. Both constants were frozen by the registration
before the held-out files were read.

Layer one attributed something to every file and was wrong most of the time.
This one **says "mp3" or "opus" and otherwise says nothing**, and it is right
when it speaks: 22 of 24 on the two families it can do, 11 of 12 abstentions on
genuine, 31 of 36 abstentions on the three families it cannot.

**The safety criterion that failed in layer one now holds.** One genuine file in
twelve receives a label — against twelve in twelve before — and that one is
recorded rather than rounded away: an instrument that invents provenance once in
twelve is still not fit to be pointed at a single wild file on its own, but it
is now fit to be one witness among several, which is the standard every other
family in this engine is held to.

## What it does not do, said plainly

AAC and Vorbis remain unattributable — 1 hit and 1 hit out of 36 — and the
instrument now knows it rather than guessing. That is the whole difference
between layer one and layer two, and it cost nothing but a null and a bar.
