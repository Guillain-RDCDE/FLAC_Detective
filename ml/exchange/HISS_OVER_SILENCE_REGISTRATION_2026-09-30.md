# Rule 11: no tape hiss over digital silence — registered 2026-09-30, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. The derivation below reads Rule 11 as shipped (1.19.0) on files
already traced by `fd-r1w/trace_r1.py`; no verdict has been computed with the
repair.

---

## Where this comes from

A controlled bench built on 2026-09-30: 33 CD tracks (a 2004 mixed hard-house
compilation and a CD single, third-party rips received that day, content
references only, **not** labelled genuine) encoded with ffmpeg 8.1
`libmp3lame` at CBR 128 and decoded back to FLAC 16/44.1. The transcode label
is by construction. 1.19.0 without torch let 3 of the 33 through as AUTHENTIC.
One of them reads, in the engine's own log:

```text
cutoff=16750 Hz, cutoff_std=0.0, edge_step_db=53.3, floor_above_db=-77.8
RULE 11A: Tape hiss detected (-52.3 dB, random)
CASSETTE DETECTED (evidence 30 >= 25). Disabling Rule 1 (MP3 Bitrate).
Final score: 0/150 - Verdict: AUTHENTIC
```

A 53 dB wall with digital silence above it, called a cassette.

## The mechanism: Rule 11A measures its own filter's leakage

Test 11A takes a 30 s segment, band-passes it from `cutoff + 500 Hz` (edges at
16 kHz and above) to 20 kHz with a 5th-order Butterworth, and calls
`20·log10(std) > −55 dB` with a random texture "tape hiss". The band starts
500 Hz above the wall, inside the filter's lower skirt. On a loud, dense master
the music just under the wall leaks through the skirt and is read as hiss.

Measured on that file, same segment, same band (17,250-20,000 Hz):

| reading | dB |
|---|---|
| 11A's filter reading | **−52.3** (over −55: "hiss") |
| true power in the band (Welch, 8,192 points) | **−98.4** |
| the same filter applied twice | −69.6 |

46 dB of the "hiss" is the music leaking through the skirt. A control file of
the same bench at 16,500 Hz reads −62.1 through the filter and −105.7 true:
same leakage, under the bar.

## The repair

**Tape hiss cannot sit over digital silence.** When the band above the edge is
digital silence by the engine's own depth instrument
(`floor_is_digital_silence(floor_above_db, cutoff)`: floor ≤ `DEEP_FLOOR_DB` =
−58 dB, edge under 19,500 Hz, the reading that already overrides gates A and D
and the container window), 11A does not credit hiss, and says so in `why:`.
Hiss is broadband: a cassette transfer keeps a noise floor above any edge its
chain has, it cannot leave silence there. Shallow or unknown floor: 11A decides
exactly as in 1.19.0. Nothing else in Rule 11 changes.

Refused on the same derivation: judging 11A by the true band power instead of
the filter (hiss only if the Welch power is also over −55 dB). Of the 22 files
that collect the cassette protection today across the traced populations, 13
would lose it, 78 rpm transfers with low edges among them. Their filter reading
is leakage too, but they are the files the protection exists for. Reworking
11A's instrument is a separate registration, not this one.

## Derivation

Rule 11 only runs under a 19 kHz cutoff, and the guard only acts where the
floor above the edge is ≤ −58 dB. Every file of the three traces
(`trace_gen.csv` 4,251 full-length tracks, `trace_60s.csv` 1,019 excerpts,
`trace_attr.csv` 84 attested-CD transcodes) meeting both conditions was run
through Rule 11 as shipped:

| population | files the guard can touch | cassette gate fires today |
|---|---|---|
| audit arms (mp3_128/192/320/V2, aac_ff128, aacmf_256; 60 s) | 113 | 0 |
| attested-CD transcodes (LAME 128/192/256) | 53 | 0 |
| halves, `long_mp3` | 39 | 0 |
| library sample (unlabelled) | 6 | 0 |
| Awesome Tapes From Africa (unlabelled) | 14 | **1** |
| any labelled genuine population | **0** | 0 |
| **total** | **225** | **1** |

