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
