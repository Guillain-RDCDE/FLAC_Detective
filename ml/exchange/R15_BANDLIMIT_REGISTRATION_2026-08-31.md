# Rule 15 reads the band limit, not the codec — registered before the repair

Written and committed **before `stereo_image.py` is touched and before the
before/after passes run**. The measurement that prompted it is already done and
is reported below as the motive, not as the result.

---

## What was measured, and it is the worst false-positive finding of the round

Set A was scored against its own key as the pre-registered diagnostic
(`V3_PREREGISTERED_2026-08-31.md`, criteria A-i to A-iii). **A-i failed: one of
our own 36 genuine files is convicted**, and four more are signalled. Four of
those five are the `band_limited_synthetic` sources — the stratum built because
it could not be found — and the convicted one carries **`spectral+stereo`**, two
evidence families, which is exactly what the corroboration gate asks for.

The first hypothesis was wrong and is recorded as wrong: a shellac 78 is not
near-mono. Those files read a side/mid energy ratio of 0.39 to 0.71, far above
`MONO_GATE`, because surface noise is uncorrelated between channels.

The mechanism is in one line of `stereo_image.side_dead_run`:

```python
dead = (mid_spec < UNION_DEAD) | (side_spec < UNION_DEAD)
```

A **union**. A bin counts as dead if *either* channel is below the bar — so on a
band-limited file the MID channel is dead above the roll-off, the whole top of
the band counts as dead, and the run length explodes. **The witness is reading
the missing top octave, which is the same thing Rule 1 is reading.** The two
"independent" families are one observation counted twice, and the corroboration
gate cannot tell.

## Measured on material that is NOT in the shipped set

44 parked sources (32 unused + 12 dropped as series duplicates), all
**AUTHENTIC** before anything is done to them. A 14 kHz roll-off is applied —
the same filter the stratum uses — **and nothing else**:

    verdicts before:  44 AUTHENTIC
    verdicts after :  22 AUTHENTIC, 15 FAKE_CERTAIN, 5 WARNING, 2 SUSPICIOUS
    two families or more: 31 of 44, of which spectral+stereo on 24
    side dead-run: median 3.50, max 13.09, against a bar of 2.0

**Band-limiting an honest file convicts it 15 times out of 44.** Not a
transcode, not a re-encode: a low-pass filter on a genuine master. That is the
population Provir named as the hardest false positives in this space, and it is
the population this engine convicts a third of.

## The repair

`side_dead_run` measures whether the side channel dies **where there is content
to have a stereo image of**. So the analysis is restricted to the bins where the
MID channel is alive:

* per frame, take the bins with `mid >= UNION_DEAD` — the bins that carry
  content at all;
* the dead-run is computed over the side channel **within those bins only**;
* if a frame has fewer than `MIN_ALIVE_BINS` live bins there is nothing to
  measure and the frame contributes nothing; if too few frames survive, the
  statistic **abstains** (NaN), exactly as it already does for a mono file.

The intent of the union is not lost: a codec that couples the side channel away
leaves mid alive and side dead, which still reads. What stops reading is a file
with no content up there at all, which was never evidence of anything.

## Criteria, registered before the passes

| # | criterion | bound |
|---|---|---|
| **F1** | convictions on the 44 band-limited genuine controls | **≤ 2**, from 15 |
| **F2** | false convictions on set A's own 36 genuine | **0**, from 1 |
| **F3** | convictions lost on set A's 252 lossy rows | **≤ 8** — the repair may cost some recall, and this is where it is priced |
| **F4** | the witness abstains rather than reads | the number of files where the statistic goes finite → NaN is **reported per population**, not bounded |

**F1 is the point of the repair. F3 is its price.** If F3 breaks, the honest
outcome is that the witness cannot be made band-limit-blind without losing
recall, and the alternative — an independence guard on the corroboration gate
instead of a fix to the witness — gets its own registration.

F2 is not a bound to be proud of on our own set; it is a floor. A set we built,
at a threshold we chose, must not convict its own genuine files.

Results appended below, dated after the fact.

---

# THE REPAIR ABOVE WAS REFUSED BEFORE IT SHIPPED — appended 2026-08-31

Written the same evening, after implementing the repair and checking it before
running the priced passes. **The diagnosis in the section above is wrong**, and
the check that refutes it took four minutes.

## What the repair predicted, and what the file said

The repair assumed the MID channel is dead above the roll-off, so that
restricting the statistic to live-MID bins would remove the artefact. Measured,
on the very files that provoked it:

    file                       live share of the 10 kHz-to-Nyquist band (MID)
    convicted 78, band-limited            0.88
    signalled 78, band-limited            0.94
    mp3_320 (real transcode)              0.84
    mp3_192 (real transcode)              0.69
    genuine, full band                    1.00

**The band-limited files have MORE live MID band than a real mp3_320.** The mid
channel is not dead up there at all — a shellac transfer's surface noise is loud
and broadband, and after `_restore` normalises every file to full scale it stays
above the bar even 60 dB down. Two versions of the guard were tried, one on a bin
count and one on a share of the band; the convicted file read 2.76 before, 2.09
under the first and 2.09 under the second, against a bar of 2.0. It never
crossed. **The change was reverted**, and the revert verified by reproducing the
original 2.76 exactly.

## The mechanism, corrected

Both channels are tested against the **same absolute bar**, and the side channel
sits 10 to 20 dB below the mid one in the top band on ordinary material. A
roll-off lowers both, but only the side channel falls under the bar — so the
statistic reads "the side channel died" when what happened is "the side channel
was always quieter and the roll-off finished the job".

The module's own history says the absolute threshold was known to be
level-sensitive and that the fix was to normalise every file. **Normalising the
whole file does not restore a band that a roll-off removed**, so the correction
that shipped then does not cover this case.

## What that changes about the finding, and what it does not

**Nothing about the finding.** 44 parked genuine sources, all AUTHENTIC, a
14 kHz roll-off and nothing else: **15 convicted, 22 signalled**, side dead-run
median 3.50 against a bar of 2.0. Band-limiting an honest file convicts it a
third of the time, and the second evidence family that permits those convictions
is this witness reading Rule 1's observation a second time. That measurement
stands and it is the deliverable.

**Everything about the repair.** F1 to F4 are withdrawn unmeasured, because the
change they were written for does not do what it was written to do. Redesigning
a calibrated witness — one whose absolute bar, mono gate and edge-run exclusions
each came from a measured failure — on the evening the defect was found, against
a corpus we built ourselves, is exactly the circularity this project exists to
avoid.

## What comes next, and it gets its own registration

Two candidate repairs, neither implemented here:

1. **A relative dead test.** A side bin counts as dead relative to the file's own
   side-channel level in the band it does have, rather than against a bar shared
   with the mid channel. Keeps the witness working on full-band transcodes,
   which is its documented domain (opus_256 92 %).
2. **A domain gate.** The witness abstains when the file's own cutoff is below
   the analysis band's top, on the same principle as `MONO_GATE`: no top octave,
   nothing to measure. Coarser, cheaper, and it costs recall on aggressively
   band-limited transcodes — which is where Rule 1 already convicts.

Both need a corpus that is not ours: the price is recall on real transcodes, and
we do not get to set that price on a set we built. **Provir's set B is the right
terrain**, and this is now on the list of things his half will measure.
