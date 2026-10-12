# Reply posted on issue #7 — fourth round

Posted 2026-09-05, after he confirmed the container property on his own files and
handed over a provenanced genuine master the engine calls SUSPICIOUS. Archived
here because the corrections and the measurements belong with the code.

---

Thank you for running it, and for the way you wrote that up. :)

Confirmed on your side, on your files, in four containers — that's the part I
couldn't do from here, and it closes the thing you originally reported. I'm glad
it's actually fixed rather than fixed-in-my-fixtures, which is what I told you
twice before and was wrong about twice before.

Now the two things in your message worth more than the confirmation.

## One correction, small but worth having

The 224k reading matching on FLAC and WAV doesn't confirm the one-ruler
measurement engaged, I'm afraid. That column is `estimate_mp3_bitrate(cutoff)` —
a pure function of the detected cutoff, nothing else. It would have matched across
your four containers before this fix too. Your real evidence is the one you led
with: identical verdict and identical score. That one is solid.

I mention it only because you might reach for that column as a diagnostic later,
and it can't carry that weight.

## Your genuine master, and what it exposed

This is the useful half of your message, and you rather understated it.

A file with the provenance you describe, coming back `SUSPICIOUS 58/100`, is worth
more to me than a hundred synthetic fixtures. And when I went looking at why, it
was not what either of us thought.

**It was never the silence rule.** `Issues: Silence: 1` is a run-level tally of
audio-quality observations across the whole scan — a long quiet stretch, clipping,
DC offset — and it contributes **nothing** to any score. It was printed four lines
above the verdict table with no label saying so. You read it as the motive; so did
I, in my own first analysis of your report. Two of the three rounds this issue ran
for were spent chasing a rule that had never been consulted about your file.

What actually decided is this:

```
cutoff 18,250 Hz  ->  Rule 1: container bitrate matches a 224 kbps MP3   +50
                      Rule 2: cutoff below the expected range             +8
                                                                        ----
                                                                          58
```

Both of those are the **same evidence family**. One reading — "the wall is low" —
scored twice. Your master is legitimately band-limited at 18.25 kHz, and the
engine has no way to tell that from a 224 kbps MP3 on spectral geometry alone.
That is the honest limit, and it is the exact shape of double-counting that got a
different rule deleted from this engine last year.

So, three changes, none of which move your verdict:

**The report now says which rule decided.** Under every flagged file:

```
 [!!] | 58/100 | SUSPICIOUS | 44.1/16 | 18.2k | 224k | 04.flac
      why: MP3 bitrate signature +50, cutoff below the expected range +8
           — 1 evidence family: spectral
```

You'd have seen "1 evidence family" and known in three seconds what took us two
rounds. The tally is now labelled *"Audio-quality notes across this run (these do
not affect any verdict)"*, which is what it always was.

**SUSPICIOUS now says what it rests on.** When one family is carrying the whole
accusation, the line reads *"Marks of a transcode, but from a single line of
evidence — not corroborated, worth a listen before you act"* instead of "Probable
transcoding". I checked whether it should simply refuse to fire without a second
source, and it can't: the corroborated-conviction bar and the SUSPICIOUS floor are
the same number, so requiring corroboration there doesn't tighten the tier, it
deletes it. There's now a test that fails if anyone tries.

Measured before changing the wording, on 59 known-genuine files and 120 known
transcodes: of the 30 transcodes that reach 55 points, **every single one carries
two to five independent families** and convicts outright. Of the three genuine
files that reach it, the one accused on a single family lands exactly where yours
does. On that sample, this tier's entire population was genuine. Your file is not
an outlier in it — it is the population.

## And something I found because of you, which I'm not fixing

While in there I checked a statistic two rules depend on. `calculate_bitrate_variance`
was computing each segment's size as `file_size / 10`, ten times, and returning the
standard deviation of ten identical numbers. **It has returned 0.0 for every file
this tool has ever analysed.** Rule 5 needs > 100 and Rule 6 needs > 50, so neither
has fired since the day they were written — and their unit tests passed the whole
time, because those tests hand the rule a variance and never ask whether one could
arrive.

I fixed the measurement. Then I wired it in, measured what happened, and **took it
back out**:

- Rule 5's threshold is 100 kbps. The real statistic, across 40 files, runs 15.1 to
  86.7. The bar sits above the range of the thing it measures — repairing the input
  doesn't wake the rule.
- Rule 6 does wake, and misfires. Its "has substantial high-frequency content" test
  is the bare constant `19000`, applied at every sample rate. On a 96 kHz file with
  a 31 kHz cutoff, Rule 2 penalises it for a cutoff *below* that rate's threshold
  while Rule 6 rewards it for the same cutoff being "high". Measured on one corpus
  file: `FAKE_CERTAIN 95` became `AUTHENTIC 0`, because the protection dropped the
  score under a fast path and seven later rules never ran at all.

Switching on two rules that have never once executed means switching on conditions
nobody has ever validated. So they keep abstaining — explicitly now, and the
function returns "not measured" rather than a fabricated zero, which is the thing
that let this hide for so long. A zero reads as "no variation whatsoever", which is
the *strongest* possible evidence of a constant-bitrate source. There's a test that
fails if someone re-wires it without fixing those thresholds first.

## Numbers

Nothing in this release moves a verdict. Across 179 files with known ground truth:
zero changes. The container property still holds 30/30 on the corpus. The accuracy
figures are unchanged and still what they are: 5 of 59 genuine files accused, 22 of
60 transcodes caught on the balanced sample.

That last pair is why I think your pipeline has it right. Spectral evidence plus
AcoustID identity plus duration, with Picard as the final gate, is a sane way to use
a triage signal — and treating these verdicts as anything stronger than triage is
not something the measurements support. I'd rather the tool said so out loud than
have you infer it from a base rate in a changelog, which is roughly what I asked you
to do last time.

## Where this leaves us

1.13.11 is in `main`. Your 04 and 06 will still read SUSPICIOUS 58 — the analysis
hasn't changed and I'm not going to quietly retune a threshold so your file passes.
But the report will now tell you it's one line of evidence rather than a
corroborated finding, which is the difference between an opinion and a claim.

If you're willing, I'd like to record that master in the project's adjudication
ledger as a documented genuine file — nothing identifying, just the provenance
basis (store purchase, four containers bit-identical after decode) and the
measurements. Files with real provenance that the engine gets wrong are the
scarcest thing this project has, and yours is the cleanest one anyone has handed
over. Entirely your call, and no hard feelings if you'd rather not.

Four rounds, and every one of them moved because you went and ran something instead
of accepting a plausible story. The plausible stories were mine every time. :)
