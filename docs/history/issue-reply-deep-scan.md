# Reply posted on issue #10

Posted 2026-09-18, with 1.13.17 tagged and verified installable from PyPI. No
measurement behind this one: the engine did what it was built to do and the
wording let the reporter down (CHANGELOG v1.13.17). Paragraphs are kept on one
line each, as GitHub renders them.

---

Hey, thanks for this! You did nothing wrong, and honestly neither did the checkbox. My wording did: it reads like an on/off switch, and it isn't one.

Here's how it really works. Once you install with `[ml]`, the CNN (Rule 12) is always on. It looks at every file the quick rules aren't sure about, whether the box is ticked or not. Files that look clean right away skip it, just to keep a scan fast. Ticking "Deep scan" sends those "clean-looking" files through the CNN as well, because that's exactly where a good AAC or Vorbis transcode can hide. So: slower, but more thorough.

That means what you saw is normal, and uninstalling torch like you did is the right way to scan with no CNN at all.

I've just released 1.13.17 with a tooltip, `--deep` help and user guide that finally say this clearly (`pip install -U flac-detective`). Thanks for taking the time to write, it made the tool a bit better :)
