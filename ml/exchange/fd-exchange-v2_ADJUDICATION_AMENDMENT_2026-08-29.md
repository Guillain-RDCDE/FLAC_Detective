# fd-exchange-v2 — adjudication amendment, 2026-08-29

The adjudications of 2026-08-23 (`fd-exchange-v2-2026-08-ADJUDICATIONS.json`,
sent to Provir with the key) are **not edited**. This is the amendment section
the convention calls for: a correction goes in a new section, dated after the
fact, and the shipped artefact keeps saying what it said when it shipped.

Two amendments, both prompted by Jamie Dodd's letter of 2026-08-29, and neither
of them a change of label. **No verdict moves. No engine verdict became a label
here or anywhere.**

---

## 1. `fd-exchange-v2-2026-08-0197` — codec class recorded: MPEG-1 **Layer II**

Label unchanged: **fake**, basis `uploader_admission`, item `TenD2005-07-16`,
taper's source line `Sony PC100 > AVI > MP2 > WAV > FLAC`.

What is added is the thing the label never said: **MP2 is MPEG-1 Layer II, not
Layer III.** A different filterbank, 32 subbands and no MDCT stage — so every
MP3-family instrument on both sides is looking for a transform this file does
not contain.

His observation, adopted: the file sits at the null for the MP3 families in both
engines *because both engines are wrong about which filterbank to look for*, and
carrying it as a miss misprices both. It is carried from here as a **codec class
neither engine covers**, and that is an admission of coverage, not of failure.

    codec_class      mpeg1_layer2
    covered_by_v113  no  (no Layer II instrument exists in this engine)
    covered_by_provir no (his statement, 2026-08-29)

Consequence, stated so it cannot be quietly enjoyed later: the v2 score of
"one false conviction each on 56 verified genuine" is unaffected — 0197 was
already adjudicated fake on the taper's admission, and his conviction of it was
already recorded as right. What changes is the *reason* it was hard, and the
reason is now a named gap in both instruments rather than an unexplained null.

Registered as the v3 candidate it implies: a Layer II arm belongs in the next
set, at which point this stops being a note and becomes a measurement.

## 2. `fd-exchange-v2-2026-08-0469` — his measurement recorded as a side channel

Label unchanged: **unverifiable**, basis `device_ambiguous`, item
`SweatyAlreadyStringBand2026-08-16`, source line `Zoom H1n` (a recorder that
writes WAV or MP3), format unstated.

He states it is the single most anomalous file in the genuine-or-unverifiable
part of the set on measurement, and that it reads as carrying lossy history. He
explicitly does not ask for the lineage ruling to move. It does not move.

What is recorded, in the `basis`-adjacent field that exists for exactly this and
carries no evidential weight:

| instrument | side | reading |
|---|---|---|
| `AAC_LATTICE` | Provir | 69 % |
| `DEAD_STRUCTURE_MAXRUN` | Provir | 126 (mean run 8.56) |
| stereo witness (Rule 15) | FLAC Detective | 5.8 |
| `telemetry.opus_edge` | Provir | edge 21,530 Hz, std 155.9 — *admitted by 4.1 Hz under his own 160 Hz bar* |

Four instruments across two independent engines read it lossy. **None of that
is a label**, and the file stays `unverifiable` until provenance arrives. The
prediction is registered here so it can be scored rather than remembered
selectively: **if provenance ever turns up for 0469, it lands lossy.** If it
turns up genuine, this row is the counter-example and gets quoted as one.

---

## Not amended: the two that stay genuine

`0306` (dknowles2008-07-13, analog FM line-in capture, no codec in the chain)
and `0362` (recipe2004-08-21, SBD, named taper, no lineage) stand exactly as
adjudicated. 0306 remains his one true false conviction on this set and 0362
remains ours.
