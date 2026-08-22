# ENCODER REGISTER — the emitter-coverage programme
Built 2026-08-12. Companion to `CLAIMS_REGISTER.md`: that one governs what we may *say*, this one
governs what we can *see*. An emitter we have never run is a blind spot we cannot price.

> ⛔ **THE BINDING CONSTRAINT IS n PER CELL, NOT BINARIES IN THE FOLDER.** The table is currently
> **71 cells / 18 emitters**, and most cells rest on ONE source. Adding 23 unmeasured encoders at
> n=1 produces a table that is wider and equally thin, and a hostile expert goes straight for the n.
> Every acquisition must arrive with the same source ladder or it is decoration.
> ✔ **RESOLVED 2026-08-12 — the "~350 cells" in memory is NOT SUPPORTED BY DISK.** Full count of
> every emitter ledger present:
> ```
> coupling_emitter_matrix.jsonl    71 cells / 18 emitters
> codec_emitter_matrix.csv         55 rows  / 26 emitters
>                                 126 total (emitter sets overlap)
> emitter_sweep.jsonl (NEW)       513 cells / 44 emitter-configs
> ```
> Pre-existing coverage was **126 cells across two files**, not ~350. Quote the measured counts;
> the memory figure has been corrected at source ([[encoder-emitter-landmarks]]).

> ⛔ **CRACKED SOFTWARE NEVER ENTERS THIS TABLE.** `era_encoders/mp3enc31full/` (Fraunhofer MP3Enc
> 3.1) ships with `fosi.nfo` — a scene release, hence the unpayable registration prompt (vendor page
> 404). A public emitter reference built with warez is a credibility problem for a project whose
> entire pitch is evidential discipline. EXCLUDED. The Fraunhofer lineage is reachable legitimately
> via `l3codeca.acm` — see gaps below.

---

## Source ladder (applies to EVERY cell)
Genre bias on HF statistics has been measured at **30x** ([[deadmax-solo-floor-is-genre-biased]]),
so a single source cannot characterise an emitter.

| tag | source | why |
|---|---|---|
| `elec` | Billy Kenny — Take Me to Church (BEATPORT_AIFF) | dense, loud, modern electronic |
| `class` | Air on a G String (Classical Album 2006, CD2/15) | sparse, quiet, FULL-BAND to Nyquist, flat HF floor — the hard case |
| `pop95` | M People — And Finally… (Bizarre Fruit) | mid-90s pop, 13.2 dB/kHz razor **already on record** = built-in instrument cross-check |

---

## OWNED — measured (in the table today)

| emitter | family | cells | note |
|---|---|---|---|
| LAME 3.90.3 / 3.92 / 3.93.1r / 3.96.1 / 3.98.4 / 3.99.5 / 3.100.1 / daily-20020930 / wb-3.97 | MP3 | 27 | 9 builds x 3 — the deepest ladder we own |
| ffmpeg / MediaFoundation | MP3+AAC | 16 | system path |
| Apple qaac / CoreAudio | AAC | 10 | |
| iTunes | MP3 | 6 | |
| Nero 1.3.3 / 1.5.4 / nero_aac | AAC | 6 | |
| FAAC | AAC | 2 | |
| Helix | MP3 | 2 | |
| BladeEnc 0.94.2 | MP3 (ISO dist10) | 2 | |
| **BladeEnc 0.91 / 0.94.2** | MP3 (ISO dist10) | +6 | **added 2026-08-12**, `_era_mp3/era_razor.jsonl`, n=1 (`pop95`) |
| **Fraunhofer MP3enc 3.0 demo / 3.1 demo** | MP3 (FhG) | measuring 2026-08-21 evening | OFFICIAL demo builds (30-s encode limit), `era_encoders/fhg_mp3enc3{0,1}_demo/`, identity in `FHG_DEMO_BUILD_IDENTITY.md`; adapter `_fhg` (short-path bit-exact 30-s input; rate measured on the encoded duration). NOT the excluded scene copy. |

## ⛔⭐ FIRST SWEEP RESULT (2026-08-12) — TWO AXES MEASURED BLIND TO THE ISO LINEAGE

396 cells, 387 OK, single failure = `nero_aac/NAACEnc` ("Invalid VBR/CBR mode", adapter owed).
Ledger: `_emitter_sweep/emitter_sweep.jsonl`. Rate-honoured check passes on every OK cell.

**Razor slope (dB/kHz), by family — recorded codec band is 23-54:**

| family | n | min | median | max |
|---|---|---|---|---|
| mp3-iso (BladeEnc) | 36 | **-0.6** | **12.8** | 31.0 |
| mp3-lame | 99 | 4.6 | 32.6 | 54.5 |
| mp3-helix | 18 | 18.7 | 32.4 | 49.1 |
| aac-nero | 81 | -0.1 | 28.1 | 44.3 |
| aac-faac | 9 | 12.4 | 31.2 | 44.9 |
| opus | 72 | 24.4 | 35.3 | 58.4 |
| vorbis | 63 | -6.3 | 26.6 | 64.2 |
| xhe-aac | 9 | 19.8 | 27.8 | 41.9 |

⛔ **THE 23-54 BAND DOES NOT HOLD.** Measured range across eight families is **-6.3 to 64.2**.
The constant was fitted on a narrower emitter set. Do not quote 23-54 without this caveat.

⛔ **NOT A GENRE EFFECT — the 3-source ladder rules it out.** Per-source medians over ALL emitters
are flat: elec 29.8 / class 31.2 / pop95 29.0. The spread is by EMITTER, not content.

⛔⭐ **BladeEnc (ISO dist10 lineage) IS INVISIBLE ON BOTH PRIMARY MP3 AXES:**

| | class | elec | pop95 |
|---|---|---|---|
| razor slope, mp3-iso | **0.2** | 12.2 | 23.9 |
| razor slope, every other family, same source | 23.6 - 43.9 | — | — |

| lattice (alias=dec) | untouched source | blade 128 | blade 320 |
|---|---|---|---|
| class | 0.0455 (1/22) | 0.0500 | **0.0455 — identical to the null** |
| elec | 0.1364 (3/22) | 0.0909 (below null) | **0.1364 — identical to the null** |

⛔ **CAUSE CORRECTED 2026-08-13 — IT IS OUR GRID, NOT THE ENCODER.** This entry previously read
"BladeEnc *does not lowpass* … the lattice is specifically deaf to this encoder". That is REFUTED.
Re-swept at **all 576 offsets**, three of the four cells lift clear of the lawful max (0.1364):
```
                     shipped grid        all-576 sweep
blade 128 class      0.0500        ->    0.2222
blade 320 class      0.0455        ->    0.2273     (was "identical to the null")
blade 128 elec       0.0909        ->    0.3810     (was "below null")
```
Real mechanism: the shipped sweep `np.arange(0,576,8)` has residues {0,8,16,24} mod 32, so it tests
**4 of the 32 PQMF polyphase phases**. BladeEnc writes no Info/LAME tag (byte-verified), so ffmpeg
cannot trim its encoder delay; the decode lands at 1057 mod 32 = **phase 1**, which is not in the
shipped set. Proven causally in both directions: shifting a BladeEnc decode onto a tested phase
takes L **0.091 → 0.444**, and shifting a LAME decode onto phase 31 takes L **0.500 → 0.136**;
untouched controls do not move.
⇒ The statistic sees BladeEnc. **The shipped offset grid does not.** Those are different claims and
only the second one is true.
⚠ Widening the grid globally is priced NEGATIVE (23.7% → 23.0% at matched FP for 8× compute), so
this is NOT an argument for res256 everywhere. The live idea it does license: sweep all offsets
**only where the delay cannot be trimmed** (no Info/LAME tag) — a small, identifiable population.
UNMEASURED as a targeted rule.
⚠ **LIMIT OF THE CLAIM:** two axes tested, NOT the stack. dead_max, Delta, the stereo specialist and
the cliff rungs are UNTESTED against BladeEnc and any may catch it. This is "two axes blind", never
"undetectable". **OWED: run the full bench over the 36 BladeEnc encodes already in
`_emitter_sweep/work/`** — they are encoded and waiting; the test costs one scan.
⚠ Bears on the [[codec-family-matrix]] 84-97% claim: if the stack also misses it, the ISO lineage
must be a STATED EXCLUSION on that claim.

⛔ **HARNESS DEFECT FOUND AND FIXED — the first ledger was discarded.** The sweep was launched twice;
both processes appended to one ledger and raced on one work directory (736 rows for 387 keys, 26
"Permission denied", "moov atom not found" truncations, and **102 duplicated keys returning
DIFFERENT slope values** — plausible numbers measured on partially-written files, reported as OK).
Archived to `_emitter_sweep/_contaminated/` as a worked example of what a race looks like here.
Fix: single-instance lockfile in `sweep_owned.py`, break-tested (a second instance refuses to start).
⚠ Every Nero/exhale/opus "failure" in that run was the race, NOT the encoder — all pass clean.

## ⭐ FULL-COVERAGE SWEEP (2026-08-12, after all four adapters were fixed)

**513 cells, 501 OK, 12 failed — and both failure classes are CORRECT OUTCOMES, not adapter debt:**
`exhale` RATE_UNSUPPORTED x3 (preset ladder ends at 9 ~= 192 kbps; 320 does not exist, so it is
recorded as absent rather than silently produced at another rate) and `NAACEnc` ADAPTER_FAILED x9
(Nero Burning ROM 6 codec DLLs absent — adversarially confirmed as a real blocker, do not table as
measured). No FLAG_IGNORED: no encoder reported discarding a flag.

