# Does a longer sample make the verdict better? — measured 2026-09-07

Prompted by the second question on issue #8. The reporter had confirmed 1.13.12
fixes the compression-level fault, then noticed that the same track, one he
knows to be genuine, reads `Fake 63` with the GUI's Sample field at 120 s and
`Authentic 0` at 30 s, and asked whether there is an ideal sample size.

The tooltip said "Higher = slower but more robust". The CLI help said the same.
`docs/technical-details.md` printed a table giving 85 % accuracy at 15 s, 95 %
at 30 s and 98 % at 60 s. None of those three claims had ever been measured.
This document is the measurement, and the claims are withdrawn in the same
release.

---

## What the setting does

`analysis/spectrum.py::analyze_spectrum` cuts three windows out of the track,
centred at one quarter, one half and three quarters of its length, each
`sample_duration` seconds wide (one window, centred, for tracks of 90 s or
less). Each window is a single FFT; `detect_cutoff` reads an edge from it on a
250 Hz grid; the engine keeps the **lowest** of the three readings. At 120 s on
a track under six minutes the windows grow until they touch, so the engine is
reading the whole track in thirds, intro and fade-out included.

Every scoring threshold was tuned at 30 s. Every accuracy figure this project
has published was taken at 30 s.

## Engine, corpora, conditions

- Engine: `main` at `b891471` (1.13.12), ML rule absent (the `notorch` shim,
  which is what `pip install flac-detective` gives a user without the ML extra).
- The audit corpus (`C:\Users\loutr\audit_corpus\`, 60 s excerpts, provenance
  known): `authentic/` 80 CD rips, `fake/mp3_192/` 80, `fake/mp3_320/` 80,
  `fake/mp3_V0/` 80 (the last for the probe only).
- The compression-level bench from the first half of issue #8: 24 tracks of
  the labelled v2 exchange set at FLAC level 5 (short excerpts, 5 genuine, the
  rest transcodes across arms).
- Full-length tracks: `fd-pistes-completes/` 12 genuine album tracks and
  `fd-transcodes-complets/` 8 transcodes of four of them (320 kbps MP3 and
  Vorbis).
- Two passes of the CLI per corpus, `--sample-duration 30` and
  `--sample-duration 120`, everything else default. Verdict-by-verdict diff on
  the same files (`fd-issue8/dur/cmpdur.py`, `shifts.py`).

## Result 1 — 30 s against 120 s, verdict by verdict

| corpus | cutoff reading moved | verdict changed | direction |
|---|---|---|---|
| 80 genuine | 11 | 2 | one accused at 120 s (`AUTHENTIC 11` → `SUSPICIOUS 56`), one released (`WARNING 50` → `AUTHENTIC 0`) |
| 24 labelled, level 5 | 6 | 1 | a real MP3-320 transcode cleared at 30 s, caught at 120 s (`AUTHENTIC 2` → `WARNING 53`) |
| 160 MP3 transcodes (192 + 320) | 18 | 4 | three caught only at 120 s, one caught only at 30 s |
| 20 full-length tracks | 2 | 0 | — |

Across the 284 files with known provenance: **7 verdicts changed, 4 towards
accusation and 3 away from it**, about one file in forty. The reading moved by
one to seven 250 Hz cells, in both directions, on about one file in eight.

The genuine file accused at 120 s is the reporter's case exactly:
`045-08 DJ Katapila` reads 17,750 Hz at 30 s (`AUTHENTIC 11`) and 18,750 Hz
at 120 s, which is inside the 256 kbps signature cell, so Rule 1 adds its +50
and the file reads `SUSPICIOUS 56` on a single evidence family.

## Result 2 — why no aggregation fixes it

The obvious repairs were tried on paper before being rejected on numbers:
make the window width fixed and let the setting choose how many windows;
take the median of the windows instead of the minimum; refuse Rule 1 when the
windows disagree. The probe (`fd-issue8/dur/probe_corpus.py`) read every
file in twelve fixed 30 s windows and twelve fixed 10 s windows spread over
the track, and recorded the spread of the readings.

The spread does not separate the populations. Genuine and MP3-192 have the
same distribution (median 0 Hz, upper quartile 500–750 Hz, tails to 5 kHz):

| bar on the 10 s-window spread | genuine released | MP3-192 released | MP3-320 released |
|---|---|---|---|
| > 250 Hz | 8 of 16 candidates | 23 of 75 | 15 of 75 |
| > 1000 Hz | 5 of 16 | 13 of 75 | 11 of 75 |

Every bar that releases half the genuine files Rule 1 can accuse also releases
a fifth to a third of the true transcodes. The median of twelve windows lands
in an MP3 cell exactly as often as the minimum of three (genuine 17 vs 16 of
80; MP3-192 75 vs 75). The instability is in the audio, not in the estimator:
a track whose spectral edge sits near a cell boundary will cross it with any
change of which seconds are read, and no choice of seconds is more true than
another.

## What changes, and what does not

- The tooltip, the CLI help, the API docs, the user guide and the examples now
  say what the setting does and that 30 s is the calibrated reading. The
  accuracy-against-duration table is withdrawn with a note saying why.
- The GUI's advanced detail panel now leads with the same `Why:` line the
  text report has carried since 1.13.11 — which rule decided and on how many
  independent families. The reporter was looking at the GUI; the line that
  would have told him "1 evidence family: spectral" was only in the text
  report.
- **No scoring change.** Verdicts at the default are bit-for-bit those of
  1.13.12; the diff above is a property of the engine that is now documented,
  not a defect that was repaired. The honest limit stays what it was: on
  spectral geometry alone the engine cannot tell a master low-passed near
  19–20 kHz from a high-bitrate MP3, and a verdict that flips with the sample
  length is a reading on a cell boundary, to be read as such.

## Files

`C:\Users\loutr\fd-issue8\dur\` — `run2.cmd`, `run3.cmd` (the passes),
`auth_30/`, `auth_120/`, `mp3_30/`, `mp3_120/`, `v2L5_120/`, `long_30/`,
`long_120/` (reports), `probe_corpus.py` + `probe_audit.csv` (the windowing
probe), `probe_analysis.py` (its tables), `cmpdur.py`, `shifts.py`.
