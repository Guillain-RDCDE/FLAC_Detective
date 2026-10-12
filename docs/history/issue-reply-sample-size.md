# Reply posted on issue #8, second round

Posted 2026-09-07, with 1.13.13 tagged. Archived here because the measurement
it rests on lives with the code
(`ml/exchange/SAMPLE_DURATION_MEASUREMENT_2026-09-07.md`, CHANGELOG
v1.13.13). Paragraphs are kept on one line each, as GitHub renders them.

---

Glad it holds. And thanks for asking the sample-size question, because the honest answer turned out to be: the tooltip was wrong.

I spent the afternoon measuring it. 120 s doesn't read the same audio more carefully, it reads different audio (the whole track instead of three 30 s slices), and on a track whose high-frequency edge sits near one of the MP3 signature cells, that alone can push the reading into the cell. That's what happened to yours. On 284 files with known provenance, 30 s vs 120 s moves about one verdict in forty, in both directions. So no ideal size: 30 s is the one every published number was measured at, and if a file flips when you change it, that tells you the reading is on a boundary, not that either length is right.

1.13.13 (on PyPI shortly) reworks the tooltip and help, and the GUI's Advanced panel now shows the "why" line, so a case like yours reads "MP3 bitrate signature +50, 1 evidence family: spectral" instead of just a number. Which is the truth of it: one reading, uncorroborated, on a master that's probably just low-passed around 19–20 kHz. The engine can't tell those apart from spectrum shape alone, and now it says so.

If you feel like it, the Advanced panel's Cutoff at 30 s and at 120 s on your track would be interesting to see. Either way, thank you for the time you've put into this.