⛔ **FOUR ADAPTERS WERE WRONG AND THEIR CELLS WERE MISLABELLED** (all confirmed by an independent
adversarial pass):
| family | defect | effect |
|---|---|---|
| nero | `-br` is **ABR**, not CBR (`-cbr` is CBR) | 81 cells were ABR labelled CBR |
| opus | opusenc's **default is VBR**; needs `--hard-cbr` | 72 cells were VBR labelled CBR |
| vorbis | `-b` without `--managed` is **advisory** | 63 cells were nominal-hint VBR |
| exhale | preset != bitrate; the map was invented | wrong presets; 320 does not exist |
⇒ Fixing them MOVED A RESULT, not just a status: **vorbis median razor 26.6 -> 17.0 dB/kHz**,
crossing from inside the codec band to BELOW the genuine-master reference.
⚠ `--managed` is NOT universally effective: on `oggenc_gt3b1` it is measurably INERT at 192k on some
content (worst rate error 3.44%). Those cells are approximate and labelled so.
⚠ Duplicate emitters, proved by hashing DECODED PAYLOAD (not containers): `nero_1_5_1 == nero_1_5_4`,
`vorb_oggenc111 == vorb_112`. Both kept deliberately as a standing reproducibility control.

⛔⭐ **THE RAZOR AXIS ALONE IS WEAK — RE-PRICED 2026-08-12 AGAINST A REAL LAWFUL POPULATION.**
An earlier version of this section said "misses 23.0% of known-lossy encodes (115/501 cells below
19.8 dB/kHz)". The 19.8 threshold was **n=1** (see `_genuine_razor/`); the honest version prices
recall against measured lawful FP, n=200 lawful vs 501 known-lossy cells:

| threshold | lawful FP | lossy caught | lossy MISSED |
|---|---|---|---|
| >=20 dB/kHz | 6.0% | 77.0% | 23.0% |
| >=30 | 1.0% | 45.5% | 54.5% |
| >=35 | 0.5% | 26.1% | 73.9% |
| **>=40** | **0.0%** | **15.0%** | **85.0%** |

⇒ At an operating point with NO false convictions the razor catches **15%**. The old "23%" was
numerically right only at a threshold costing 6% lawful FP — unusable under Rule #1.
Recall at the zero-FP point, by family: opus 31.9% · mp3-helix 16.7% · xhe-aac 16.7% ·
mp3-lame 14.1% · aac-faac 11.1% · aac-nero-old 11.1% · aac-nero 5.6% · vorbis 1.6% ·
**mp3-iso 0/36 (0.0%) — BladeEnc reads zero at EVERY usable threshold.**

Retained for reference, the raw below-19.8 counts that first exposed the blind spot:

| family | invisible | note |
|---|---|---|
| mp3-iso (BladeEnc) | **24/36 (67%)** | 12/12 on class AND elec; 0/12 on pop95 |
| vorbis | **35/63 (56%)** | same content gradient |
| aac-nero-old | 12/36 (33%) | |
| aac-nero | 27/90 (30%) | |
| mp3-lame | 13/99 (13%) | |
| mp3-helix | 1/18 (6%) | |
| opus | **0/144 (0%)** | every cell caught |
| xhe-aac | 0/6 (0%) | |

⚠⚠ **TWO CAVEATS WITHOUT WHICH 23% IS MISLEADING — never quote it bare:**
1. **UNWEIGHTED CELL COUNT OVER AN ARTIFICIAL EMITTER MIX.** 144 opus cells vs 6 xhe-aac reflects
   what we happen to OWN, not wild prevalence. Weighted by [[wild-mp3-encoder-census]] (83% LAME),
   real exposure is far lower — LAME is only 13% invisible. The blind spot is REAL but concentrated
   in MINORITY lineages.
2. **ONE AXIS, NOT THE STACK.** dead_max, Delta, the stereo specialist and the cliff rungs are
   untested against these. `bench_bladeenc.py` is the first proper answer for the ISO lineage and
   the same test is now OWED for Vorbis.
⚠ The 19.8 dB/kHz genuine-master reference is itself a single inherited constant; it needs its own
provenance check before anything above is quoted.

⭐ Content gradient is consistent across families: sparse/quiet material hides lossy damage from a
BANDWIDTH statistic, because there was little HF to remove. This is why the 3-source ladder exists.

## ~~OWNED — never measured~~ ✔ CLEARED 2026-08-12 (kept for the record)

Every row below was measured in the full-coverage sweep the same day — Opus (8 builds x 2 configs),
Vorbis (7), the remaining BladeEncs, Nero 1.1.34.2 + SSE, exhale, and the LAME variants. See the
FULL-COVERAGE SWEEP section above for the resulting table.

| emitter | family | builds | status |
|---|---|---|---|
| Opus | Opus | 8 (0.1.2 → 1.6.1) | ✔ measured — 144 cells (hard-CBR + default-VBR as separate emitter cells) |
| Vorbis / aoTuV / GT3b1 | Vorbis | 7 | ✔ measured — 63 cells; ⚠ `--managed` INERT on `oggenc_gt3b1` at 192k |
| BladeEnc 0.92.7 / 0.94 | MP3 (ISO dist10) | 2 | ✔ measured — the family that broke both spectral axes |
| Nero 1.1.34.2 (+SSE) | AAC | 2 | ✔ measured (CBR + ABR cells) |
| exhale | xHE-AAC | 1 | ✔ measured at 128/192; **320 RATE_UNSUPPORTED** — preset ladder ends at 9 |
| LAME 3.90.3mod / 3.93.1w32 | MP3 | 2 | ✔ measured |
| CDex 1.51 | MP3 (bundles LAME) | 1 | ⛔ CONFIRMED an INSTALLER, not an encoder — excluded from discovery, not counted as coverage |

✔ **RESOLVED:** `nero_1_0_0_2` and `nero_1_0_7_0` DO contain binaries — nested deeper than the
original depth-3 search reached (`<dir>/NeroAACCodec-x.x.x.x/win32/neroAacEnc.exe`). They now
measure clean as `aac-nero-old` (36 cells). The earlier "no binary found" note was a search-depth
artefact, not an absence — the same class of error as reading a path as provenance.
⚠ Still unresolved: `lame3.93.1`, `wb_lame3.90.3`, `wb_lame3.92` — no binary located at any depth.

## LAME 3.94 beta 1 / 3.95 / 4.0 — BUILT HERE 2026-08-21 evening, 27 cells, all OK (rates honoured)

Three rungs the ladder lacked, built from source (identity + deviations in
`era_encoders/FHG_DEMO_BUILD_IDENTITY.md`; the source trees are gitignored, the binaries ignored by policy):
- **3.94b ≡ 3.95 BYTE-FOR-BYTE on every cell** (edge/slope/stopband identical across 27 values) — the
  beta and the release share one encoder core; differences are frontend-only. Kept as a standing
  reproducibility control, like `nero_1_5_1 == nero_1_5_4`.
- **LAME 4.0 (2026-07-11)** reads as 3.100's generation on the idem era bench (Δ 0.000 vs the
  ffmpeg-3.100 V0 reference, 41/72 @1%) — the release notes' "housekeeping only" is MEASURED true.
  Register cells: 128k edge ~16.3–16.5 kHz, 192k ~18.5–18.7 kHz, 320k ~19.9–20.2 kHz, razor 26.6–46.3.
- 3.94b/3.95 cells: 128k ~17.0–17.2 kHz, 192k 17.6–18.7 kHz, 320k 18.6–20.0 kHz — the 2003 presets'
  bandwidth table; on the V0 era bench these two are THE KNEE (19/72 @1%; 3.93.1 is dead, 3.96.1 23/72).
⚠ The sweep's recursive discovery measured `lame4.0_src/.../output/lame.exe` as a second emitter
(same binary); those 9 duplicate rows were removed and the source tree added to SKIP.

## ⭐⭐ LAME ARCHIVE SET — 34 rungs banked 2026-08-21 19:10 ("I went ham"), 29 runnable, 261 new cells — THE LOWPASS LADDER ACROSS THE WHOLE LINEAGE

Owner pulled the public LAME binary archive (3.20 → 3.93.1); identities in `era_encoders/ERA_BUILD_IDENTITY_lame_archive.md`.
Every runnable build went through the same 3-source × 3-rate ladder. Table GENERATED from the ledger by
`_emitter_sweep/archive_rung_table.py` (median edge [min–max] and median slope across the three sources; snapshot 2026-08-21 21:06):

