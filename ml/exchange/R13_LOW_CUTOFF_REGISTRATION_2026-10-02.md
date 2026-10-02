# Rule 13 under 18 kHz: the cutoff gate removed — registered 2026-10-02, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. The derivation reads Rule 13 as shipped (1.20.0) on files already
traced; no verdict has been computed with the change.

---

## Where this comes from

Issue #12 (2026-10-02): a Bandcamp FLAC (The Enigma TNG, *Doomhammer 666k*,
2025, full-band to 21.5 kHz) encoded with `oggenc -q1` (Vorbis, ~80 kbps) and
decoded back to FLAC reads **AUTHENTIC 16** on 1.20.0, default and `--deep`,
with and without torch. Reproduced on the reporter's own two files.

On that file, every instrument this engine uses for a cutoff under 18 kHz
steps aside:

| reading | value | consequence |
|---|---|---|
| floor above the edge | −35.3 dB | not digital silence: Vorbis at `-q1` fills the band with noise, the depth instrument does not fire |
| cutoff wander | 471 Hz (16,750 / 16,750 / 17,750) | Rule 1 exits at gate A |
| CNN | p 0.016 (raw 0.083) | reads it as genuine (it reads 0.95-0.99 on the same setting over hard house) |
| Rule 13 | **not asked**: `MIN_CUTOFF_HZ` = 18,000 | — |
| Rule 13 if asked | **2.43**, Vorbis window | +25 |

Reproduced at scale on the bench of 2026-09-30 (33 loud CD tracks, ffmpeg
`libvorbis -q:a 1`): 1.20.0 catches 32 of 33 with torch, **23 of 33 without**.

`MIN_CUTOFF_HZ` was set on the argument that "below that the cheap spectral
rules are already informative". At `-q1` on dense material they are not.

## The change

`should_run_rule_13` stops reading the cutoff: Rule 13 is asked on every file
not already convicted, on the fast path and on the main path alike. Bars,
points and both hypotheses unchanged.

## Derivation (Rule 13 as shipped, full decode, every traced file under 18 kHz)

| population | files read | median | max | ≥ 2.0 |
|---|---|---|---|---|
| certified genuine under 18 kHz (`ml/recert_admission.csv`, not admitted) | 22 | 1.26 | **1.46** | 0 |
| labelled genuine under 18 kHz (audit, v2, wild traces) | 15 | — | **1.36** | 0 |
| Dust-to-Digital (78 rpm, cylinders; cutoffs down to 2 kHz) | 45 | 1.29 | 1.40 | 0 |
| Awesome Tapes From Africa (cassettes) | 29 | 1.25 | 1.43 | 0 |
| library sample | 52 | 1.26 | 2.06 | **1** |
| MP3 128-320 / V0 / V2 arms | 100 | 1.26 | 1.51 | 0 |
| bench Vorbis q1 | 33 | 2.50 | 4.34 | 26 |
| issue #12, transcode / original | 2 | — | 2.43 / 1.33 | 1 |

77 traced files were not on disk any more (transcode halves, attested-CD
transcodes, one v2 and one library file).

The one unlabelled file over 2.0, named before any verdict is computed: Red
Hot Chili Peppers, *Make you feel better* (*Stadium Arcadium*, 2006, CD 2),
2.06, Vorbis window, edge 17,500 Hz.

The bench's ten torch-less misses read Rule 13 at 1.48, 1.66 and **2.01-3.49**
on the other eight.

## Criteria, registered before the passes run

Before = 1.20.0 (`8a837f2`); after = the same plus this change only.
`FLACAnalyzer.analyze_file`, default mode, 30 s, **torch live and torch absent**
(the reporter's configuration is unknown, the engine must hold in both).

Corpora: all labelled genuine (audit 80, v2 56, attested 28, full-length 12,
received 17, wild 144); every unlabelled file under 18 kHz on disk; the issue's
two files; the bench's 33 Vorbis q1, 132 high-bitrate transcodes and 37 CD and
store files; a control of 100 unlabelled files at or over 18 kHz.

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **L1** | labelled genuine: verdict or score moves (both modes) | **0** | any |
| **L2** | issue #12 transcode | leaves AUTHENTIC in both modes | stays AUTHENTIC in either |
| **L3** | issue #12 original | AUTHENTIC 0, unchanged | any change |
| **L4** | bench Vorbis q1 caught, torch absent | 23 → **31** of 33 | under 28 |
| **L5** | bench Vorbis q1 caught, torch live | 32 → **33** | under 32 |
| **L6** | unlabelled files moved | the Red Hot Chili Peppers track only | any other |
| **L7** | detections lost | **0** | any |
| **L8** | the 100-file control and the 169 bench files over 18 kHz: any change | **0** | any |

L1, L3, L7 or L8 failing refuses the change; L2 failing means it does not fix
the issue and it is not shipped as a fix. Cost (Rule 13 on files under 18 kHz
that are not already convicted, about 4 s each) is measured and reported.
