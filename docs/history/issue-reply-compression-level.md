# Reply posted on issue #8

Posted 2026-09-07, with 1.13.12 on PyPI. Archived here because the measurement
it quotes lives with the code (`tests/test_compression_level_independence.py`,
CHANGELOG v1.13.12). Paragraphs are kept on one line each, as GitHub renders
them.

---

Thanks for this — and for doing the L8 → L0 round-trip before reporting. That one line settles that it's on my side, and it saved me a morning.

You're right, and it's a bug I had already found and then never shipped. The engine was reading the size of the file and treating it as the bitrate of the audio. A FLAC at level 0 is 5 to 15 % bigger than the same audio at level 5, and one of the rules works in 50 kbps windows, so your track sat on an edge: outside it at 0–3, inside it at 4–8. Same audio, two answers.

The fix went into `main` on the 4th (issue #7 was the same fault seen from the WAV/ALAC side), and then I didn't tag it. PyPI stayed at 1.13.8, so your "latest version" box was ticked honestly and there was nothing to update to. Sorry about that.

1.13.12 is on PyPI now: `pip install -U flac-detective`. I checked it on 24 tracks at all nine levels: on 1.13.8, two of them changed verdict with the level, exactly your pattern; on 1.13.12, none do.

One thing I can't tell from here is which of your two numbers was the right one. The two tracks that flipped in my set were real MP3 transcodes that the low levels had been letting through. If you run 1.13.12 on your file and feel like saying what it reads now, I'd be curious — but either way it will read the same at every level.