| rung | 128k edge kHz (slope dB/kHz) | 192k edge kHz (slope dB/kHz) | 320k edge kHz (slope dB/kHz) | cells |
|---|---|---|---|---|
| lame3.20 | 16.0 [16.0–16.0] (28) | 20.0 [19.4–22.1] (8) | 20.0 [20.0–22.1] (5) | OK×9 |
| lame3.24b | 16.0 [16.0–16.0] (29) | 20.0 [19.5–22.1] (9) | 20.0 [20.0–22.1] (5) | OK×9 |
| lame3.29b | — | — | — | ERROR×9 |
| lame3.30b | 16.0 [15.7–16.0] (31) | 20.0 [19.5–22.1] (10) | 21.4 [20.1–22.1] (19) | OK×9 |
| lame3.34b | 16.0 [15.7–16.0] (32) | 20.0 [19.5–22.1] (9) | 21.4 [20.1–22.1] (19) | OK×9 |
| lame3.35b | — | — | — | ERROR×9 |
| lame3.50 | 16.0 [15.7–16.0] (32) | 20.0 [19.5–22.1] (9) | 21.4 [20.1–22.1] (19) | OK×9 |
| lame3.55b | 16.0 [14.7–16.0] (26) | 20.0 [19.5–22.1] (8) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.56b | 16.0 [14.7–16.0] (25) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.57b | 16.0 [14.7–16.0] (25) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.58b | 16.0 [15.7–16.0] (32) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.59b | 16.0 [16.0–16.0] (34) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.60b | 16.0 [16.0–16.0] (31) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.61b | 16.0 [16.0–16.0] (31) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.62b | 16.0 [15.7–16.0] (31) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.63b | 16.0 [15.7–16.0] (31) | 20.0 [19.4–22.1] (9) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.65b | 15.3 [14.9–15.3] (30) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.66b | 15.3 [14.9–15.3] (30) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.67b | 15.2 [14.2–15.3] (28) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.68b | 15.3 [15.1–15.3] (28) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.69b | 15.3 [15.1–15.3] (28) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.70 | 15.3 [15.1–15.3] (28) | 20.0 [19.4–20.8] (34) | 21.4 [20.1–22.1] (18) | OK×9 |
| lame3.80b | 15.3 [15.1–15.3] (30) | 20.0 [19.4–20.8] (37) | 21.4 [20.1–22.1] (16) | OK×9 |
| lame3.82b | 15.3 [15.1–15.3] (30) | 20.0 [19.5–20.8] (36) | 21.4 [20.1–22.1] (14) | OK×9 |
| lame3.83b | — | — | — | ERROR×9 |
| lame3.85b | 15.3 [15.1–15.3] (28) | 20.0 [19.5–20.8] (34) | 21.4 [20.1–22.1] (15) | OK×9 |
| lame3.86b | — | — | — | ERROR×9 |
| lame3.87a | 15.3 [15.1–15.3] (28) | 20.0 [19.5–20.8] (34) | 21.4 [20.1–22.1] (15) | OK×9 |
| lame3.88b | 15.3 [15.2–15.3] (32) | 19.2 [19.1–19.4] (35) | 21.4 [20.1–22.1] (14) | OK×9 |
| lame3.89b | 15.3 [15.2–15.3] (32) | 18.6 [18.5–18.8] (36) | 20.5 [20.1–21.5] (19) | OK×9 |
| lame3.90 | 15.3 [15.2–15.3] (31) | 18.6 [18.5–18.8] (35) | 20.5 [20.1–21.5] (20) | OK×9 |
| lame3.90.1 | 15.3 [15.2–15.3] (31) | 18.6 [18.5–18.8] (35) | 20.5 [20.1–21.5] (20) | OK×9 |
| lame3.90.3 | 15.3 [15.2–15.3] (31) | 18.6 [18.5–18.8] (35) | 20.5 [20.1–21.5] (20) | OK×9 |
| lame3.90.3mod | 15.3 [15.2–15.3] (31) | 18.6 [18.5–18.8] (35) | 20.5 [20.1–21.5] (20) | OK×9 |
| lame3.91 | 15.3 [15.2–15.3] (31) | 18.6 [18.5–18.8] (35) | 20.5 [20.1–21.5] (20) | OK×9 |
| lame3.92 | 15.3 [15.2–15.3] (27) | 18.6 [18.5–18.8] (31) | 20.1 [20.1–21.5] (17) | OK×9 |
| lame3.93 | 15.3 [15.2–15.3] (27) | 18.6 [18.5–18.8] (31) | 20.5 [20.1–21.5] (22) | OK×9 |
| lame3.93.1r | 15.3 [15.2–15.3] (26) | 18.6 [18.5–18.8] (31) | 20.5 [20.1–21.5] (22) | OK×9 |
| lame3.93.1w32 | 15.3 [15.2–15.3] (26) | 18.6 [18.5–18.8] (33) | 20.5 [20.1–21.5] (22) | OK×9 |
| lame3.94b | 17.0 [17.0–17.2] (31) | 18.5 [17.6–18.7] (40) | 19.0 [18.6–20.0] (12) | OK×9 |
| lame3.95 | 17.0 [17.0–17.2] (31) | 18.5 [17.6–18.7] (40) | 19.0 [18.6–20.0] (12) | OK×9 |
| lame3.96 | 17.0 [17.0–17.2] (33) | 18.5 [17.4–18.7] (38) | 18.6 [18.1–19.0] (12) | OK×9 |
| lame3.96.1 | 17.0 [17.0–17.2] (33) | 18.5 [17.4–18.7] (38) | 18.6 [18.1–19.0] (12) | OK×9 |
| lame3.97 | — | — | — | ERROR×9 |
| lame3.97_mingw64 | 16.5 [16.4–16.5] (31) | 18.6 [18.5–18.7] (37) | 20.0 [19.9–20.1] (38) | OK×9 |
| lame3.98 | 16.5 [16.0–16.5] (30) | 18.6 [18.5–18.7] (35) | 20.0 [19.9–20.1] (37) | OK×9 |
| lame3.98.3 | 16.5 [16.0–16.5] (30) | 18.6 [18.5–18.7] (35) | 20.0 [19.9–20.1] (38) | OK×9 |
| lame3.98.4 | 16.5 [16.0–16.5] (31) | 18.6 [18.5–18.7] (35) | 20.0 [19.9–20.1] (38) | OK×9 |
| lame3.98.4b | 16.5 [16.0–16.5] (31) | 18.6 [18.5–18.7] (35) | 20.0 [19.9–20.1] (38) | OK×9 |
| lame3.99 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame3.99.1 | 16.5 [16.4–16.6] (33) | 18.6 [18.5–18.7] (38) | 20.0 [19.9–20.2] (43) | OK×9 |
| lame3.99.2 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame3.99.3 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame3.99.4 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame3.99.5 | 16.5 [16.4–16.5] (33) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.1] (41) | OK×9 |
| lame3.99.5_src | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame3.100 | 16.5 [16.4–16.5] (33) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.1] (41) | OK×9 |
| lame3.100.1 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| lame4.0 | 16.5 [16.3–16.5] (37) | 18.6 [18.5–18.7] (39) | 20.0 [19.9–20.2] (41) | OK×9 |
| wb_lame3.97 | 16.5 [16.4–16.5] (31) | 18.6 [18.5–18.7] (37) | 20.0 [19.9–20.1] (38) | OK×9 |
| lame_daily_20020930 | 15.3 [15.2–15.3] (27) | 18.6 [18.5–18.8] (31) | 20.1 [20.1–21.5] (17) | OK×9 |

**What the ladder says (default CBR `-b` lowpass, i.e. the as-shipped config — user `-k`/`--lowpass` overrides are a
different class, see the full-band-320 work):**
- **128k brackets the GENERATION from the lowpass alone**: 16.0 kHz (3.20–3.63b, 1999–2000) → **15.3 kHz** (3.65b–3.93.1,
  2000–2003, the Napster/Kazaa golden age) → 17.0 kHz (3.94b/3.95/3.96/3.96.1, 2003–2005) → **16.5 kHz** (3.97 → 4.0, 2006–2026: 3.97, 3.98, 3.98.3, 3.98.4 ×2, 3.99–3.99.5 ×2, 3.100 ×2, 4.0 — one config on every cell).
  The wild's commonest rate now carries a four-way era split on one number.
- **192k**: 20.0 kHz and barely a wall (slope 8–9) up to 3.63b; a REAL wall (slope ~34) from 3.65b; 19.2 at 3.88b; **18.6 from 3.89b
  onward, unchanged through 4.0** (3.94b–3.96.1 18.5). Point releases measured 21:06: every 3.99.x and both 3.100 builds ≡ 4.0 on all nine cells.
- **320k**: effectively OPEN (21.4, slope 14–19) from 3.34b to 3.88b → 20.5 (3.89b–3.93.1; 3.92 and the 2002 daily 20.1) → 19.0
  (3.94b/3.95) → 18.6 (3.96/3.96.1) → **20.0 (3.97 → 4.0)**. So a 2000–2001 LAME 320 rip has no lowpass wall at all — wall-invisible,
  like the Fraunhofer engine ([[encoder-emitter-landmarks]]); the 21.4 "edge" is the filterbank ceiling, not a lowpass.
- The 1999 builds (3.20/3.24b/3.30b) lowpass ONLY at 128 (16.0); at 192/320 on classical they read 22.05 kHz, slope ≈ 0.
- 3.90 ≡ 3.90.1 ≡ 3.90.3 ≡ 3.90.3mod ≡ 3.91 on every cell (one generation, frontend churn); 3.93 ≡ 3.93.1r on edge.

**Instrument lessons this set forced (all fixed in code, stale rows purged with `.bak_*` kept):**
- ⛔ **EXIT-0 STUB** — 3.20/3.24b given ffmpeg's default WAV (LIST/INFO chunk before `data`) print "Encoding…", return rc=0 and
  write a **419-byte file**; 3.30b at least refuses ("WAVE header corrupt"). Both WAV writers (sweep `prep()`, era bench) now
  write `-map_metadata -1 -fflags +bitexact`; audio bytes unchanged, no other cell moved. Seventh species in the census.
- ⛔ The sweep CACHES encodes; the stubs from the first pass were then "found" and decoded → `DECODE_FAILED ×9` for a rung that
  encodes fine. A cached encode under 4 kB is now treated as absent.
