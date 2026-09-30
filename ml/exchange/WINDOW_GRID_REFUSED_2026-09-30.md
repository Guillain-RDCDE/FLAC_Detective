# Rule 1's container window yielding to the MP3 grid: refused on its derivation — 2026-09-30

**Nothing here was registered and then run.** The candidate was priced offline
on the engine's own readings and failed the criterion every registration in
this folder carries first: no file that is not a known transcode may move toward
accusation. Recorded so the afternoon is not spent twice.

## Where this comes from

The same controlled bench as `HISS_OVER_SILENCE_REGISTRATION_2026-09-30.md`:
33 CD tracks of loud 2004 hard house, encoded with ffmpeg `libmp3lame` CBR 128
and decoded back to FLAC. Two of the three misses of 1.19.0 without torch leave
Rule 1 at the container window, on the high side:

| file | cutoff | step across the edge | floor above | FLAC-equivalent size | 192 cell window |
|---|---|---|---|---|---|
| mp3_128 t02 | 16,500 Hz | 31.8 dB | −53.1 dB | 959 kbps | 500-750 |
| mp3_128 t15 | 16,750 Hz | 46.5 dB | −57.5 dB | 983 kbps | 500-750 |

Hard walls, but a floor just above `DEEP_FLOOR_DB` (−58), so the depth gate of
1.13.16 does not override the window; a loud, dense master compresses above
the window whatever its history (the container-window cliff named by the
WALL_GATE registration). With torch live the CNN still flags t02 (WARNING 47).

`POSITION_REMAINDER_REFUSED_2026-09-26.md` closed step and floor as separators
here and said what it would take: *a second instrument, independent of the
cutoff*. Since 1.19.0 the engine has one, Rule 16's MP3 granule grid. The two
misses read **17.2 and 17.4**; the bench's 33 CD sources read 1.20-1.34.

## The candidate

When Rule 1 would exit because the container is **over** its window, and the
edge is a wall (step ≥ `WALL_MIN_STEP_DB`, 12 dB), read the grid; at or above a
bar, the window yields and the +50 stands.

## Derivation

All 38 full-length files of `fd-r1w/trace_gen.csv` (4,251 tracks) that exit
Rule 1 over the window today. **All 38 are unlabelled** (library sample,
Awesome Tapes From Africa, Dust-to-Digital); no labelled genuine and no
transcode exits there. Grid read by `grid_peak_ratio`, the Rule 16 instrument,
on the full decode.

| grid bar | files given the +50 | which |
|---|---|---|
| 1.6 (`GRID_BAR`) | 11 | 7 ATFA (DJ Katapila ×2, Papé Nziengui, DJ Black Low ×3, Teno Afrika) + 4 library |
| 3.0 | 7 | 3 ATFA + 4 library |
| 6.4 (over every ATFA reading) | 4 | library: Rone, 18h15, Fakear, Neat Beats |
| 8.6 (over every genuine grid on record) | 3 | library: Rone (13.71, step 39.1 dB), Fakear (10.44, 33.4 dB), Neat Beats (12.75, 37.7 dB) |
| 10.0 | 3 | the same three |

The strongest genuine grid on record is Mondkopf track 7 at 8.09 (pressed CD,
AccurateRip), 8.57 counting the wild file now `undecided`
(`MP3_GRID_PROVENANCE_CLOSURE_2026-09-28.md`). A bar set above the genuine
population is the principled one, and it still gives the +50 to three library
tracks with hard walls whose provenance nobody can settle. Only a bar above
13.71 is clean on these 38 files, and the two misses sit at 17.2: choosing 14
would be choosing the number that separates this bench from this library.

**Refused.** The two files stay a limit of what this engine reads: a hard wall
over a −53 to −57 dB floor, loud enough to leave the window, and a grid, is
what Rone, Fakear and Neat Beats also show. The CNN is the reading that
reaches them today.
