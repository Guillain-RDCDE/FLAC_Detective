# Reply posted on issue #7 — second round

Posted 2026-09-04, after the reporter came back with the `soundfile` output and
the 1.13.8 rerun. Archived here because the reasoning belongs with the code.

---

You were right and I was wrong, and I'm glad you pushed. :)

Your five lines killed my hypothesis stone dead — `PCM_16` across the board, same
frame count, same rate — and the clean-venv rerun on 1.13.8 killed my fallback
position too. That's two of my excuses gone in one comment. Thank you for taking
the trouble; a lot of people would have shrugged and closed the tab.

I reproduced it this morning. Bit-identical samples, four containers:

```
case.flac   WARNING    33/150   families: cnn, spectral, stereo, temporal
case.wav    AUTHENTIC   3/150   families: none
case.aiff   AUTHENTIC   3/150   families: none
case.m4a    WARNING    33/150   families: cnn, spectral, stereo, temporal
```

Same detected cutoff, 19,250 Hz, in all four. So there it is at last, in my own
hands rather than yours.

## What it actually was

Your structural instinct was pointing at the right half of the engine and the
wrong mechanism, and honestly the wrong mechanism was the more obvious guess.
It isn't the reader: ALAC gets decoded to a temp WAV by ffmpeg and then walks the
exact same path as everything else. But the thing you noticed — that ALAC sided
with FLAC — is the whole clue, and it's the observation that cracked this. Not
FLAC against the world. **Compressed against uncompressed.**

Three links in the chain, and it's the third one that stings.

**One.** Rule 1 reads a compression ratio as evidence: audio that squeezes down
to ~800 kbps has thrown information away somewhere. Reasonable. But the ratio was
computed from the size of the file on disk. So a FLAC reads ~819 kbps, a WAV and
an AIFF read 1411 kbps no matter what their samples hold, and an ALAC reads its
own codec's ratio. A fact about the packaging was being used as a fact about the
recording.

**Two.** At a 19,250 Hz cutoff the rule's 256 kbps cell expects 600–850 kbps. The
FLAC is inside that window. The WAV isn't, and the bypass that's supposed to
handle uninformative containers needs a residual floor at or below −55 dB — which
genuine material with an actual noise floor doesn't have. So Rule 1 speaks on the
compressed containers and stays silent on the uncompressed ones.

**Three, and this is the real defect.** There's a fast path that exits early on
`score < 10 and mp3_bitrate_detected is None`, and that exit returns AUTHENTIC
without running rules 7, 10, 12, 13, 14 or 15. On uncompressed input, that `None`
doesn't mean "Rule 1 looked and found nothing." It means "Rule 1 had nothing to
look at." The engine read an absent measurement as a negative result.

Which is to say: **your WAV was never cleared. It was never examined.** The
silence rule you saw voting on the FLAC didn't run on the WAV at all. Two of your
four files got a verdict, and two got waved through the door. I'd rather tell you
that plainly than dress it up.

## What's changed

The compression ratio is now measured by actually compressing the audio. Anything
that isn't already a FLAC gets re-encoded to FLAC at one fixed setting, and *that*
size is what the rule reads. All four containers now report 818.8 kbps for the
same samples, and the table above collapses to one row repeated four times —
same score, same verdict, same witnesses, same reason text.

And the fast path can no longer acquit on a measurement it didn't take. When the
container bitrate carries no compression information, the file gets the full rule
set instead of a free pass.

Two costs, and I'd rather you hear them from me than find them:

- Non-FLAC files are slower now. The re-encode is about 10 % of the analysis
  time here (9 seconds against ~100, on a 70-second fixture), and beyond that
  your WAVs and AIFFs will be slower simply because they're now running the rules
  they'd been skipping. That part is the point rather than a regression.
- One residual I haven't closed: a level-8 FLAC is ~1–2 % smaller than the
  reference encode, so a FLAC sitting within ~1.5 % of one of Rule 1's window
  edges could still land on the other side from its WAV twin. The windows are
  ~250 kbps wide, so it's a narrow band, but it isn't zero and I'm not going to
  pretend it is.

## The part I'm least proud of

The container-independence test I told you about last time? It already existed. It
was green through every single run of this. Its fixture was six seconds of quiet
tones, and every container took the fast path on it and agreed — because nothing
was ever consulted. It wasn't testing the property. It was measuring its own
silence, and reporting that as a pass. You warned me about exactly this shape of
mistake by implication when you asked for the fixtures to be checked, and I built
one anyway.

It now carries a second fixture calibrated onto the rules that actually hold the
dependency, runs in default mode as well as `--deep` (deep bypasses the fast path
by design, so a deep-only test can't see half of this), includes ALAC where ffmpeg
is around, and fails outright if the fixture ever stops discriminating — a test
that agrees because nothing ran is now a failing test. On the old code the new
assertions come back with exactly your pattern:
`{'FLAC': 'WARNING', 'WAV': 'AUTHENTIC', 'AIFF': 'AUTHENTIC', 'ALAC': 'WARNING'}`.

## One more thing, since I was in there

`calculate_bitrate_variance` divides the file size by ten, ten times, and takes
the standard deviation of ten identical numbers. It has returned 0.0 for every
file this tool has ever analysed. Rule 5 needs > 100 to fire and Rule 6 needs
> 50, so both have been unreachable end-to-end since they were written —
including Rule 6's −30 protection for authentic high-bitrate files, which is
precisely the thing that should have been shielding your FLAC. Their unit tests
pass because they hand the rule a variance directly and never ask whether one
could arrive. I'm not fixing that in this release: giving those two rules their
votes back moves verdicts across the whole corpus, and that deserves its own
measured release rather than being smuggled in behind a bug fix.

## Where this leaves us

It's in `main` as 1.13.9. If you have the appetite for one more run, I'd love to
know what your four files do now — and particularly whether anything in your
library *changes verdict* that you believe is genuine, because that's the failure
mode this fix could plausibly introduce and your ears are better placed than my
fixtures.

Either way: this one was yours. The ALAC observation is what turned it, and I'd
have kept looking at readers for another week without it. Thanks for the second
comment as much as the first. :)