- `--quiet` predates 3.3x: 3.20 parses it as `-q -u -i …`, 3.24b/3.30b "unrec option" — adapter dropped it (changes no bytes).
- Not runnable on Windows 11 and recorded as ERROR×9, never hidden: **3.29b, 3.35b, 3.97 (DOS build)** = 16-bit images;
  **3.83b, 3.86b** = invalid PE images in the archive zips. Smart App Control blocked 3.55b–3.57b until the owner turned it off.
- Archive packaging quirks: the "3.93.1" zip ships the **same exe as 3.90.1** (dropped as a duplicate); the "3.81b" zip ships the
  3.80b binary. Identity file has the hashes.

**Ledger after this block: 900 rows — OK 828 · RATE_OFF 15 (wmav2/ac3_mf, measured, rate not honoured) · RATE_UNSUPPORTED 3
(exhale 320) · ADAPTER_FAILED 9 (NAACEnc, codec DLLs absent) · ERROR 45 (the five non-runnable images above).**


## ⭐ FRAUNHOFER MP3enc 3.0 / 3.1 DEMO — FIRST CELLS (2026-08-21 18:30, 18 cells, all OK, rates honoured on the 30-s encode)

Official Fraunhofer demonstration builds (no key; 30-s limit; `era_encoders/FHG_DEMO_BUILD_IDENTITY.md`).
The first legitimate Fraunhofer encoder in the register — the lineage the wild "no VBR header /
FhG-consistent" class (5.9% of the E:\ last-hop census) descends from; its output carries no Xing/Info tag, as those do.

| build (PE date) | 128k edge | 192k edge | 320k edge | read |
|---|---|---|---|---|
| MP3enc **3.0** (1998-04-03) | 11,983–12,226 Hz | 14,675–14,734 Hz | **14,772–14,879 Hz** | a RATE-INDEPENDENT ~14.8 kHz ceiling above 192k — the old Fraunhofer bandwidth policy, unlike anything in the LAME ladder (LAME 320 ≈ 20 kHz) |
| MP3enc **3.1** (1998-09-23) | 14,309–14,740 Hz | 17,060–19,633 Hz (content-dependent) | 19,525–20,144 Hz | six months later the bandwidth policy changed: ~14.5k at 128, up to ~20k at 320 |

**Switch audit 2026-08-21 19:55 (`-h` of both demos):** NEITHER has a VBR mode — the Fraunhofer demos are CBR-only
(`-br`, `-qual`, `-crc`, `-esr`, `-dm`); the FhG-VBR arm for the V0-end must come from iTunes' Fraunhofer engine via
COM instead. ⭐ **3.0 exposes `-bw <float>` (encoder bandwidth) and `-no-is` (disable Intensity Stereo)** — so its
~14.8 kHz ceiling is a DEFAULT a user could raise, and **intensity stereo is ON by default in 3.0** (a side-channel
tell class of its own — see [[midrange-side-kill-is-v2b-immune]]); 3.1's help drops both switches. Cells above are the
as-shipped defaults, which is what the wild carries.

## ⭐⭐ FRAUNHOFER PROFESSIONAL ACM CODEC — l3codecp.acm 3.4.0.0, SHIPPED BY WINDOWS, DRIVEN IN-PROCESS (2026-08-21 20:15, 9 cells, all OK, rates honoured)

Owner 20:04: "I want full FhG coverage." The 1999–2005 Fraunhofer generation — the engine inside WMP 9/10 on XP,
Sound Forge, Cool Edit, Nero's "FhG mp3" — has been on this machine the whole time as `C:\Windows\System32\l3codecp.acm`
(Fraunhofer-signed, v3.4.0.0; identity `era_encoders/FHG_ACM_IDENTITY.md`). It is NOT registered in Drivers32 (only the
decode-only `l3codeca` is), which is why the 08-07 bridge got NOTPOSSIBLE everywhere. `dev_hunt/_encoders/fhg_acm/fhg_acm_encode.py`
loads it with `acmDriverAddW(ACM_DRIVERADDF_FUNCTION)` — process-local, no registry, no system setting — and the sweep drives it as
the virtual emitter `fhg_acm/l3codecp34`. Format table: MPEG-1 L3 CBR 32–320 kbps (+ MPEG-2/2.5 low rates), stereo/mono,
**no VBR**, joint stereo, no CRC, no Xing/Info tag; drops the last ~64 ms (no end flush).

| rate | elec | class | pop95 | read |
|---|---|---|---|---|
| 128k | 15,795 Hz (slope 27) | 15,795 (38) | 15,784 (33) | **a FIXED 15.8 kHz lowpass** — between the 1998 demo's 14.3–14.7 and LAME's 15.3/16.5 |
| 192k | 18,206 (slope 3.8 — no wall) | 22,050 (none) | 20,004 (36) | content-dependent, mostly OPEN |
| 320k | 19,445 (12.5 — weak) | 22,050 (none) | 20,010 (37) | content-dependent, mostly OPEN |

**Reads.** (1) The FhG lineage now has its own generation ladder on the lowpass: **3.0 (1998-04) caps ~14.8 kHz at every rate
from 192 up → 3.1 (1998-09) lowpasses by rate (14.5/17–19.6/19.5–20.1, real walls) → ACM 3.4 (Windows) walls ONLY at 128
(15.8) and keeps bandwidth above → Apple's build (iTunes) never lowpasses at any rate.** The philosophy memory recorded for
iTunes-FhG ("keep bandwidth, starve bits") starts at this ACM generation. (2) Consequence for detection: a 192/320 rip from
the WMP-era Fraunhofer codec carries **no lowpass wall** — wall statistics are blind to it, exactly like the iTunes rips; it
lands in the wild "FhG-consistent" class (headerless CBR, no wall). (3) **Idem row done 20:32** (`_convict/idem/fhgacm_idem_row.py`, 72 stems, 30-s): **self-pairs at 320 with AUC 0.999** (0.08 vs
null 1.39) and at 128 with 0.974 — the WMP-era headerless-CBR 320 class has a strong same-encoder fixed point, and the probe is a
system binary; the LAME-3.100 probe is BLIND to ACM-320 (AUC 0.45) — family-locking confirmed on a second Fraunhofer generation.
Map: `ENCODER_PROBE_MAP_v0.md` v0.2.
(4) **LAWFUL PRICE, 21:27** (`fhgacm_lawful_price.py`, 30-s excerpts, gt-joined floor, 912 rows): under the **ACM-320 probe** the
twelve lowest "lawful" reads (0.015–0.126) are ALL `SQUAD-E_GDRIVE` files — `re-con - n-joy`, `DCODEMYDIRECTION`, `rave heaven`,
`fix me`, `doesnt matter`, `dedededed`, `tinchy`, … — the very files the 08-07 drive triage flagged as transcodes, now reading AT the
Fraunhofer-ACM fixed point (and NOT at the ACM-128 one: their median under `fhgacm_128` is 2.34). **The quarantined drive is not
lawful ground truth ([[squad-e-gdrive-not-lawful-ground-truth]]) and is excluded from the denominator:** clean lawful **n=596 — min
0.209, q01 0.492, q05 0.814, median 1.70**. Against that: ACM-320 arms **69/72 below the lawful MINIMUM (0-FP shape), 72/72 at q01**;
ACM-128 arms 44/72 below min, 68/72 at q01. The ACM-128 probe is weaker (lawful q01 0.150 → 8/72; its tail is the Simply Jazz
archival set — the band-limited-archival FP mechanism again). ⚠ Constructed fixtures, not the wild; family-locking in the REVERSE
direction (LAME and FhG-3.1 arms under the ACM probes) is running as `fhgacm_cross_row.py` — the leg is only a family fingerprint if
those read lawful-like. **It held, with one qualification (cross row 21:48, `fhgacm_cross_row.py`, 72 stems):** under the ACM-320 probe, LAME-320 arms
read lawful-like (median 0.89; **1/72 below the lawful minimum**, 10/72 at q01) and the 1998 FhG-3.1 320 arms too (0.72; 2/72) — **family-
AND generation-locked at matched rate** — but **LAME-128 arms fall to the fixed point (median 0.09; 50/72 below the minimum)**: the probe
carries the generic heavily-quantised response to ANY ~128k MP3. So the ACM-320 probe convicts "Fraunhofer-ACM 320 OR a ~128k MP3 of any
make"; a second probe separates them (under `mp3_128` a LAME-128 file sits at its own fixed point ~0.2, an ACM-320 file reads ~4.3).
**The SQUAD-E tail, so probed (`squade_tail_probe.py`, the twelve lowest):** `mp3_128` 1.8–7.3 · `mp3_320` 3.1–4.9 · `fhgacm_128` 1.8–3.7 ·
**`fhgacm_320` 0.015–0.126** — high under every LAME probe and under ACM-128, at the fixed point ONLY under ACM-320: **the fixture
signature of a Fraunhofer-ACM 320 encode** (ACM-320 arm: 4.32 / — / 2.44 / 0.08) and of nothing else measured. ⇒ **Phase search 23:00 (`idem_phase_search.py --full`, 576 phases, mp3_320 and mp3_128): all twelve stay high at their best phase — 2.2–4.0 under LAME-320 (best phase mostly 529 = the untrimmed-decode alignment, so the grid was found and the LAME probe still does not reach them), 1.6–7.0 under LAME-128 — against 0.015–0.126 under ACM-320. The attribution STANDS; dedededed (2.17) and tinchy (2.24) sit at the top of the LAME-320-aligned range and are said so.** **The drive's
"(master).wav" transcodes — rave heaven, fix me, doesnt matter, dedededed, tinchy, re-con n-joy, DCODEMYDIRECTION, TWISTA009, the beating
of the drum, im guna make you love me, ultrabeat p & d re-con, save this fuckin rave — carry the NAMED family "Fraunhofer ACM-generation
320 kbps" (the WMP 9/10 / Sound Forge / Cool Edit-era codec).** Caveats that travel with it: n=12 files, constructed fixtures as the
reference, another FhG-core 320 encoder of the same generation would sit at the same point (Sound Forge/Cool Edit plug-ins); the 08-07
triage's "mid-rate" reading for several of these came from texture floors — the two readings are now in tension and the idem family read
is the better-anchored one (four probes, one fixed point).
**Not in the share folder** (Windows-licensed system binary; MANIFEST_RESTRICTED names it and its sha256).

