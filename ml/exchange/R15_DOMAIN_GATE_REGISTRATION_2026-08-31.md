# Rule 15's domain gate is set too low — registered before the passes

Written and committed **before `stereo_seam.py` is touched and before any
before/after pass runs**. Third document on this defect the same day; the first
two are refusals and they are what make this one short.

---

## The gate already exists

`rules/stereo_seam.py`:

```python
# Below this cutoff the file is band-limited and the 10 kHz band is empty anyway.
MIN_CUTOFF_HZ = 12000.0
```

The reasoning is already correct and already written down. **The constant is
simply in the wrong place.** Our band-limited controls read a cutoff of
15,250-15,500 Hz — above 12,000, so they walk through the gate and the witness
testifies about a band that is not there.

That makes this a re-pricing of a constant that was set on the wrong evidence,
which is the same shape as the R11D repair, and not a new mechanism.

## Why the two previous attempts failed, in one line each

* **Restricting the statistic to live-MID bins** — refused: the MID channel is
  *not* dead on these files (live share 0.88-0.94, higher than a real mp3_320 at
  0.84).
* **A relative dead test** — refused by its own registered guard: it removes the
  artefact completely (0 of 34 over the bar, from 27 of 34) and costs 0.10 of
  arm-vs-genuine AUC against a 0.03 budget. The absolute bar is where the
  witness's signal lives.

So the repair cannot live inside the statistic. It lives in **where the statistic
is allowed to speak** — which is what the gate is for.

## Where the constant goes, and how it was chosen

The cutoff distribution was measured **before** this document was written, and it
is quoted here rather than pretended away:

    genuine (audit_corpus, n=20)   median 22,050   min 19,500
    mp3_320                        median 20,250   min 19,250   0 of 20 below 17 kHz
    aac_ff256                      median 22,050   min 19,500   0 of 20 below 17 kHz
    opus_256                       median 20,250   min 19,500   0 of 20 below 17 kHz
    vorbis_q8                      median 21,500   min 19,500   0 of 20 below 17 kHz
    band-limited controls          median 15,500                18 of 20 below 17 kHz

There is an empty band between **15,500** and **19,250**. The rule applied:
**the round figure inside that gap, placed below the lowest arm cutoff with at
least 2 kHz of margin.** That is `MIN_CUTOFF_HZ = 17000.0`, 2,250 Hz under the
lowest arm reading and 1,500 Hz over the band-limited median.

## Criteria

| # | criterion | bound |
|---|---|---|
| **T1** | convictions on the 44 band-limited controls | **≤ 2**, from **15** |
| **T2** | false convictions on set A's own 36 genuine | **0**, from **1** |
| **T3** | convictions lost on the four high-rate arms (mp3_320, aac_ff256, opus_256, vorbis_q8; 160 files) | **≤ 2** — none of them reads below 17 kHz, so a loss here means the gate is doing something other than what it says |
| **T4** | convictions lost on the low-rate arms (mp3_192, aac_ff128; 80 files) | **reported, not bounded** — this is where the gate genuinely bites, and it is the population Rule 1 already convicts on the cutoff alone |
| **T5** | set A's 252 lossy rows | conviction loss **≤ 8** |

**T3 is the criterion that can refuse this.** The gate is justified by the claim
that no real high-rate transcode sits below 17 kHz; if convictions are lost there
anyway, the claim is wrong and so is the constant.

**T4 is the honest cost, disclosed rather than bounded.** A witness that stops
testifying about heavily band-limited files loses nothing the engine needs: those
files are Rule 1's domain, convicted on the wall itself. Reporting it is the
point — a repair whose price is not named is a repair nobody can argue with.

Results appended below, dated after the fact.

---

# RESULTS — appended 2026-08-31, criteria unedited above

Before on `MIN_CUTOFF_HZ = 12000`, after on `17000`, same files, same order,
full engine, `deep=True`. 284 files for T1/T3/T4 (`ml/r15_gate_pass.py`) and
set A's 288 for T2/T5 (`ml/run_engine_on_set.py`).

| # | bound | measured | |
|---|---|---|---|
| **T1** convictions on the band-limited controls | ≤ 2 | **15 → 4** | **failed** |
| **T2** false convictions on set A's 36 genuine | 0 | **1 → 0** | **held** |
| **T3** convictions lost on the four high-rate arms | ≤ 2 | **0** | **held** |
| **T4** convictions lost on the low-rate arms | reported | **0** | — |
| **T5** convictions lost on set A's 252 lossy | ≤ 8 | **2** (one vorbis_q8, one opus_256) | **held** |

    high-rate arms, convictions before -> after
      mp3_320 17 -> 17    aac_ff256 26 -> 26    opus_256 13 -> 13    vorbis_q8 24 -> 24
    low-rate arms
      mp3_192 12 -> 12    aac_ff128 11 -> 11

    the witness itself, files where it testifies
      band-limited  27 -> 2      every arm unchanged except mp3_192, 32 -> 31

**The gate costs nothing and it was free to raise.** Not one conviction is lost
on any of the six arms, high or low rate, and the witness goes silent on exactly
the population it had no business testifying about. On set A the price is two
files out of 252 and the false conviction is gone.

## T1 failed, and the four survivors name the next defect

The band-limited controls move 15 → 4 convicted, and 13 of the rest land on
SUSPICIOUS rather than AUTHENTIC. **All four survivors carry the same pair, and
it is not the one this repair touched:**

    src056  cnn+spectral        src060  cnn+spectral
    src059  cnn+spectral        rh1982-10-18…  cnn+spectral

The CNN reads a spectrogram. On a file whose top octave has been removed, it is
reading the same roll-off Rule 1 is reading — so `cnn` and `spectral` are no more
independent here than `stereo` and `spectral` were. **The corroboration gate
counts families; it does not ask whether they are looking at the same thing.**

That was already named as the deeper fix in the two documents this one follows,
and it is now measured rather than suspected: closing the stereo path removed
eleven convictions and left four standing on the same mechanism, one family over.

## What ships and what does not

Ships: `MIN_CUTOFF_HZ = 12000 → 17000`, with the measurement in the comment.

Does not ship: any change to the corroboration gate. An independence guard
touches every rule pair in the engine, it needs its own registration and its own
priced corpus, and inventing it at the end of the same day that produced two
refused repairs is how the third one gets refused too.

**Standing statement for the next letter to Provir**, because he is the reason
this stratum exists: on this engine, band-limiting an honest file used to convict
it 15 times in 44, now convicts it 4, and the remaining four are the CNN and the
spectral rules reading one observation twice.
