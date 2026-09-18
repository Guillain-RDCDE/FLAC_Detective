# Reply posted on issue #10

Written 2026-09-18, for 1.13.17. No measurement behind this one: the engine
did what it was built to do and the wording let the reporter down (CHANGELOG
v1.13.17). Paragraphs are kept on one line each, as GitHub renders them.

---

Thanks for reporting this. Nothing is wrong on your end, and the checkbox works: the wording was the problem.

"Deep scan" was never an on/off switch for the CNN. Once the `[ml]` extra is installed, Rule 12 runs on every file the fast rules leave in doubt, box ticked or not. Files that look clean at once skip it, to keep a scan fast. Ticking "Deep scan" sends those through the CNN too, because that is where a high-bitrate AAC or Vorbis transcode hides. Slower, more thorough.

So what you saw is expected, and what you did (`pip uninstall torch torchaudio`) is the right way to scan with no CNN at all.

1.13.17 rewrites the tooltip, the `--deep` help and the user guide so they say this plainly. Thanks again for taking the time.
