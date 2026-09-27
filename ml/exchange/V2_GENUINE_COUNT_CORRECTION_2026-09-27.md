# Correction: the "v2 genuine" column of five documents held three files that are not genuine — 2026-09-27

Found while reviewing the provenance of the files Rule 16 reads
(`MP3_GRID_REGISTRATION_2026-09-27.md`). **No criterion's outcome changes**;
counts do, and they are corrected here rather than in the documents, which keep
saying what they said when they were committed.

## What happened

The bench folder `fd-r8/v2_genuine` (built 2026-09-25) took every file the raw
v2 key labels `genuine` — 59. The v2 key was adjudicated on 2026-08-23
(`fd-exchange-v2-2026-08-ADJUDICATIONS.json`, archive.org lineage, the MiniDisc
method) and three of those 59 are not genuine:

| file | adjudication (2026-08-23) |
|---|---|
| `fd-exchange-v2-2026-08-0197` | **fake** — taper's source line `Sony PC100 > AVI > MP2 > WAV > FLAC` |
| `fd-exchange-v2-2026-08-0386` | **unverifiable** — `lineage_unknown` ("unknown > CDR", taper unknown) |
| `fd-exchange-v2-2026-08-0469` | **unverifiable** — `device_ambiguous` (Zoom H1n, WAV or MP3) |

The labelled v2 genuine population is **56**. The folder was built from the key
and not from the adjudications; that is the whole error.

## What it changes, document by document

Every document below counted the three as genuine. That is the conservative
direction for their safety criteria (a genuine file that moves toward
accusation breaches them), and none of the three moved in any of them, so
**every safety criterion stands as reported**. What changes is the size of the
populations and one reading:

| document | as written | corrected |
|---|---|---|
| `LOW_WALL_REGISTRATION_2026-09-25.md` | v2 genuine 59; "0 genuine newly signalled on 203" | v2 genuine 56 (+ 1 fake, 2 unverifiable, none moved); 0 on **200** |
| `STEREO_SPREAD_REGISTRATION_2026-09-25.md` | v2 genuine 59, convicted 2 → 2 | 56 genuine, convicted 1 → 1 (`0362`, the known genuine false conviction); `0386` (unverifiable) convicted 1 → 1 |
| `POSITION_REMAINDER_REFUSED_2026-09-26.md` | "v2 genuine" among the 60 s corpora | the three rulings stand; no reading quoted there comes from the three files |
| `MP3_GRID_REGISTRATION_2026-09-27.md` | "291 further labelled genuine … every file under 1.50 except three"; "four genuine-labelled files" | **288** genuine, every one under the 1.6 bar except **two** (pachy ×2); and "under 1.50" was itself off by one file: the highest ordinary genuine reads **1.503** (TST 2026-08-08, *Hotel Columbo*), under the bar by 0.10. **Three** genuine-labelled files read a strong grid (Mondkopf, pachy ×2) and **one** unverifiable (`0386`) |
| `CHANGELOG.md` v1.17.0 / v1.19.0 | "0 genuine … on 203"; "four genuine-labelled files … one v2 genuine file" | 200; three genuine files and one unverifiable one (a correction entry is added to the CHANGELOG) |

## The fix

`fd-r8/v2_genuine` now holds the 56; the three are moved to
`fd-r8/v2_adjudicated/` with their rulings in its README. Any future bench
that wants "v2 genuine" reads the adjudications, not the key.