The one file: Teno Afrika & Don Diego, *Sk love* (ATFA), a 16,000 Hz edge over
a −61.6 dB floor. The same artist's other traced tracks read hard walls at
17,500-18,750 Hz (steps 37-46 dB). It is named here before any verdict is
computed.

No labelled genuine file has a floor this deep under 19.5 kHz — the DEPTH_GATE
registration measured 0 of 155, and these traces agree — so the guard cannot
reach one.

## Criteria, registered before the passes run

Before = 1.19.0 (worktree at `9ef8d61`); after = the same plus this repair
only. `ml/bench_run_analyzer.py`: `FLACAnalyzer.analyze_file`, torch live,
default mode, `--sample-duration 30`, 2 workers.

Corpora: audit authentic (80), v2 genuine (59 as traced, 56 after the
2026-09-27 correction), attested CDs (28), full-length genuine (12), received
(17), wild (148); the 225 files of the table; the 22 full-length files
(`trace_gen.csv`, cutoff under 19 kHz) the cassette gate protects today; the bench's 35 CD tracks and its 165 transcodes (33 × mp3_128,
mp3_320, full-band VBR `-q:a 0`, aac 256, vorbis q6).

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **H1** | labelled genuine: verdict or score moves | **0** | any |
| **H2** | the 21 other full-length files the cassette gate protects today: verdict or score moves | **0** | any |
| **H3** | the bench's cassette-protected mp3_128 transcode | leaves AUTHENTIC | stays AUTHENTIC |
| **H4** | unlabelled files that move | *Sk love* only, toward accusation | any other |
| **H5** | transcodes that lose a detection | **0** | any |
| **H6** | every other file: verdict or score moves | **0** | any |

H1, H2, H5 or H6 failing refuses the repair. The bench's own detection counts
with torch live are reported as measured; the torch-less counts above are
superseded by them.

---

## RESULTS — 2026-09-30, after both passes (appended; everything above is as committed in `5a851b8`)

785 files, each run before and after (one path sat in two lists), 0 errors.
Verdict or score moved on **2** files, both predicted by name.

| id | criterion | predicted | measured | |
|---|---|---|---|---|
| H1 | labelled genuine moved (audit 80, v2 56, attested 28, full-length 12, received 17, wild 144 = 337) | 0 | **0** | held |
| H2 | the 21 other files the cassette gate protects today | 0 | **0** | held |
| H3 | the bench's cassette-protected mp3_128 transcode | leaves AUTHENTIC | **AUTHENTIC 0 → FAKE_CERTAIN 96** | held |
| H4 | unlabelled movers | *Sk love* only | ***Sk love* only: AUTHENTIC 0 → SUSPICIOUS 73** | held |
| H5 | transcodes losing a detection | 0 | **0** | held |
| H6 | every other file | 0 | **0** | held |

*Sk love* now reads Rule 1's +50 on its depth (16,000 Hz edge over −62 dB,
the 160 kbps cell) and stops at SUSPICIOUS on one family. It is an unlabelled
file of a set sold as digitised tapes; the engine's reading is not a label.

The bench's detection counts, torch live, before → after (33 files per arm):

| arm | caught before | caught after |
|---|---|---|
| mp3_128 (CBR) | 32 | **33** (31 FAKE_CERTAIN, 2 WARNING) |
| mp3_320 (CBR) | 15 | 15 |
| full-band VBR (`-q:a 0`, no low-pass) | 0 | 0 |
| aac 256 (ffmpeg native) | 0 | 0 |
| vorbis q6 | 0 | 0 |

The two mp3_128 WARNINGs are the container-window misses, reached by the CNN
alone; the window repair that would have taken them further was refused on
its derivation (`WINDOW_GRID_REFUSED_2026-09-30.md`). The 0/33 on AAC 256,
Vorbis q6 and full-band VBR are the engine's limit on these loud masters with
the CNN live, reported as measured. The 35 CD sources and the two store files
stay AUTHENTIC 37/37.

Bench: `D:\fd-jamie-2026-09-30\hiss\` (`before.jsonl`, `after.jsonl`,
`cmp.py`, `cmp_results.txt`). Suite: 877 passed, 83 skipped.
