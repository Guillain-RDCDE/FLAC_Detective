# Reply posted on issue #8, third round

Posted 2026-09-08, with 1.13.14 on PyPI. Archived here because the measurement
it rests on lives with the code
(`ml/exchange/R11D_REMOVAL_REGISTRATION_2026-09-08.md`, CHANGELOG v1.13.14),
and because it corrects the previous reply (`issue-reply-sample-size.md`),
which explained his file wrongly. Paragraphs are kept on one line each, as
GitHub renders them.

---

Thank you for those two. They show I was wrong about your file, and I'd rather say so plainly.

The cutoff is the same in both runs, 17.2 kHz. So the reading never moved, which was my whole explanation yesterday. What actually changed is in your per-rule lists: at 30 s there is an "R11D: natural cutoff variation (236 Hz, wow/flutter)" line, at 120 s there isn't. That test looked at whether the cutoff landed in different 250 Hz cells across the three windows, called two cells "tape flutter", and with the roll-off line above it that was enough to treat your file as a cassette transfer: −40, MP3 rule switched off, Authentic 0. At 120 s the windows overlap, the wander reads zero, the cassette protection lapses, and you get the Fake 63. A 250 Hz grid read three times a minute apart cannot hear wow and flutter, on any file. That test is gone in 1.13.14, and the Why line now names Rule 11 instead of "_calculator".

So what your file reads, honestly, is: a wall at 17.25 kHz where a 192 kbps MP3 leaves one, plus the stereo side channel dying above 10 kHz, which is a second, independent trace. Two signs, not one. I'm not telling you the file is a transcode; I have no way to know that from here, and you know where it came from. But the engine's reading at 30 s was an acquittal on a rule that measured nothing, and the reading at 120 s is the one it actually has.

If you're sure of the provenance (a rip you made yourself, a purchase from a lossless store), it would be worth a lot to me: a genuine file that carries both of those traces is exactly the kind of file this project lacks, and I'd want to look at it properly rather than argue with a screenshot.
