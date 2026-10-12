# Reply posted on issue #7 — third round

Posted 2026-09-04, correcting the reply posted earlier the same day. That one
claimed the property held; it did not, and the corpus measurement that would have
said so had not been run. Archived here because the corrections belong with the
code.

---

I owe you a correction, and it is not a small one. :)

The reply I posted this morning said the property held now. It did not. I had
tested it on a synthetic fixture I built myself and on nothing else, and then I
told you it was fixed. That is the same mistake as the first round wearing a
different hat — I built my own trap again, and this time I told you the way out
of it before checking.

So I went and did the thing I should have done before writing to you at all: ran
the engine over a real corpus, both containers, and counted.

## What that said

First, about the version you filed against, before any of my changes:

```
FLAC and WAV agree on 23 of 30 real files
```

Seven divergences, in both directions. Including this one, from bit-identical
samples:

```
fd-exchange-2026-08-0006   FLAC AUTHENTIC     0/150
                           WAV  FAKE_CERTAIN 105/150
```

Your report was about four times bigger than your report. You found it on four
files of yours; it was sitting on nearly a quarter of a 599-file corpus that has
been in this repository the whole time, unmeasured from this angle.

Second, about my morning fix. I had exempted FLAC files from the new measurement,
to keep a re-encode off the common path in a library sweep. That was a bad trade
and the word I used for the leftover risk — "narrow" — was wrong twice over. I
also told you Rule 1's windows were "~250 kbps wide". They overlap; what matters
is the distance between edges, and those sit **50 kbps apart**. Two rulers that
disagree by half a percent straddle an edge far more often than that framing
suggests:

```
on-disk size vs reference re-encode, 120 corpus files
  mean 0.63 %   p95 1.46 %   max 4.17 %
  pairs landing on opposite sides of a Rule 1 edge:  9/120  (7.5 %)
```

One of those nine reads 852.0 kbps on disk and 848.2 kbps re-encoded, sits 0.2 %
from the 850 boundary, and came back `AUTHENTIC 6/150` as FLAC and
`FAKE_CERTAIN 86/150` as WAV. My fix had moved the divergence, not removed it.

And a third thing, smaller but still wrong: I told you Rule 6's −30 protection
"is precisely what should have been shielding your FLAC". It would not have.
Rule 6 requires that no MP3 signature was detected, and Rule 1 runs before it and
had just detected one. Rule 5 needs > 1000 kbps and your file reads 819. The
variance defect I described is real; the connection I drew to your file, I
invented. I'm sorry — that is exactly the kind of tidy story that sounds like an
explanation and isn't.

## What the actual fix is

One ruler, for every container, FLAC included. The compression ratio is measured
by re-encoding the audio at one fixed setting, whatever it arrived in, so the
number describes the samples rather than the packaging.

I considered a tolerance band around the cell edges instead and the arithmetic
refused: at ±1.5 % the dead zone eats 42 % of a 50 kbps gap, and Rule 1 would go
quiet across most of its own range. The grid is finer than the measurement, so
the measurement has to become exact rather than the grid blurrier.

The obvious cost is that re-encoding every file doubled the analysis time of a
file that would otherwise take the fast path — 6 s to 14 s each on my labelled
set — and that file is most of anyone's library. So the measurement is skipped at
cutoffs where Rule 1 returns before it ever looks at the container: there the
ratio is consulted by nobody, and the rule answers the same for every container
regardless. That brings it to 8 s, and the agreement result is identical either
way.

That skip is a shortcut that would rot in silence if someone moved a threshold, so
it is pinned by a test that states the property rather than copying the numbers:
**where the gate refuses to measure, a container bitrate of 300 kbps and one of
1411 kbps must give byte-identical answers**, across the whole grid of cutoffs,
wander values and residual floors.

## Numbers, before and after

```
                                                    1.13.8    1.13.10
FLAC and WAV agree, 30 blind-corpus files            23/30      30/30
false positives, 59 genuine files, known labels       5/59       5/59
detections, 60 labelled transcodes                   22/60      22/60
verdicts changed across 119 labelled files                          0
seconds per file, labelled set                          6           8
```

Not one verdict moves across 119 files whose true codec arm is known. That is the
line I was most worried about — a container fix that quietly buys agreement by
accusing more things would be worse than the bug.

One blind-corpus FLAC does change, the 852.0/848.2 kbps file above, from
`AUTHENTIC 6` to `FAKE_CERTAIN 86`. It does not become guilty: the released engine
already convicted it in its WAV form, and an independent engine from a separate
project convicts it too on its own evidence. The fix deletes a contradiction
rather than inventing an accusation.

And a genuine loss, so you hear it from me: two of the seven divergences settle on
`AUTHENTIC` where that other engine convicts. Their WAV forms had been caught
before — by the uninformative-container bypass firing where it had no measurement
behind it. Being right for no reason isn't a detection worth defending, but two
catches are gone and I'd rather write that down than round it off.

## Two numbers that aren't about your bug

While I had ground truth loaded I measured the engine against it, and the result
is unchanged by this release in both directions:

```
5 of 59 genuine files accused   (two of them FAKE_CERTAIN, at 92 and 73 points)
22 of 60 transcodes caught
```

One genuine file in twelve accused, two with the verdict that is supposed to
require corroboration between independent evidence families. And a set drawn from
ten codec arms walks past this engine roughly two times in three. Neither figure
is caused by what you reported and neither is fixed here — folding that into a bug
fix would be how it quietly never gets measured again. But you are running this
thing over a real library on the strength of what it tells you, so you should have
both numbers, and now the README and changelog carry them too.

## Where this leaves us

1.13.10 is in `main`. Your four files should now give the same verdict in all four
containers, and I'd genuinely like to know whether they do — including if the
answer is that something you know to be genuine now gets accused. That is the
failure this could introduce and I have 119 files saying it doesn't; you have a
library, which is better evidence than I have.

Thank you for not letting the first answer stand. Twice now the thing that moved
this forward has been you going and running something rather than accepting a
plausible story, and the plausible stories were mine both times. :)
