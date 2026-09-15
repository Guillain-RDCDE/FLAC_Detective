# Rule 1 depth gate: the floor above the edge — registered 2026-09-15, before the after-pass

Written and committed **before the after-pass is run**, per the convention: the
criteria are fixed while the answer is still unknown. The before-pass on the
shipped engine (1.13.15, worktree `fd-v11315` at `8fe38ab`) is running; its
numbers are not in this section.

Prompted by two commercial AIFF files received on 2026-09-14 for an A/B: the
Beatport editions of two tracks whose CD and vinyl editions run to 20.5–21 kHz.

---

## What the two files showed

Two Beatport AIFFs (44.1 kHz, 16-bit, uncompressed) of "DJ Hein — Energetic
Rhythm", original mix and Donkey Rollers remix. The CD rip of the remix (EAC,
AccurateRip-confirmed) reads a cutoff at 20,500 Hz; the owner's vinyl rips read
20,750 and 21,000 Hz; the Beatport files read **16,250 and 16,000 Hz**. The
same master lost 4 kHz on its way to the store.

1.13.15 on them, `--sample-duration 30`, and 1.13.14 before it, identical:

| file | cutoff | step across the edge | Rule 1 | Rule 2 | verdict |
|---|---|---|---|---|---|
| original mix, Beatport AIFF | 16,250 Hz | 8.8 dB | 0 — "a roll-off, not a codec wall" | +19 | **AUTHENTIC 18** |
| Donkey Rollers remix, Beatport AIFF | 16,000 Hz | 7.7 dB | 0 — same | +20 | **AUTHENTIC 20** |
| Donkey Rollers remix, CD rip (FLAC) | 20,500 Hz | 0.9 dB | 0 | 0 | AUTHENTIC 0 |

Two locks hold the door shut on these files, and each would hold alone:

1. **Gate D reads their edge as a slope.** The Beatport low-pass is soft:
   7.7 and 8.8 dB over 500 Hz, under the 12 dB bar. Over 2 kHz it falls 25–26
   dB, then nothing — but gate D reads two cells, not the floor.
2. **Gate C-prime has no depth reading to accept an uncompressed container.**
   On WAV/AIFF the container bitrate is ~1411 kbps whatever the audio's
   history, and the v1.12 repair accepts that only when "the wall proves its
   depth" — read by `compute_residual_floor_db` in a FIXED band at 0.961–0.993
   × Nyquist, computed only when the cutoff sits in [0.85, 0.94) × Nyquist.
   A wall at 16 kHz has no reading there. This is the mechanism named in the
   v1.12 campaign as its one missed efficacy prediction (G2: 15/34 instead of
   the registered 20) and deferred as "v1.13 material". It was never done.

## The instrument: `spectrum.floor_above_edge_db`

On the same Hann-windowed FFT and the same 250 Hz cells `detect_cutoff` scans
(each cell's median level relative to the 10–14 kHz reference median, raw
magnitude), the **median cell level from (cutoff + 1,000 Hz) up to 0.993 ×
Nyquist**, taken on the window that produced the minimum cutoff — the edge
Rule 1 acts on. NaN when fewer than 4 cells (1 kHz) fit above the gap, which
is the case from about 19.9 kHz up at 44.1 kHz: in the near-Nyquist zone the
existing residual-floor instrument rules, and this one abstains. NaN when no
edge was found.

It reads what the slope gate cannot: **what is left above the edge**. A codec
low-pass, soft or steep, leaves digital silence; a mastering roll-off keeps
falling into an analogue or dither floor, and the vinyl and CD editions of the
same music keep noise up to Nyquist.

