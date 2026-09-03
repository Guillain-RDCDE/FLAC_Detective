# Reply posted on issue #7

Hi — thank you for this, genuinely.

And thank you for saying up front that the write-up came from an AI, and that you're happy to talk human to human. That's a rare and useful thing to put at the top of a bug report: it tells me exactly how much to trust each part, and it saves us both a round of guessing. The report itself is well built — a clear property, a stated expectation, a reproduction, hashes. That's more than most.

Here's what happened when I sat down with it, told in order, because the order is the interesting part.

**I reproduced your bug within the hour.** Built the same audio into four containers, ran the current engine: FLAC came back WARNING, WAV and AIFF and ALAC came back AUTHENTIC. There it was, exactly as you described.

**It wasn't the container.** My FLAC was 24-bit and my WAV and AIFF were 16-bit. The engine was reading genuinely different audio — a spectral rule fired on one and not the other, and even the passive witnesses read different frequencies, 22,018 Hz against 20,134. I'd built my own trap and walked into it.

Rebuilt with the same 16-bit samples in all four, verified as the arrays soundfile returns rather than through a converter:

```
b.flac   AUTHENTIC  score=0  cutoff=20250  families=['stereo','temporal']
b.wav    AUTHENTIC  score=0  cutoff=20250  families=['stereo','temporal']
b.aiff   AUTHENTIC  score=0  cutoff=20250  families=['stereo','temporal']
b.m4a    AUTHENTIC  score=0  cutoff=20250  families=['stereo','temporal']
```

Same verdict, same score, same cutoff, same witnesses, down to the same rule text. On the current version the property you're asking for holds.

**Now the bit I'd want to know if I were you.** `ffmpeg -f s16le | sha256sum` converts to 16 bits before it hashes. So it cannot tell a 24-bit file apart from its own 16-bit truncation — which is exactly the pair you get when the WAV was made from the FLAC, or when one tool in the chain truncated and another didn't. The hashes match and the audio is still different.

I'm not telling you that's your case. I'm telling you it's the case I hit, using your method, an hour after reading your report, and it produced your exact pattern: compressed containers behaving differently from uncompressed ones.

Three seconds to find out, on your files:

```python
import soundfile as sf
for p in ["04.flac", "04.wav", "04.aiff", "04.m4a"]:
    i = sf.info(p)
    print(p, i.format, i.subtype, i.frames, i.samplerate)
```

If `subtype` isn't identical across all four, that's your answer. If it IS identical and you still get different verdicts, then it's a real container dependency, I've missed it, and I'd want that output plus `--advanced` on the two files that disagree. I'd rather be wrong here than right.

One more thing that might matter: you're on 1.9.0, and a fair amount of the scoring changed since. In particular there's now a corroboration barrier — no conviction from a single evidence family. The lone silence rule you saw voting couldn't reach SUSPICIOUS on its own today. I'm not saying "upgrade and go away"; I'm saying a report against 1.9.0 and a fix in 1.13.8 are hard to discuss together, and I'd love to know what the current version does on your library.

**Two things changed here because of you.**

Your second suggestion was simply right, and it's in regardless of how your case resolves: a container-independence test. Same samples in FLAC, WAV and AIFF, asserting identical verdict, score, cutoff and evidence families — and asserting first that the fixtures really hold identical samples at identical bit depth, so the test can't be fooled the way I was.

And the report now carries a **Format** column with the sample rate and bit depth, next to the cutoff:

```
 Icon | Score   | Verdict         | Format    | Cutoff   | Bitrate  | File
 [!!] | 55/100  | SUSPICIOUS      | 44.1/24   | 18.2k    | 224k     | a.flac
 [!!] | 55/100  | SUSPICIOUS      | 44.1/16   | 18.2k    | 224k     | a.wav
```

That's the fix your issue really earned. The CSV carried that information and the HTML carried it; the text report — the one people actually read — didn't. If it had, you'd have spotted this yourself in three seconds and never needed to write to me. A verdict without the reading it came from is just an opinion, and mine was being one.

To be straight with you about where this leaves us: I haven't fixed your problem, because I was never able to see it. What I've done is make it visible and make sure it can't come back unnoticed. Run those five lines and tell me what you get — if the subtypes match, I'll dig further and I'll be glad you pushed.

Good luck with the library sweep. If you find more of these, please do send them — this one was worth the afternoon whichever way it lands.