## ⭐⭐ XING MP3 — AudioCatalyst 2.1 (xmencmp3.dll 1.0.0.6, 1999-07-29), THE 16 kHz LANDMARK MEASURED (2026-08-21 21:27, 24 cells, all OK)

**Route, stated plainly:** the owner installed a *scene* "FULL" pack of AudioCatalyst 2.1 (AppleSeed; the .nfo itself cites the
PWA release named in the DOJ case) — his decision, his machine, for R&D measurement. Nothing from it enters the share folder and the
install is EXCLUDED from any public emitter table until a clean twin of the encoder DLL is found (official 2.1 trial / RealJukebox /
MusicMatch). Identities: `AudioCatalyst.exe` 2.10.00 — **PE timestamp 2039-03-22 = a patched header** (the crack); the engine
`C:\Program Files (x86)\Common Files\Xing Shared\MPEG Encode\xmencmp3.dll` **1.0.0.6, Xing Technology Corporation, PE 1999-07-29,
sha256 1af1bfaca975f129…** (319,488 B) — a COM DLL, unregistered, exports only licensing (`Authenticate/Unlock`), so there is no CLI/COM
door: the owner encoded the three sweep sources in the GUI ("Create an MP3 now"), the files entered the ledger through the MANUAL
emitter path (`D:\Xing_cells\out\<label>\<source>_<rate>.mp3`, byte-copied into the sweep so every check ran unchanged). Settings
read back from `AudioCatalyst.ini` (UAC-virtualised): CONSTANT, Default (Joint Stereo), XingReduceSampleRate=True, copyright/original
bits on, **MP3HighFrequencyMode = the switch that decides the whole fingerprint.**

| config | rate | elec | class | pop95 | read |
|---|---|---|---|---|---|
| **HF Mode OFF** (`xing_ac21_cbr_nohf`) | 128 | 16,021 (28) | 16,010 (46) | 16,021 (32) | **a FIXED 16.0 kHz wall at EVERY rate, every source** — slopes 28–53, stopbands −53 to −76 dB |
| | 192 | 16,021 (36) | 16,021 (44) | 16,021 (33) | |
| | 256 | 16,021 (42) | 16,026 (38) | 16,021 (35) | |
| | 320 | 16,021 (53) | 16,026 (38) | 16,021 (33) | |
| **HF Mode ON** (`xing_ac21_cbr`, as shipped in 2.1) | 128 | 16,085 (13) | 19,854 (33) | 17,727 (29) | content edges; |
| | 192 | 18,147 (3) | 19,859 (46) | 18,330 (19) | opens with rate, |
| | 256 | 19,794 (42) | 19,859 (48) | 18,352 (21) | but never above a |
| | 320 | 19,794 (50) | 19,886 (32) | 18,519 (19) | **~19.9 kHz ceiling** |

