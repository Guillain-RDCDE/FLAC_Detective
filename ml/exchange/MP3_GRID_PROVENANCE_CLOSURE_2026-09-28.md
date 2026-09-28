# Rule 16's genuine counter-examples, closed on provenance — 2026-09-28

Follows `MP3_GRID_REGISTRATION_2026-09-27.md` (its provenance review) and
`V2_GENUINE_COUNT_CORRECTION_2026-09-27.md`. The question: can Rule 16 (the MP3
granule grid) be given points? It depends on what the files that read a grid
while labelled genuine really are. Everything below is documentary or a probe
of a public stream; **no engine reading becomes a label**, and the rulings go
through `ml/wild_fake_ledger.json` in its own schema.

---

## pachy 2025-07-31 (two tracks of the wild genuine set) — now `undecided`, out of the genuine population

* The band's own archive.org upload: "Source: SBD (Live Radio performance
  recorded to Audacity)". **The only one of the uploader's 48 items with no
  recording device in its chain**; the other 47 name a Tascam DR-05x or a
  Zoom H5 (one: "SBD > Tascam DR-05x > Audacity").
* The station, WPPM-LP 106.5 Philadelphia, broadcasts digitally as an **MP3
  stream at 192 kbps** — radio-browser.info, and the stream itself probed on
  2026-09-28: `mp3, 192000 b/s, 44100 Hz, stereo`. FM could not have carried
  the 18.75 kHz content the files hold.
* Side channel only: the engine reads an 18,750 Hz wall, a FLAC-equivalent size
  of 566 kbps (a LAME 192 decode's), and a Rule 16 grid of 8.3-8.6.

No lossy link is *admitted*, so no basis in the ledger's list carries a fake.
Ledger: `label: undecided`, `basis: null`, `selection: detector` (Rule 16 is
why they were read), note with the evidence above. Files moved to
`wild_authentic_undecided/`; the wild genuine population is **146**.

## Mondkopf, *Summer afternoon on the Caribbean sea* — stays genuine; recorded as a probable hybrid

Pressed CD (Annexia Records, `Annexia.03 CD`), XLD secure rip, AccurateRip OK.
Rule 16 on the twelve tracks of the disc: **11 read 1.22-1.35, track 7 reads
8.09**. One track of an otherwise clean disc carries an MP3 grid: the likeliest
story is a track mastered from an MP3, the "hybrid" class of the Set C
proposal. Nothing public documents the mastering, so it stays genuine.

## The library, measured — why Rule 16 gets no points

All 564 tracks of the unlabelled populations (library sample, Dust-to-Digital,
Awesome Tapes From Africa) with an edge under 0.95 × Nyquist:
**56 read a grid ≥ 1.6** (the list is in the bench folder,
`fd-mp3grid/unl_flagged.txt`).

| | tracks | album has a rip log | log with an AccurateRip match |
|---|---|---|---|
| grid ≥ 1.6 | 56 | 8 (14 %) | **3 (5 %)** |
| grid < 1.6 | 508 | 123 (24 %) | **71 (14 %)** |

Grid-reading tracks are about three times less often part of a disc the owner
ripped and verified — consistent with MP3-sourced downloads among them (a 1998
live bootleg, folders named "(FLAC)", Bandcamp issues of digitised tapes), and
not proof of it. But three of the 56 **are** AccurateRip-verified pressed
CDs: Mondkopf track 7 (8.09) and two Dust-to-Digital 78 rpm restorations
(3.53, 1.64).

**Points for Rule 16 are refused, finally.** They would reduce the halves'
disagreement (a simple re-tiering of the after-pass gives 12 → 8 of 44 at
+30, 12 → 4 at +50), and they would signal documented pressed-CD tracks and
about one edged library track in ten whose provenance nobody can settle.
Rule 16 stays a zero-point witness; as such it cannot reach any of these
files (0 library tracks sit at the conviction bar on one family).

## Where the halves stand, and why this closes

12 of 44 disagree after 1.19.0. The remainder is Rule 1's +50 and the CNN's
+30 landing in one half only, on readings where some MP3 decodes and some
genuine files are indistinguishable for every instrument this engine has
(`POSITION_REMAINDER_REFUSED_2026-09-26.md`), and the one new instrument that
tells them apart reads a grid on documented genuine discs too. What would move
it is provenance, not an engine change: if the owner of the flagged tracks can
say which are downloads, those become labels, and points for Rule 16 get a
registration of their own.