Measured offline from the gate D probe's cell profiles (`fd-issue8/wall/
probe30.csv`, `probe30_v2.csv`, 30 s, the calibrated setting; scratch script
`floor_above.py`), on edges below 19,500 Hz that have a reading:

| arm | files | edges < 19.5 kHz | soft (< 12 dB) | floor min / p10 / median / p90 (dB) |
|---|---|---|---|---|
| reporter's two files (issue #8) | 2 | 2 | 2 | −44.4 / — / −42.6 / — |
| full-length genuine (12) | 12 | 0 | — | no edge |
| audit authentic (80) | 80 | 4 | 2 | −49.9 / −46.0 / −34.8 / −32.2 |
| v2 genuine (63) | 63 | 9 | 4 | **−55.2** / −50.8 / −37.0 / −32.5 |
| **Beatport AIFF (2)** | 2 | 2 | 2 | **−65.1 / −62.8** |
| full-length LAME 192 + 128 (24) | 24 | 24 | 0 | −68.1 / −66.4 / −57.5 / −35.5 |
| audit mp3_128 | 80 | 75 | 0 | −75.8 / −70.4 / −54.3 / −41.7 |
| audit mp3_192 | 80 | 75 | 1 | −75.6 / −70.1 / −58.0 / −42.7 |
| audit mp3_320 | 80 | 5 | 2 | −68.6 / −66.2 / −62.4 / −41.2 |
| audit mp3_V0 | 80 | 7 | 4 | −68.7 / −64.0 / −37.8 / −31.7 |
| audit mp3_V2 | 80 | 74 | 4 | −75.8 / −67.9 / −52.6 / −39.6 |
| audit aac_ff128 | 80 | 75 | 0 | −70.6 / −66.1 / −50.9 / −39.0 |
| v2 mp3_192 / mp3_320 / mp3_V0 | 61 / 60 / 61 | 58 / 13 / 19 | 1 / 5 / 4 | −76.5 / −67.3 / −67.7 min |
| v2 aac_ff128 / ff256 / ff320 | 63 / 61 / 61 | 60 / 8 / 10 | 1 / 4 / 4 | −71.4 / −65.2 / −51.7 min |
| v2 aacmf_256 / opus_256 / vorbis_q8 | 60 / 61 / 60 | 22 / 10 / 16 | 6 / 4 / 10 | −69.7 / −61.8 / −67.5 min |

Three things in that table decide the design.

**The bar: −58 dB.** Of 155 genuine files (13 edges below 19,500 Hz with a
reading), the deepest floor is −55.2 dB — one v2 file with a hard 22 dB wall
at 17,750 Hz. The deepest genuine SOFT edge is −49.9 dB. The two Beatport
files read −62.8 and −65.1. A bar at −58 sits 2.8 dB under the deepest
genuine edge and 4.8 dB above the shallower Beatport file; at −55 the genuine
hard wall would sit 0.2 dB from the line, and at −60 the Beatport remix would
sit 2.8 dB from it. The margins are reported as they are: the genuine hard
walls below 19.5 kHz are 7 files, not 70.

**The floor is relative, so it is partial on purpose.** It is measured
against the 10–14 kHz reference like every other cell reading here, so a
quiet or HF-poor recording (much of the v2 set is live tape) reads a shallow
floor even under a codec: the medians of the CBR arms sit at −51 to −58 dB.
At −58 the instrument reaches 32 of 75 mp3_128 walls, 38 of 75 mp3_192, 12 of
24 full-length LAME. On FLAC input those walls are already convicted by the
container window; the reach matters for uncompressed input, where they are
currently invisible, and is measured below (E-criteria) rather than assumed.

**What it changes on soft edges.** Below 19,500 Hz, a soft edge with a floor
at or under −58 dB: 0 genuine, and 7 transcodes across the labelled sets —
the 320 kbps transcode of DJ Katapila (−62.4) and the V0 transcode of The
Mebusas (−60.9) that gate D acquitted on 2026-09-08 (Rule 1 had read the
master's own roll-off; it now reads the silence the codec left above it), and
five v2 files (mp3_320 ×2, aac_ff128, aac_ff256, opus_256). Those are the
only FLAC movers the derivation allows, and they can only move toward
conviction.

## The repair

1. `analyze_spectrum` returns a sixth value, `floor_above_db`, read on the
   window that produced the cutoff. NaN when no edge was found or when fewer
   than 4 cells fit above the gap.
2. `constants.DEEP_FLOOR_DB = -58.0`.
3. **Gate D yields to depth**: `edge_is_a_slope` returns False when
   `floor_above_db <= DEEP_FLOOR_DB`, whatever the step. A soft edge over
   digital silence is a codec low-pass with a gentle filter. The reason line
   says so. NaN keeps gate D's existing behaviour exactly.
4. **Gate C-prime accepts the depth from either instrument**: an uncompressed
   container is accepted when the near-Nyquist residual floor proves the wall
   (unchanged) OR when `floor_above_db <= DEEP_FLOOR_DB`. The +50 reason line
   names the floor when the container was uninformative.
5. `rule1_may_consult_container` mirrors both, so the re-encode that sizes the
   container is taken on exactly the files Rule 1 will score.
6. The container window itself is **not touched**; on FLAC input every other
   path is unchanged by construction.

## Criteria, registered before the after-pass runs

Corpora, before-pass on 1.13.15 and after-pass on the repaired code, same
files, same order, `--sample-duration 30` (the calibrated setting), plus 120 s
on the reporter's files, torch shimmed out on both sides (the CI
configuration):

* the 7 received files (3 Beatport AIFF, 2 vinyl WAV, the CD FLAC, Uluru);
* the reporter's two files (30 s and 120 s);
* `audit_corpus/authentic` (80) **as FLAC and as WAV** (ffmpeg, source bit depth);
* `audit_corpus/fake/mp3_320` and `mp3_V0` (80 each) as FLAC — the two arms
  that hold the predicted soft-edge movers;
* `audit_corpus/fake/mp3_128` and `mp3_192` (80 each) **as WAV** — the reach
  on uncompressed input;
* `fd-pistes-completes` (12 genuine full-length) and `long_mp3` (24).

| # | criterion | bound |
|---|---|---|
| **A1** | genuine files newly convicted (`FAKE_CERTAIN`) on any corpus, FLAC or WAV | **0** — structural; one means the derivation is wrong |
| **A2** | genuine files newly signalled (`WARNING`+) on any corpus, FLAC or WAV | **0** — structural |
| **A3** | every FLAC-input mover | toward conviction, cutoff < 19,500 Hz, step < 12 dB, floor ≤ −58 dB, carries the depth reason — any mover outside that profile withdraws this document |
| **P1** | the two Beatport AIFFs | Rule 1 +50 on both; verdict `FAKE_CERTAIN` or `SUSPICIOUS` on both |
| **P2** | the reporter's two files | unchanged: AUTHENTIC, same score, at 30 s and 120 s |
| **P3** | the CD FLAC, the two vinyl WAVs, Uluru, Twisted | unchanged verdict and score |
| **E1** | `mp3_128` as WAV, signalled after | ≥ 25 of 80 (before-pass expected near 0 on this input) |
| **E2** | `mp3_192` as WAV, signalled after | ≥ 25 of 80 |
| **E3** | FLAC movers on `mp3_320` + `mp3_V0` | exactly the two named files, or fewer; any other name is reported and examined |
| **E4** | transcodes losing a conviction or a signal, any corpus | **0** — the gate can only add |

A1, A2, A3 or E4 breached: the repair does not ship in this form. E1–E2
under the bound: shipped anyway if A-criteria hold (a partial reach on
uncompressed input beats none), and the shortfall is reported with the reason.

## Remaining defects, reported and not repaired here

* **The floor is relative to the programme level**, so a codec wall over a
  quiet or dark recording reads shallow and stays out of reach on
  uncompressed input. An absolute reading (dBFS) would see the dither floor
  directly; it is a different instrument with its own calibration. Own
  registration.
* **The container window cliff** (WALL_GATE registration) is untouched.
* **The near-Nyquist zone** (≥ 19.9 kHz here) keeps its fixed-band residual
  instrument and its known limits; the Twisted AIFF (20,250 Hz, floor −50.4
  in a 2-cell band) is out of this repair's reach by construction.

Results are appended below, after the run, in a section dated after the fact.

---

## AMENDMENT — 2026-09-15, after the first after-pass, before the second

The first after-pass (`after1_*`, kept) ran on the repair as registered above
and **P1 failed**: both Beatport AIFFs still read AUTHENTIC 18 and 20. Gate D
did yield — its reason line is gone from both files — and Rule 1 then reached
the container window, which said no.

The mechanism, measured rather than guessed: since the one-ruler repair
(issue #7) EVERY container is sized by re-encoding its audio to FLAC, so an
AIFF no longer reads at PCM level. Lock 2 as described above ("no depth
reading to accept an uncompressed container") does not exist any more; gate
C-prime's PCM branch is dead code on this engine. What holds the door is
**the container window itself**: the 160 kbps cell accepts 450–650 kbps, and
these two dense, loud trance masters compress to **776 and 848 kbps** with
their 16 kHz ceiling (the CD edition of the remix: 939; the vinyl rips: 661
and 700). The window is calibrated on the FLAC size of decoded MP3s of
typical music; a loud master sits outside it whatever its history. That is
the container-window cliff named in the WALL_GATE registration, seen from
the other side: there it acquitted a steep-wall transcode at 762 kbps, here
it acquits a soft-wall one at 776.

### The amended repair

Item 6 ("the container window is not touched") is withdrawn and replaced:

6. **The container window yields to depth.** Below the 320 cell, when the
   floor above the edge is at or under `DEEP_FLOOR_DB`, Rule 1 awards its
   +50 without consulting the container window, and the reason line names
   the floor. When the floor is shallow or unknown, the window decides
   exactly as in 1.13.15. Gate C-prime's PCM branch is left in place (it is
   NaN-safe and inert on this engine) and documented as such.

Nothing else changes. The gate can still only add a +50, never remove one.

### What the amendment widens, on the instrument table above

The FLAC-input movers are no longer only the soft edges: every hard wall
below 19.5 kHz with a floor at or under −58 dB that the window currently
acquits can now be convicted. On the labelled sets those are transcodes by
construction (0 of 155 genuine files read a floor at or under −58 dB below
19.5 kHz; the deepest genuine hard wall reads −55.2). The margin is the same
2.8 dB it was, on the same 13 genuine edges, and it now guards a larger
population; that is said here rather than discovered later.

### Criteria, re-registered for the second after-pass

A1, A2, A3 (profile: toward conviction, cutoff < 19,500 Hz, floor ≤ −58 dB,
carries the depth reason — the step condition is dropped), P1, P2, P3 and E4
stand as written. E1 and E2 now measure the window's cost on both containers
alike (the WAV arms read the same FLAC-equivalent size as the FLAC arms):
transcodes signalled after ≥ 25 of 80 on each. E3 becomes: every FLAC mover
on `mp3_320` + `mp3_V0` is a transcode with floor ≤ −58 dB, listed by name.

The `after1_*` folders are the record of the failed first pass; the second
pass writes `after2_*`.