**Reads.** (1) **The wild "Xing class" is HF-Mode-OFF Xing: one rate-independent 16.0 kHz wall** — the two genuine specimens on disk
now have an emitter, and a bitrate-blind 16.0 kHz razor is a LANDMARK, not a rate estimate (a 320 kbps Xing file reads like a 128 kbps
LAME file on bandwidth alone — [[lame-bitrate-ladder]]'s "assuming LAME" caveat made concrete). (2) HF Mode ON (the 2.1 default) is a
second, softer fingerprint with a ~19.9 kHz ceiling — AudioCatalyst 2.x users who left the default produced that. (3) Xing wrote no
Xing/Info header on CBR here; a Xing-VBR cell is owed (the VBR quality slider). (4) Provenance caveat travels with every row —
**BUT THE CLEAN TWIN WAS ALREADY IN THE REGISTER (21:46).** Xing Technology → RealNetworks → the encoder was open-sourced in 2005 as
the **Helix MP3 encoder** (`era_encoders/helix_mp3/hmp3.exe`, RPSL, measured 08-12, IN THE SHARE FOLDER). Its default cells read
**15,838–15,870 Hz at 128 and 16,015–16,026 Hz at 192/320 on all three sources — the same 16.0 kHz wall** as AudioCatalyst 2.1 with
HF Mode off (16,010–16,026); and **`hmp3 -HF2` = Xing's "High Frequency Mode"** (19.2–19.9 kHz at 192/320 ≈ the HF-on cells).
So the public emitter table cites **Helix 5.0 (clean, redistributable) for the Xing class**, and the owner-installed AudioCatalyst 2.1
is the private confirmation that the 1999 product behaves identically to its 2005 open-source descendant — the warez caveat no longer
touches the claim, only the 2.1 binary itself. Still worth holding from the same archive, both clean-route: **`tompg.zip` (Xing MPEG
encoder CLI 3.0, 1997-11-03)** — the earliest Xing generation, and **`MP3EN15.EXE` (XingMPEG Encoder 1.5b9, 1999-01-03, GUI)**.

**THE XING LINEAGE, CLEAN ROUTE, 21:55 (`era_encoders/XING_IDENTITY.md`; owner fetched tompg / MP3EN15 / Helix-x64 from the archive page
and dropped them in `Encoders/Xing/` on the Drive):**

| generation | binary | PE date | 128 / 192 / 320 edges (elec / class / pop95) | route |
|---|---|---|---|---|
| **Xing tompg 3.0** (CLI; `-B` is PER CHANNEL, `-L3`) | `xing_tompg30/tompg.exe` | 1997-11-03 | **16,021 / 16,021 / 16,021** at every rate, every source (slopes 26–47) | clean (Xing's own distribution) |
| XingMPEG Encoder 1.5b9 (GUI) | `xing_mp3en15b9_installer/MP3EN15.EXE` | 1998-04-23 stub | not yet installed (owner's hands) | clean (Xing shareware) |
| AudioCatalyst 2.1, HF off | `xmencmp3.dll` 1.0.0.6 | 1999-07-29 | 16,010–16,026 at every rate | scene pack (private) |
| AudioCatalyst 2.1, HF on (default) | same | | 16.1–19.9 (content, ≤19.9 ceiling) | scene pack (private) |
| Helix 5.0 r11 x86 (default) | `helix_mp3/hmp3.exe` | 2005 | 15.84–15.87 at 128; 16.015–16.026 at 192/320 | clean (RPSL, in the share) |
| Helix 5.0 r11 x86 `-HF2` | same | | 19.2–19.9 at 192/320 | clean |
| **Helix 5.0 r11 x64** (default) | `helix_mp3_x64/hmp3enc64.exe` | 2009-05-16 | 16.0 at 128; **19.2–19.9 at 192/320 = HF ON by default** | clean (owner drop) |

**Reads.** The **16.0 kHz wall is the Xing engine's constant from 1997 to 2005** — tompg, AudioCatalyst and Helix-x86 read it to the bin;
"High Frequency Mode" (AudioCatalyst 2.x) = Helix `-HF2`, and the 2009 x64 Helix compile ships with it ON by default — **the same source
with a different build default**: build ≠ version, a third time tonight. A wild file with a rate-independent 16.0 kHz razor is Xing
(or Helix default) — and that family now has three clean-route emitters in the register, so the public table never needs the 2.1 binary.


## ⭐⭐ WINDOWS MEDIA ENCODER 9 SERIES — MICROSOFT'S OWN WMA 9.1 STANDARD / PRO, HEADLESS (2026-08-21 22:35, 15 cells OK + 3 RATE_UNSUPPORTED)

Owner fetched the archive.org ISO (`WindowsMediaEncoder9Series_2003`, curator-scanned); both wrappers Authenticode-valid Microsoft,
Defender clean. The IExpress wrapper demands "DirectX Media 8.1" (a 2001 runtime no modern Windows can install) — **the MSI inside has
no such condition** (launch conditions: VersionNT64 ≥ 502, Privileged), so the owner installed `D:\WME9\x64\WMEncoder64.msi` directly
(msiexec, elevated). Engine: `C:\Program Files\Windows Media Components\Encoder\WMEncEng.dll` **10.00.00.3809, Microsoft Corporation,
PE 2006-10-18, sha256 c0db52705acbd52e…**; driven by the shipped `WMCmd.vbs` (`-audioonly -a_codec WMA9STD|WMA9PRO -a_mode 0
-a_setting <kbps>_44_2`). Sweep virtual emitters `wme9/WMA9STD`, `wme9/WMA9PRO` (family `wma-ms`). Rates honoured exactly
(128,016 / 192,016 / 320,008 bps reported). **WMA9PRO 320 at 44.1 kHz/16-bit is refused by the codec** ("input media format is
invalid" — Pro's 320 needs 48 kHz/24-bit) → RATE_UNSUPPORTED ×3, recorded, never substituted.

| codec | 128k | 192k | 320k | read |
|---|---|---|---|---|
| **WMA 9.1 Standard** (`wmav2` to ffmpeg; the WMP rip codec) | **15,956 / 15,983 / 15,967 Hz** (slopes 24–37) | 18,648 / 18,761 / 18,599 (30–45) | 20,064 / 20,085 / 20,064 (31–41) | **a 16.0 kHz wall at 128** — the WMP-default rip; 18.7 at 192; 20.1 at 320 |
| **WMA 9.1 Professional** | 15,951 / 15,983 / 16,064 (23–37) | 18,739 / 18,761 / 18,707 (29–45) | — (unsupported at 44.1/16) | same ladder as Standard at 128/192 |
| ffmpeg `wmav2` (the clone, earlier tonight) | 19,794 / 20,080 / 20,004 at a MEASURED 138 kbps | 276 kbps, 19.8–20.1 | 551 kbps, 20.1 | **no wall, wrong rates — not the wild WMA fingerprint** |

**Reads.** (1) **The wild WMA-128 class (WMP's default rip 1999–2005, our 32/32 blind spot) carries a 16.0 kHz wall** — the third
16-kHz family tonight (Xing 1997–2005; LAME 3.20–3.63b at 128; now WMA 9.1 at 128) and a different container, so the wall alone is a
landmark class, not an emitter. (2) ffmpeg's `wmav2` is NOT a stand-in for Microsoft's encoder at any rate: no lowpass, rates off —
every WMA number derived from the clone is about the clone ([[encoder-transfer-mediafoundation]] again, for WMA). (3) Still open in
the lineage: WMA 7/8 (the 1999–2002 codecs — WME 7.1 / WMP 7), WMA Lossless (needs VBR mode 2), Voice; WME 9 can emit WMA 9 Voice
and Lossless if ever needed. **Not in the share** (Microsoft installer; the owner placed the ISO on the Drive himself).

## ⭐⭐ LATE-NIGHT FAMILIES (2026-08-21 23:00 → 2026-08-22 00:20): XingMP3 1.5 (clean), 8hz, GOGO, Shine, l3enc 1994–97, oggenc 1.0.1

**XingMP3 Encoder 1.5b9 — `x3enc.exe` (CLI) + engine `XmeEncMp3.dll` PE 1999-02-10, CLEAN ROUTE (Xing shareware, owner-installed).**
HF off (`-l`): **16,010–16,026 Hz at 128/192/320 on all three sources**; HF on (default): 16,085 / 19,854 / 17,743 at 128 · 18,147 /
19,859 / 18,319 at 192 · 19,794 / 19,886 / 18,519 at 320 — **identical, cell for cell, to the AudioCatalyst 2.1 scene-pack readings**
(same engine family four months apart). ⇒ every Xing number in the register is now backed by a clean binary (x3enc, tompg, Helix);
the AudioCatalyst install is surplus to the record.

**8hz-mp3 0.2b (April 1999, the dist10 child LAME 2.x grew from):** 128k 16,015 / 22,012 / 19,999 (content — no fixed lowpass),
192k 19,342 / 22,050 / 20,004, 320k 19,972 / 22,050 / 20,021 — slopes 1–32: the ISO-reference lineage does not lowpass (BladeEnc's cousin).

**GOGO-no-coda 3.07–3.12 (2001–2003, LAME-3.88-derived): one config across all six** — 128k **15,235–15,272 Hz** (LAME 3.8x/3.9x's
15.3 kHz, as the lineage predicts), 192k 18,519–19,450, 320k 20,074 / 21,442 / 22,050 (open). The Japanese fork carries the LAME 3.88
lowpass table unchanged through three years of speed work.

**Shine 0.1.4 (2005, the simple fixed-point encoder):** no lowpass at any rate (128k 17,151 / 22,050 / 20,004; 192k 19,331 / 22,050 /
20,004; 320k 19,999 / 22,050 / 20,058; slopes −3 … 27) — content edges only.

**Fraunhofer l3enc 1.00 → 2.72 (1994–97), DOS, via DOSBox, at the shareware cap 112 kbit/s JS (first 18 cells; 12 slow cells re-cutting
overnight with a 30-min limit):** **1.00 / 1.50 (Jul 1994 / Feb 1995): 13,905–13,954 Hz** · **2.00 (Sep 1995): 16,026–16,123 Hz** ·
**2.60 / 2.61 / 2.71 / 2.72 (1996–97): 15,057–15,100 Hz**. The very first Fraunhofer generation moved its 112k lowpass three times in
three years (13.9 → 16.1 → 15.1 kHz) — the earliest MP3s in existence are a datable class on one number. 0.99a/0.99c landed overnight (13,873–13,943 Hz — the 1994 generation); **2.70 does not run under DOSBox**
(go32/DPMI build hangs silently; bracketed by 2.61/2.71 at 15.1 kHz) — 27/27 cells across the nine runnable packages by 01:28.

**oggenc 1.0.1 (libvorbis 1.0.1 + libogg 1.0, BUILT HERE from the owner's xiph tarballs):** 128k 20,494 / 20,683 / 20,021, 192k 20,807 /
21,808 / 20,069, 320k 21,447 / 22,050 / 20,080 — the 2003 Vorbis tuning's ~20.5 kHz at 128 (held 1.1.2 / 1.2.0 / aoTuV / GT3 read 19.5–20).
`-b` enables bitrate management in 1.0.1 (it accepted `--managed` too).

**Banked, not yet measured:** Winamp 5.53 plug-ins (enc_aacplus = CT aacPlus; AudioCoder host owed); Thomson mp3PRO player (encoder
inside the exe, `/ENCODE` opens the GUI — owner cells at the 64k demo cap); RealProducer Basic 8 (cook3260.dll — owner GUI cells);
SoundVQ (IS3 `Data.z`: `encoder.exe` + `SVQbatch.exe` inside — extractor owed); WME 7/7.1 (install vs WME 9 caveat). Identities:
XING_IDENTITY.md, DIST10_IDENTITY.md, GOGO_IDENTITY.md, WINAMP553_IDENTITY.md, FHG_L3ENC_IDENTITY.md.

## ⭐ REALAUDIO G2 COOK — RealProducer Basic 8 (2000), owner GUI cells (2026-08-22 00:24–00:32, 12 cells OK)

The first RealNetworks emitter in the register. `C:\Program Files (x86)\Real\RealProducer\Codecs\cook3260.dll` 6.0.7.1208 "Cooker G2 Audio
Codec for RealAudio" (sha256 71e8170989738779…, PE 2000-06-23) + `Common\encn3260.dll` 6.0.7.1185 "Live Anything Encoder Library"; `realprod.exe`
8.0.0.45 — GUI only (Basic), so the owner encoded the three sweep sources through the Recording Wizard (Record From File → **Single-rate** →
Audio Format **Stereo Music** → one Target Audience) into `D:\Xing_cells\out\real_cook_g2\<src>_<target>.rm`; the manual-emitter door
(any container; `.rm` labels are the target's nominal number, `vbr`-style) decoded them with ffmpeg's cook decoder and measured them by the
same instrument. Target Audience → actual cook mode: **56K Modem = 32.5 kbps @ 22.05 kHz · Dual ISDN = 64.7 kbps @ 44.1 · 256K and 512K
DSL = the SAME 96.7 kbps @ 44.1 mode** (Basic 8's Stereo Music tops out at 96 k; 512K = duplicate payload, kept as a reproducibility pair).

| label (target) | cook mode | elec | class | pop95 | read |
|---|---|---|---|---|---|
| 56 (56K Modem) | 32.5 k @ 22.05 kHz | 22,007 (0.8) | 22,012 (−8.8) | 22,023 (−2.8) | band limit is the 22 kHz sample rate itself (11 kHz content) — below the instrument's wall window; recorded as no wall |
| 128 (Dual ISDN) | 64.7 k @ 44.1 | **15,935 (22)** | **15,940 (33)** | **15,929 (36)** | **a 15.9 kHz wall** — the fourth 16-kHz-class family of the night |
| 256 / 512 | 96.7 k @ 44.1 | 19,735 (24) | 20,252 (52) | 20,004 (32) | ~20 kHz, content-dependent |

**Reads.** (1) RealAudio's 64 k cook mode (the late-90s stream-rip class) walls at 15.9 kHz — indistinguishable from Xing/WMA-128/early-LAME
on the wall alone; the `.rm`/`.ra` container and the cook codec name it. (2) The 96 k mode is ~20 kHz like everyone's 192–320. (3) The 32 k
mode's 22.05 kHz sampling is its own tell. Identities in the register; RealProducer 13 installer banked (owner folder) — later raac/racp.

## ⭐ GOGO 2.x → 3.13a — the Japanese fork's THREE LAME generations, from the owner's WinGOGO packs (2026-08-22 01:05–01:20, 27 cells OK)

The owner's Drive folder `Gogo-No-Coda` carried the three WinGOGO installers rarewares lists beside the 3.07–3.12 CLIs we had
measured: `wing224d.exe` (2.24d, Jan 2000, "based on LAME 3.23"), `wing239c.exe` (2.39c, Dec 2000, "LAME 3.29 + parts of 3.5x"),
`wing313a.exe` (3.13a, May 2004, "LAME 3.88") — plain LZX cabs, 7-Zip opens them; each carries a command-line frontend + the engine
DLL (frontend 2.23 / 2.36 / 2.36 again; the DLL owns the options too — GOGO 2.x DLLs do not know `-silent`: usage + WAIT FOR A
KEY, hung two minutes headless; the adapter drops the switch for `gogo_2.*` rungs). 3.13a's pack is GUI-only; the owner supplied
a `gogo.dll` 3.13 **built 2017-09-09** (PE) — a modern build of the 2004 source (build ≠ version caveat, as lame3.93.1w32).
Identities + shas: `era_encoders/GOGO_IDENTITY.md`.

| rung | engine | 128k elec / class / pop95 | 192k | 320k | read |
|---|---|---|---|---|---|
| gogo_2.24d_2000 | DLL 2.24d (LAME 3.23 lineage) | **16,015 / 15,730 / 16,021** | 19,471 / 22,050 / 20,010 | 21,442 / 22,050 / 20,069 | the 16.0 kHz generation; no fixed lowpass above 128 |
| gogo_2.39c_2000 | DLL 2.39c (LAME 3.29+3.5x) | **16,015 / 15,730 / 16,021** | 19,471 / 22,050 / 20,010 | 21,442 / 22,050 / 20,069 | **IDENTICAL to 2.24d cell for cell** |
| gogo_3.13a_2004 | DLL 3.13 (2017 build; LAME 3.88) | **15,267 / 15,235 / 15,262** | 19,224 / 19,450 / 19,132 | 21,442 / 22,050 / 20,074 | the 3.x table = 3.07–3.12 |

**Reads.** (1) The fork tracks LAME's lowpass table by generation, not by its own version number: 16.0 kHz at 128 for the 2.x
line (1999–2000), 15.3 kHz for the 3.x line (2001–2004) — one number dates a GOGO file to its generation, and 2.24d vs 2.39c is
NOT separable on the wall (same table through a year of speed work). (2) 3.13a (2017 DLL) reads as its 2003 siblings — the
lowpass policy survived the rebuild; whether the quantiser did is a fixed-point question not asked tonight. (3) GOGO 2.x at 192k
on the classical source is open (22,050) where 3.x caps at 19.4 — the 2.x table had no 192 lowpass; another generation tell.

## ⭐⭐ CODING TECHNOLOGIES aacPlus v1.28 (Winamp 5.53 `enc_aacplus.dll`, 2008) — HE-AAC v1 / HE-AAC high / LC-AAC, driven in-process (2026-08-22 08:03–08:10, 18 cells OK)

The Winamp-era HE-AAC encoder (XM/Sirius, Winamp rips, early streaming) — banked 08-21 from the owner's Winamp 5.53 installer, run
today through our own x86 host `dev_hunt/_encoders/winamp_aacplus/aacplus_host.exe` (Winamp AudioCoder API: `CreateAudio3(nch,
srate, bps, 'PCM ', &outt, ini)` → C++ object; **vtable slot 0 = Encode** — slot 1 is the deleting destructor (it returned `this`
and destroyed the coder: that is how the layout was found), slot 3 delay-loads libmp4v2). Dependencies NSCRT.dll (2003) +
libmp4v2.dll from the same installer sit beside the plug-in; the host sets the plug-in's folder as the DLL search path. Output = ADTS.
Type/bitrate support MEASURED: `AACP` aacPlus (HE-AAC v1 + SBR) 64–128 kbps only; `AACH` aacPlus High Bitrate 96–256; `AACr` LC-AAC
64–320 (the MP4 variants `M4A+`/`M4AH`/`M4A ` exist, not cut). Identities: `enc_aacplus.dll` sha 045b1278872293e5 (PE 2008-03-17),
`nscrt.dll` 8094af5ee310714c, `libmp4v2.dll` 91352c617f4f700d — WINAMP553_IDENTITY.md. Rates honoured (129–135 / 194–196 / 320–321).

| type | 128k elec / class / pop95 | 192k | 320k | read |
|---|---|---|---|---|
| AACP (HE-AAC v1, SBR) | **20,338 / 20,435 / 20,080** | (not offered) | (not offered) | SBR reconstructs HF to ~20.1–20.4 kHz at 128 — a HE-AAC 128 reads like a 320 on the wall alone |
| AACH (HE-AAC high) | 20,080 / 22,050 / 19,918 | 20,085 / 22,050 / 20,010 | (not offered) | ~20 kHz / open — content-limited |
| AACr (LC-AAC) | **16,005 / 15,913 / 16,010** | 19,445 / 22,050 / 20,004 | 21,447 / 22,050 / 20,074 | **a 16.0 kHz wall at 128** — CT's LC core joins the 16-kHz class (Xing, WMA9-128, early LAME, cook-64, FhG ACM 15.8); open above |

**Reads.** (1) The family's LC core lowpasses at 16.0 kHz at 128k — the fifth 16-kHz-class emitter; at 192/320 it is open. (2) Its
HE-AAC modes have no wall at all at 128 (SBR fills to ~20 kHz): a 2005 XM/Winamp HE-AAC rip at 64–128 kbps will NOT show a codec
wall — the SBR seam/structure is the tell, not the edge ([[derrien-mdct-residual-probe]] / the stereo-side family are the axes).
(3) The plug-in's UI strings: "Note: some channel modes are only available for certain bitrates" — the support map above is what
that means in practice. Also today: **Xing VBR** (x3enc `-v 50/75/100`, labels nominal 128/192/320, achieved 103–135 / 127–169 /
152–203 kbps): edges 19,471–19,488 / 19,848–19,854 / 19,127–19,138 Hz at every scale — HF mode stays ON in VBR, no 16-kHz wall,
content-limited; the 16.0 kHz Xing wall is a CBR-HF-off property, not "Xing".

## ⭐ iTunes' FRAUNHOFER MP3 ENCODER — THE 3×3 LADDER + ONE VBR CELL, via COM (2026-08-21 20:20–20:31, 12 cells, all OK)

iTunes 12.13.10.3 on this machine (the Apple build of the Fraunhofer engine; memory `encoder-emitter-landmarks`). Until tonight it
was in the register only as one-master FIXTURES. Driver `dev_hunt/_encoders/itunes/itunes_mp3_convert.ps1` (COM: CurrentEncoder =
"MP3 Encoder", ConvertFile2, copy out, delete the library track) + the refusing wrapper `itunes_mp3_cell.py` (rate within 12% /
44.1 kHz / CBR-vs-VBR as requested, else ADAPTER_FAILED with the reason). The bitrate and mode live ONLY in the GUI Import Settings:
the owner set **Custom · VBR off · 44.100 kHz · Joint Stereo · Smart Encoding on · filter <10 Hz on** at 128 → 192 → 320, read each
back after OK-ing out and relaunched iTunes (20:19 / 20:22 / 20:24), then **Custom 256 · VBR ON · Quality Highest** (20:28). The sweep
carries the emitter only while `ITUNES_MP3_KBPS` (+`ITUNES_MP3_VBR=1`) states what the GUI holds; VBR rows keep the measured average
and are never RATE_OFF (`vbr: true`). Last GUI state left: Custom 256 VBR Highest, 44.1 kHz.

| setting | elec | class | pop95 | measured kbps | read |
|---|---|---|---|---|---|
| CBR 128 | 19,461 Hz (slope 14) | 22,050 (0.5) | 20,015 (25) | 128/128/128 | **no wall at 128** — content edges |
| CBR 192 | 19,794 (11) | 22,050 (0) | 20,010 (34) | 192/192/192 | no wall |
| CBR 320 | 21,442 (20) | 22,050 (0) | 20,069 (21) | 320/320/320 | no wall |
| VBR 256 Highest | 19,838 (4) | 22,050 (0) | 20,021 (21) | 280/260/296 (avg) | no wall; Xing header written |

**Reads.** (1) **Apple's Fraunhofer build never lowpasses — now on three sources × four configs, 128 included** (the one rate a
lowpass would have been expected at). Against the same sources: ACM 3.4 walls at 15.8 kHz at 128, the 1998 3.1 demo at 14.3–14.7,
3.0 at 12.0–12.2. (2) Container DNA holds: CBR output is headerless (no Xing/Info/LAME string; iTunes prepends ID3v2), VBR writes a
Xing header without a LAME string — the census's "FhG-consistent" and "XING-STYLE (no LAME tag)" classes respectively.
(3) Every Fraunhofer generation we can now run at 192/320 is wall-invisible except the two 1998 builds; **the Fraunhofer family is
a texture/intermittency problem, not a wall problem** — `mid_contrast`, idem, alignment DNA. (4) The VBR cell is the first
legitimate **Fraunhofer-VBR arm** for the V0-end question (era bench next-work #3).
**Not in the share folder** (Apple's binary; MANIFEST_RESTRICTED names the route — iTunes + the two driver scripts, which are ours and ship in _records/).



⇒ Two FhG generations, six months apart, with DIFFERENT cutoff policies — the edge alone brackets the
generation on this lineage, the way the LAME tag does for LAME. Razor slope 21.6–69.4 dB/kHz (one
soft cell: 3.1 pop95@192 reads 13.3). Caveats: 3-source ladder, 30-s excerpts, demo builds of a
1998 encoder family; the FastEnc / ACM generation (WMP era) is NOT covered by these.

## STILL UNMEASURED — the only genuine gap in what we own

| emitter | why | blocker |
|---|---|---|
| `nero_aac/NAACEnc` | frontend for the Nero Burning ROM 6 "Nero Digital Audio (HE-AAC)" plug-in | **codec DLLs absent.** Adversarially confirmed as a REAL blocker, not adapter debt. 9 cells ADAPTER_FAILED. Do not table as measured. |

## GAPS — not owned

Ranked by (wild prevalence x our blindness). Four of six are free and legal.

| gap | family | why it matters | route | cost |
|---|---|---|---|---|
| **Fraunhofer MP3 (full-length / FastEnc-ACM generation)** | MP3 | the 1990s professional path (Audition, Sound Forge, Winamp, ISDN). ✅ 2026-08-21: the OFFICIAL MP3enc 3.0/3.1 DEMO builds (30-s limit) are owned and measuring — the lineage is no longer absent; the FULL-length encoder and the WMP-era ACM generation remain the gap. The scene copy stays excluded. | `C:\Windows\System32\l3codeca.acm` — **already licensed as part of Windows**. No ffmpeg ACM path; drive via the Windows ACM API or an ACM-aware era tool. | **free** |
| **FDK-AAC** | AAC | every Android device and much of streaming | open source | **free** |
| **WMA (Std/Pro)** | WMA | memory: **32/32 unarmed** — a complete blind spot | Windows Media Format SDK / Windows itself | **free** |
| **8hz-mp3 / Shine / Gogo** | MP3 | dist10 siblings; cheap lineage breadth | GPL / open | **free** |
| **Xing** | MP3 | *the* 16 kHz cutter; historically huge in late-90s ripping | see below | buy |
| **RealAudio (Cook/RA)** | Real | 90s–2000s rips still circulate; ffmpeg DECODES but cannot ENCODE, so we cannot build controls | see below | ask |

### Finding Xing
Xing Technology (Arroyo Grande CA, founded 1989) was **acquired by RealNetworks in 1999**, so the
two hunts are one hunt. Xing's MP3-bearing products, by name — these are the search terms:
**Audio Catalyst**, **MP3 Grabber**, **StreamWorks**, **XingMPEG**, plus a **Mac MP3 encoder**
(reportedly the first on that platform — would need a classic-Mac emulator to run).

⭐ Xing is the highest-value single landmark in this list, because it is the **extreme** case: the
encoder was built for speed with a minimal psychoacoustic model and is known for a hard ~16 kHz
lowpass at every bitrate. It was also enormously popular for ripping c. 1999-2001, so wild files
exist in quantity. (Note for the record: an earlier session attributed that 16 kHz wall to 1990s
MP3 encoders *as a family* — **measured wrong**, BladeEnc holds the band to ~20 kHz. The behaviour
is Xing-specific, which is exactly why the cell matters.)
1. **RealJukebox** (1999–2001) was a free download and is understood to have used the **Xing MP3
   encoder** for ripping — the cheapest legitimate route to Xing's lineage. ⚠ Believed, not verified;
   confirm the encoder identity before the cell is quotable.
2. **Xing AudioCatalyst 2.x** — boxed retail; turns up on eBay. Buying a licensed physical copy is
   clean, and this project already buys discs for provenance work.
3. **Bundled OEM copies** — Xing shipped with some CD-ROM drives and burner suites of the era.
   A boxed Easy CD Creator / drive bundle may carry it.
4. ⛔ Not a route: abandonware download sites. Same objection as MP3Enc — it would poison the table.

### Finding RealAudio — ⭐ THE GAP IS ONE CODEC, NOT A FAMILY
RealAudio is a **container that mostly wraps other people's codecs**. Decomposed by FourCC:

| FourCC | actual codec | relevance | our position |
|---|---|---|---|
| `lpcJ`,`14_4` | IS-54 VSELP | speech | irrelevant to music provenance |
| `28_8` | G.728 LD-CELP | speech | irrelevant |
| `sipr` | Sipro ACELP-NET | speech | irrelevant |
| `ralf` | RealAudio **Lossless** | not lossy | irrelevant to lossy detection |
| `dnet` | **Dolby AC-3** | DVD/concert rips — a real wild source | ⚠ **ffmpeg encodes AC-3 natively and we have never measured it** |
| `atrc` | **Sony ATRAC3** | MiniDisc lineage | likely already covered — [[atrac-encoder-acquired]] |
| `raac` | MPEG-4 **LC-AAC** | mainstream | covered (Nero / FAAC / qaac / ffmpeg) |
| `racp` | MPEG-4 **HE-AAC** | streaming | reachable (Nero HE / FDK) |
| **`cook`** | **RealNetworks G2, in-house, 1998** | **the only genuinely unique one** | **decode-only** |

⇒ The acquisition target is **cook alone**, not "RealAudio".

**Why cook is worth the trouble beyond coverage:** it is a pure MDCT transform codec with a
**single block size** — no window switching. Our lattice probes are built around block geometry, so
a fixed-lattice codec with no block switching should be unusually legible to them. Plausibly the
most detectable codec we would ever hold, if controls can be built.

Routes:
1. **RealProducer Basic was genuinely free** (RealNetworks gave it away to seed content), which makes
   archived copies far less problematic than cracked commercial software. Versions G2 / 8 / 10 / 11.
   This is the encoder that produces `cook`.
2. **Helix Producer** — RealNetworks' successor line with open-sourced components. **We already hold
   `helix_mp3`**, so the lineage relationship is established.
3. ffmpeg has a **reverse-engineered cook DECODER** (libavcodec, Dec 2005) and no encoder. Enough to
   *characterise wild cook files*, not enough for same-content recreation. Until an encoder is
   obtained, cook cells are **observation-only and must be labelled as such**.

⇒ Register correction: move **AC-3** out of "gap" — we can encode it today with ffmpeg and never have.

### Funding note
Xing and Real are the only two that cost money, and a research licence for building a **public**
encoder-provenance reference is squarely what grant money is for. Put them in the NLnet budget as a
named line item under M4 rather than begging — a named deliverable strengthens the application.

---

## Status vocabulary
- **measured** — run through the current instrument with the full source ladder; cells quotable.
- **owned/unmeasured** — binary in hand, no cells. A blind spot we could close today.
- **gap** — not held. Any claim of coverage over this family must name the exclusion.
- **excluded** — held but unusable on principle (warez). Never counted as coverage.

---

## ⛔⭐ BUILD IDENTITY — added 2026-08-20, because a version banner is not a build

**Why this section exists.** `_encoders/musepack/BUILD.md` argues, in a document now in Guillain's
hands, that *"generating forensic fixtures with a binary of unknown build provenance and then making
encoder-specific claims off them is self-undermining"*. Until today **this register recorded zero
hashes** — eleven LAME builds identified by a label we invented. We asserted the principle and had
not applied it to our own ladder.

**What forced it.** Guillain, 2026-08-20: his Debian `mpcenc` reports the same
`MPC Encoder 1.30.1 --stable--` banner as our build but comes from **r495, twenty revisions past our
r475**. Same banner, different source. We already held the mirror of that (C23 / :2448):
`lame3.93.1w32` was **compiled 2023-09-10** and still emits the 2002-era 20,106.6 Hz wall — same
source version, different build date. ⇒ **banner, source revision and build date are three
independent axes**, and a label pins none of them.

⛔ **AND IT REPRODUCES INSIDE OUR OWN LADDER — two banner collisions in eleven builds:**

| our label | sha256[:16] | bytes | PE built (UTC) | reported banner |
|---|---|---|---|---|
| `lame3.90.3` | `1378da3a03c562c3` | 188,928 | 2004-02-06 | LAME version 3.90.3 MMX |
| `lame3.90.3mod` | `e34bce50e59d383d` | 187,904 | 2004-02-05 | LAME version 3.90.3 MMX ← same |
| `lame3.92` | `cb2cdfde7b170d90` | 195,072 | 2002-04-16 | LAME version 3.92 MMX |
| `lame3.93.1r` | `05288b1f6ee9323b` | 184,832 | 2003-05-11 | LAME version 3.93 MMX |
| `lame3.93.1w32` | `33b4ed8f51c803f5` | 751,104 | **2023-09-10** | LAME version 3.93 MMX ← same |
| `lame3.96.1` | `13632cb88958cc39` | 187,904 | 2004-07-26 | LAME version 3.96.1 |
| `lame3.98.4` | `1db09bd2d0bce1cd` | 507,904 | 2010-06-06 | LAME 32bits version 3.98.4 |
| `lame3.99.5` | `70040331c3d2dede` | 516,096 | 2012-12-05 | LAME 32bits version 3.99.5 |
| `lame3.100.1` | `2a411a117671c7b0` | 1,421,312 | 2020-09-07 | LAME 32bits version 3.100.1 |
| `lame_daily_20020930` | `91566093679ce07d` | 192,512 | 2002-09-30 | LAME version 3.93 MMX (alpha 2) |
| `wb_lame3.97` | `f6a2c6c55ca60756` | 520,192 | 2006-10-03 | LAME 32bits version 3.97 |

**11 distinct binaries, 11 distinct labels, but only 9 distinct banners.** `3.93.1r`/`3.93.1w32`
are byte-different builds twenty years apart reporting one string, and the string says **"3.93"**,
not "3.93.1" — so the banner is *less* specific than our own label. `3.90.3` / `3.90.3mod` likewise.

⇒ **Our labels are sound and our binaries are distinct.** The gap was never correctness, it was
**reproducibility**: nobody outside this machine could tell which "LAME 3.92" we meant, and we could
not have proved it ourselves if a binary were ever swapped. Now they can, and we can.

### What this does and does not touch

✔ **GMF is unaffected.** Its evidence is RECREATION FROM THE SAME SOURCE (:2513) — the CD is
continuous to 22 kHz, the store file walls at 21,436.3 Hz, and the CD's own audio through
`lame3.92` reproduces that wall. That is a behavioural demonstration with a binary in hand, not an
inference from a version string. The bracket was never resting on the banner.
⭐ It is now also **reproducible**: the binary is `sha256 cb2cdfde7b170d90…`, 195,072 bytes, PE built
2002-04-16.

⚠ **Any future claim of the form "encoder version X does Y" must cite the sha256, not the banner.**
Two of our eleven builds would satisfy such a claim by banner while being different programs.
