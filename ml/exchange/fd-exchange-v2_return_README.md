# fd-exchange-v2 — FLAC Detective's return: the key, the adjudications, the evidence columns

Sent 2026-08-23 after Provir's verdicts arrived (sha256 42d0e7a424fad5ae...). Nothing here left this machine before.

## fd-exchange-v2-2026-08-LABELS.json — the answer key, as frozen
`labels[id] = {label, source_slug}`; 59 sources x 10 arms (genuine, mp3_192, mp3_320, mp3_V0, aac_ff128, aac_ff256,
aac_ff320, aacmf_256, opus_256, vorbis_q8). Arms are ffmpeg 8.1 encodes decoded by ffmpeg (phase 0 by construction for
the MP3 arms); the source_slug names the Live Music Archive item.

## fd-exchange-v2-2026-08-ADJUDICATIONS.json — what the key got wrong, read off the items' own metadata
One "genuine" is a taper-documented MP2 chain (0197 -> fake); two have no verifiable lossless provenance (0386 unknown > CDR;
0469 Zoom H1n, format unstated) -> unverifiable, excluded from the genuine denominator. 56 verified genuine remain.
Read these BEFORE scoring yourself on the genuine tier.

## fd-exchange-v2_columns_flacdetective.csv — engine pass (FLAC Detective 1.13.0, deep, CNN on)
file, bytes, engine_version, score (0-150), verdict (AUTHENTIC / WARNING / SUSPICIOUS / FAKE_CERTAIN),
evidence_families (independent families accusing; a conviction needs two; witness families stereo/temporal appear
with zero points by design), score_breakdown (JSON, points per rule), hires_verdict, sample_rate, bit_depth,
cutoff_hz (the wall, 250 Hz grid), cutoff_std_hz (wall wander across windows), energy_ratio (above the wall),
residual_floor_db (near-Nyquist depth reading, NaN where not computed), container_kbps (bytes*8/seconds),
stereo_run (Rule 15: side-channel dead-run median, bar 2.0), seam (Rule 14: temporal-variability drop, bar 0.60).

## fd-exchange-v2_idem_flacdetective.csv — idem pass (libmp3lame 3.100 via ffmpeg, CBR 320, files never pipes)
idem_R_phase0, idem_R_best_canonical (minimum over phases {0, 529, 47}), idem_best_phase. 60-s excerpt from sample 0.
Ten rows NaN: the one 96 kHz source's arm (probe reads 44.1/48 only). No full 576 search here - canonical phases only.

## sha256
5735caa83e677ba6159680ce301245f29a8ba71c053c43d407bbccc850f322c6  fd-exchange-v2-2026-08-ADJUDICATIONS.json
c5571d397589d02434a3ca42e1765c636e7c694ac1c514fc72cc531014e3ec1e  fd-exchange-v2-2026-08-LABELS.json
e5e6f0b74618c2fc83681a6241b3b9f15f1e34a59b79db002ebf313b041aaa2d  fd-exchange-v2_columns_flacdetective.csv
bfdd492a778d9500c6743d6bba0881e0caba201049276452b8772cce93bce291  fd-exchange-v2_idem_flacdetective.csv
