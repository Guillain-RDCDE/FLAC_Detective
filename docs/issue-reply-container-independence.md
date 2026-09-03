# Reply to post on issue #7

Thank you for this, and for saying up front that the write-up was AI-generated —
it saves everyone a guessing game, and the report itself is well built: a clear
property, a stated expectation, a reproduction, and hashes. That is more than
most bug reports carry.

Short version: **I could not reproduce it on the current version, and I think I
know what happened, because I reproduced it by accident first and the cause was
not the container.**

## What I did

I built the same audio into four containers and ran the current engine on all
four. First attempt: FLAC read WARNING, WAV/AIFF/ALAC read AUTHENTIC. Your bug,
apparently, on 1.13.8.

It was not. My FLAC was **24-bit** and my WAV and AIFF were **16-bit**. The
engine was reading genuinely different audio, and the difference in the report
was real — a spectral rule fired on one and not the other, and even the
independent witnesses read different frequencies (22,018 Hz against 20,134 Hz).

Rebuilt with the same 16-bit samples in all four containers, and verified equal
as the arrays `soundfile` returns rather than through a converter:

```
b.flac   AUTHENTIC  score=0  cutoff=20250  families=['stereo', 'temporal']
b.wav    AUTHENTIC  score=0  cutoff=20250  families=['stereo', 'temporal']
b.aiff   AUTHENTIC  score=0  cutoff=20250  families=['stereo', 'temporal']
b.m4a    AUTHENTIC  score=0  cutoff=20250  families=['stereo', 'temporal']
```

Identical verdict, identical score, identical cutoff, identical witnesses, down
to the same rule text. On 1.13.8 the property you are asking for holds.

## The part worth your attention

**`ffmpeg -f s16le | sha256sum` cannot tell a 24-bit file from its own 16-bit
truncation.** It converts to 16 bits before hashing, so if your WAV was made from
your FLAC — or both were made from a 24-bit master by a tool that truncated one
of them — the hashes match and the files are still different audio to anything
that reads them properly.

I am not asserting that is your case. I am saying it is the case I hit within an
hour of reading your report, using your verification method, and it produced
exactly the pattern you describe: the compressed containers behaving differently
from the uncompressed ones.

The check that separates the two, on your files:

```python
import soundfile as sf
for p in ["04.flac", "04.wav", "04.aiff", "04.m4a"]:
    i = sf.info(p)
    print(p, i.format, i.subtype, i.frames, i.samplerate)
```

If the `subtype` column is not identical across all four, that is the answer. If
it is identical and the verdicts still differ on 1.13.8, then it is a real
container dependency, I want to know, and I would ask for that output plus
`flac-detective --advanced` on the two disagreeing files.

## Also relevant: 1.9.0

You are four minor versions back, and quite a lot of the scoring changed in
between — the silence rule's activation window, a domain guard on band-limited
material, a corroboration barrier that now requires two independent evidence
families before any conviction, and an abstention verdict. The rule you saw
voting alone ("Issues: Silence: 1") could not produce a conviction on its own in
1.13.8; a single family is held below that bar by design now.

That is not me telling you to upgrade and go away. It is that a report against
1.9.0 and a fix in 1.13.8 are hard to talk about together, and I would rather
know what 1.13.8 does on your files.

## What I have changed regardless

Your second suggestion was the right one and it is in, independent of how your
case resolves: a container-independence test. Same samples written to FLAC, WAV
and AIFF, asserting identical verdict, identical score, identical cutoff and
identical evidence families — and asserting first that the fixtures really do
hold identical samples, compared as read, so the test cannot be fooled the way I
was. ALAC is left out only because `libsndfile` cannot write it and I did not
want a test that needs ffmpeg installed.

If your files do turn out to differ in bit depth, that is worth its own issue:
the engine is entitled to read 24-bit and 16-bit differently, but a user with an
album in four formats has every right to expect to be told which one they are
looking at, and today the report does not say.

Thanks again — this was a good use of my afternoon either way.
