# Rule 13 before the acquittal: the default scan asks it on silent full-band files — registered 2026-10-01, before the measurement is read

Written and committed **before the probe's results and the before/after
passes are read**, per the convention. The direction chose the change on
2026-10-01 over two alternatives (leave the default as it is and push
`--deep` harder in the docs and GUI; make `--deep` the default).

---

## Where this comes from

The controlled bench of 2026-09-30 (33 loud 2004 hard-house CD tracks,
third-party rips used as content references, encoded with ffmpeg 8.1 and
decoded back to FLAC 16/44.1; the transcode label is by construction). With
torch live, 1.19.1, 33 files per arm:

| arm | default scan | `--deep` | Rule 13's points in `--deep` |
|---|---|---|---|
| AAC 256 (ffmpeg native) | 0 | 33 | 55 on 32 |
| Vorbis q6 | 0 | 33 | 55 on 31, 25 on 2 |
| MP3 320 CBR | 15 | 33 | 0 (the CNN) |
| full-band VBR MP3 (`-q:a 0`, no low-pass) | 0 | 29 | 0 (the CNN) |
| the 35 CD tracks + 2 store files | 0 flagged | 1 WARNING 31 (CNN alone) | 0 on all 37 |

The cause is not a defect of a rule. **Short-circuit 2** acquits a file whose
fast rules score under 10 with no MP3 signature, before Rules 12-16 run;
only `--deep` bypasses it, and the documentation says so ("`--deep`: catch
high-bitrate AAC/Opus/Vorbis (slower)"). The branch is, in its own comment,
"precisely the 256-320 kbps AAC blind spot". A default scan never looks there.

## The change

In the default mode, the fast path **asks Rule 13 first** when
`should_run_rule_13` admits the file (cutoff ≥ `MIN_CUTOFF_HZ` = 18 kHz, not
already convicted). If Rule 13 scores nothing, the file is acquitted exactly as
before, with a `why:` line that says Rule 13 read no grid. If it scores, the
file is not acquitted: it goes on to the witnesses the deep branch runs
(Rules 14, 15, 12, 16) and its verdict is computed from everything. `--deep`
is unchanged; so is every file that does not reach the fast path.

Rule 13 itself is unchanged: bars `RATIO_HARD` 3.0 → +55, `RATIO_REVIEW` 2.0 →
+25, both hypotheses (KBD and Vorbis windows). Its calibration
(`ml/recert_880.csv`, 877 certified-genuine files: 797 logged rips of the
direction's library, 80 audit): median 1.27, p99.9 1.614, **max 2.418**; 1 file
of 877 over 2.0, 0 over 3.0. On the fast path the score is under 10, so a lone
+25 lands under WARNING (31): **only a reading at or over 3.0 can move a
file's verdict**, to SUSPICIOUS at most on its own.

**Cost**, measured on 10 genuine full tracks (3-12 min): decode 1.0-2.8 s,
Rule 13 5.9-9.5 s — about **+9.5 s per full-band file** the default scan used
to acquit at once. Not paid under 18 kHz, nor on files that leave by any
other path.

## Criteria, registered before anything below is read

**Probe** (`fd-r13/r13_probe.py`): the shipped `apply_rule_13_mdct_alignment`
on the full decode, on every file with a cutoff ≥ 18 kHz in
`fd-r1w/trace_gen.csv` and `trace_60s.csv`, plus the bench. Populations:
labelled genuine (audit authentic, v2 genuine, attested CDs, full-length,
received, wild), unlabelled (library sample 1,672, Dust-to-Digital 1,851,
Awesome Tapes 275), the audit arms, the halves, the bench.

**Passes**: before = 1.19.1 (`e8cebd6`); after = the same plus this change;
`FLACAnalyzer.analyze_file`, default mode, torch live, 30 s. Run on every
labelled genuine file, on every unlabelled file the probe reads at ≥ 2.0, on
the audit AAC / Vorbis / Opus arms, and on the bench (37 + 132). A file the
probe reads under 2.0 cannot move by construction (Rule 13 returns 0 and the
fast path returns as before); a sample of 100 of them is run both ways to
check that construction.

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **R1** | labelled genuine files the probe reads ≥ 3.0 | 0 | any |
| **R2** | labelled genuine files whose verdict or score moves | 0 | any |
| **R3** | the bench's 37 CD and store files: verdict moves | 0 | any |
| **R4** | the bench's AAC 256 and Vorbis q6 caught in the default scan | ≥ 60 of 66 | under 50 |
| **R5** | audit `aac_ff256` / `aac_ff320` / `vorbis_q8` newly caught in the default scan | most of what `--deep` catches | none |
| **R6** | unlabelled files reading ≥ 3.0 | listed by name with their verdict; none expected among the logged rips (the 797 of the calibration) | — (shipping decided on the list, in writing) |
| **R7** | the 100-file control: any verdict, score or family change | 0 | any |
| **R8** | transcodes losing a detection | 0 | any |

R1, R2, R3, R7 or R8 failing refuses the change. MP3 320 and full-band VBR
are outside Rule 13's reach (it reads AAC and Vorbis windows) and stay
`--deep`'s, through the CNN; reported, not judged. Apple AAC is also outside
its reach (fires on 0-13 % at 128-320 kbps in the calibration), and is the
store format: this change does not close that, and the docs will say so.
