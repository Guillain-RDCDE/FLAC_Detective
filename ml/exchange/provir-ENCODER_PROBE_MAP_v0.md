# ENCODER × PROBE RESPONSE MAP — v0 (2026-08-21, derived from ledgers on disk)

**What this is.** For every emitter-config the idem sweep measured (`idem_sweep.jsonl`, manifest =
the 2026-08-12 emitter sweep), the **median R_b03_16k** under each LAME-3.100 CBR probe
(`idemlib.PROBES` mp3_128 / mp3_192 / mp3_320), beside the lawful population under the same probes.
LOW = the file sits at that probe's fixed point (re-encoding moves it little). The "map" the owner
asked for on 2026-08-21 ("once we have all the encoders, map them — Guillain might benefit too") —
this is the v0 that existing data supports; v1 adds the FhG / Xing / Helix probes once those
encoders exist as probe rungs, and the V0/VBR probes.

**Read it like this.** The tell is a MATCH between the probe's quantiser generation+mode and the
file's. Diagonal cells (probe rate = file rate, probe encoder ≈ file encoder) are where it fires.

```
emitter (rate)            mp3_128 probe   mp3_192 probe   mp3_320 probe      n/cell
LAWFUL (309 files)            4.69            3.00            3.14
lame3.100.1  128/192/320      0.27 /  4.36 /  4.92     1.13 /  0.58 /  3.09     3.83 /  2.47 /  1.14   6
lame3.99.5   128/192/320      0.27 /  4.38 /  4.95     1.14 /  0.56 /  3.11     3.95 /  2.46 /  1.21   6
lame3.98.4   128/192/320      1.49 /  4.82 /  4.93     1.22 /  1.72 /  3.22     3.15 /  2.60 /  2.03   6
wb_lame3.97  128/192/320      1.42 /  4.67 /  4.92     1.36 /  1.71 /  3.13     3.02 /  2.65 /  1.94   6
lame3.96.1   128/192/320      1.35 /  4.34 /  4.89     1.38 /  0.98 /  3.15     3.39 /  2.66 /  1.58   6
lame3.93.1   128/192/320      1.12-1.27 / 4.0-4.5 / 4.9   1.17-1.43 / 1.95-2.08 / 3.0-3.1   3.7-3.8 / 2.5 / 1.75-1.79   6
lame3.92     128/192/320      1.57 /  4.47 /  4.92     1.43 /  2.12 /  3.11     3.40 /  2.54 /  1.76   6
lame3.90.3   128/192/320      1.34 /  4.19 /  4.99     1.21 /  1.92 /  3.03     3.61 /  2.41 /  1.53   6
helix_mp3    128/192/320      2.68 /  3.90 /  4.84     2.73 /  3.00 /  3.28     3.63 /  3.04 /  2.83   11-12
bladeenc 0.91-0.94.2 (128/192/320)  3.30 / 4.05 / 4.90   2.55-2.83 / 2.55-2.63 / 3.1   3.0 / 2.9 / 2.55   3-5
faac / nero (all) / exhale / vorbis / opus (all)   ≈ lawful under every mp3 probe (codec-paired, as expected)
```
(cells read "file@128 / file@192 / file@320" under the column's probe; full table: `fhg_family_check.py`
prints the lawful thresholds; the raw matrix script is in this commit's message trail.)

**What it says (v0, constructed fixtures, n = 3–20 per cell — a MAP, not a claim):**
1. **LAME 3.99/3.100 is the probe's own generation**: the diagonal reads 0.27 / 0.57 / 1.1–1.2
   against lawful 4.69 / 3.00 / 3.14 — the tell at full strength at every CBR rate.
2. **Generation decay is milder at CBR than at V0.** At CBR 320 the 3.90–3.93 era still reads
   1.53–1.79 (below lawful's 3.14 median, though inside its lower tail: lawful q01 1.415 / q05 1.72);
   this morning's V0 era bench had the same generations DEAD (0/72 at 1%). VBR mode-pairing is
   the harder constraint.
3. **The 128 probe has the widest lawful margin** (lawful 4.69): every LAME generation at 128 reads
   0.27–1.57, Helix 2.68, BladeEnc 3.30 — at low rates the tell is nearly family-agnostic.
4. **Other mp3 families are NOT at LAME's fixed point**: Helix ≈ lawful at 192/320; BladeEnc mildly
   low (2.5–2.6 vs 3.0–3.1) — family-locked, consistent with the V0 version-locking. ⇒ full
   1995–2026 coverage needs FAMILY probes (FhG via `l3codeca.acm` — the cracked MP3Enc 3.1 in
   era_encoders is EXCLUDED per ENCODER_REGISTER; Xing; Helix exists as an emitter and can be a
   probe), not only LAME generations.
5. **Non-mp3 codecs read lawful under mp3 probes** — the codec-pairing result, again.

**Caveats:** constructed fixtures (the emitter sweep's 3 sources/cell ladder), LAME-3.100 probes
only, one 60-s window, no VBR probes in this ledger. The wild FhG-consistent check
(`fhg_family_check.py`, E:\ calibration) adds the first real-file FhG row under mp3_320/mp3_V0.

**Sharing plan (owner, 2026-08-21):** encoders + this matrix go to Guillain's Drive folder once
the encoder set is complete — measurement of public encoders is MECHANISM, not calibration
([[open-core-calibration-split]]: fitted thresholds stay; response matrices travel).

## v0.1 ADDENDUM (2026-08-21 18:45) — new-family rows, and the column the map was missing: DIRECTION

`newfam_map_row.py` (72 lossless_ctrl stems, 60-s excerpts, arms built in memory; 0 errors):

```
arm            | ac3_320 probe | ac3mf_256 probe | wmav2_192 probe | mp3_320 | mp3_V0 | aac_256
lossless_ctrl  |   0.71        |   3.09          |  16.40          |  3.11   |  3.05  |  1.13
ac3_320        |   8.23 ⚠      |     -           |     -           |  3.01   |  3.16  |  1.26
ac3mf_256      |   8.83 ⚠      |   1.89          |     -           |  2.92   |  3.06  |   -
wmav2_192      |     -         |     -           |   3.74          |  3.36   |  2.48  |  1.44
```
AUC (arm reads LOWER than lossless, same probe): ac3_320 × ac3_320 **0.022 = INVERTED** (matched
pairs arm > ctrl 68/72, median +7.72 dB) · ac3mf_256 × ac3mf_256 **0.915 normal** · wmav2_192 ×
wmav2_192 **0.970 normal** (enormous: 16.4 vs 3.74) · cross-family: ac3 under mp3_320 0.491 (= lawful),
wmav2 under mp3_V0 0.624 (mild).

⭐ **ffmpeg's AC-3 converges one pass LATER than LAME.** For a lossless input the first and second
AC-3 passes move the audio by about the same amount (d1 ≈ d2 → R ≈ 0); for an already-AC-3 input the
next pass still moves it a lot and the one after barely (R ≫ 0). Separable — but with the OPPOSITE
sign to every mp3 cell. ⇒ **Every probe row now carries its DIRECTION**; a single "lossy reads low"
threshold across probes would convict the wrong side on AC-3. [[kill-conditions-must-test-one-thing]]:
state what the control reads, per probe. Microsoft's MF AC-3 is one-pass idempotent (normal); wmav2
is strongly one-pass idempotent (the lossless first pass is very expensive).
Cross-family: AC-3 and WMA files look LAWFUL to the LAME probes — codec-pairing, one more family.
Caveats: constructed fixtures; ffmpeg's encoders (ac3, wmav2) and Microsoft's MF AC-3 — not every
AC-3/WMA encoder in the wild (Dolby's own, WMP's own WMA) — and wmav2 at "192" emits ~276 kbps.

## v0.1 ADDENDUM (19:10) — the first FRAUNHOFER rows: arm AND probe (fhg_idem_row.py, 72 stems, 30-s excerpts)
```
arm            | fhg31_128 probe | fhg31_320 probe | mp3_128 (LAME) | mp3_320 (LAME)
lossless_ctrl  |   7.82          |   0.16          |   4.52         |   3.02
fhg31_128      |   0.81  ✓       |   0.17          |   2.81         |   3.45
fhg31_320      |   7.85          |   0.09          |   4.36         |   3.27
AUC: fhg31_128×fhg31_128 0.987 · fhg31_320×fhg31_320 0.701 · fhg31_128×mp3_128 0.804 · fhg31_320×mp3_320 0.452
```
- **The fixed-point mechanism holds for Fraunhofer at 128** (self-pairing AUC 0.987 — as strong as LAME's).
- **At 320 the FhG-3.1 probe barely converges in one pass** (lossless reads 0.16 — the AC-3 species of
  behaviour, weak self-probe, AUC 0.70); FhG-320 is better read by its bandwidth signature than by idem.
- **Cross-family:** the LAME-128 probe half-sees an FhG-128 file (0.80 — the wide 128 margin again);
  the LAME-320 probe reads FhG-320 as lawful (0.45) — the wild FhG check, reproduced on constructed files.
- 30-s excerpts (demo limit): this run's own lossless cell is the null; not comparable to the 60-s
  lawful thresholds.

## v0.2 ADDENDUM (20:32) — the SECOND Fraunhofer generation: Windows' professional ACM codec 3.4 as arm AND probe (fhgacm_idem_row.py, 72 stems, 30-s excerpts)

Median R_b03_16k (lower = nearer the probe's fixed point); null = lossless_ctrl under the same probe.

arm            | fhgacm_128 probe | fhgacm_320 probe | mp3_128 (LAME) | mp3_320 (LAME)
---------------|------------------|------------------|----------------|---------------
lossless_ctrl  |   2.45  (null)   |   1.39  (null)   |   4.52 (null)  |   3.02 (null)
fhgacm_128     |   0.37  ✓        |   0.06  ✓        |   2.82         |   3.41
fhgacm_320     |   2.44           |   0.08  ✓✓       |   4.32         |   3.23
AUC (arm below null): fhgacm_128×fhgacm_128 **0.974** · fhgacm_320×fhgacm_320 **0.999** · fhgacm_128×fhgacm_320 0.993 ·
fhgacm_128×mp3_128 0.804 · fhgacm_320×mp3_320 **0.450** · fhgacm_320×mp3_128 0.520 · fhgacm_320×fhgacm_128 0.492

- **The ACM 3.4 codec self-pairs at 320 (AUC 0.999, 0.08 vs null 1.39)** — unlike the 1998 demo, whose 320 was nearly transparent
  to its own probe (0.70). A WMP-era Fraunhofer 320 rip — the wild headerless-CBR class — has a STRONG same-encoder fixed point;
  the probe is a system binary every Windows has. This is the lattice-leg candidate for that class (pricing on lawful still owed).
- ⚠ The 320 probe also pulls the 128 arm to 0.06 (AUC 0.993): part of that is the generic "heavily quantised reads low under a
  higher-rate probe" response ([[v0-end-idem-version-locked]]) — attribute only from the SELF cell (128×128 0.974), never from the
  cross cell.
- **Family-locked, second generation confirmed:** the LAME-3.100 320 probe is BLIND to ACM-320 (AUC 0.45) and half-sees ACM-128
  (0.80 = the generic 128 margin, identical to the 3.1 demo's 0.80). Same shape as the 1998 row: a Fraunhofer file needs a
  Fraunhofer probe.
- Direction: normal (arm BELOW null) on every cell. Not yet run: cross-generation (3.1 arms under the 3.4 probe and vice versa) —
  the attribution question; cheap, same stems.

## v0.3 ADDENDUM (21:55) — the cross-family square closed, and the SQUAD-E tail probed on four axes

Under the Fraunhofer-ACM-3.4 probes (72 stems, 30-s; lawful minima from the clean n=596 pricing: fhgacm_320 0.209, fhgacm_128 −0.219):

arm            | fhgacm_320 (med · below min / below q01) | fhgacm_128 (med · below min / q01)
---------------|------------------------------------------|------------------------------------
lossless_ctrl  | 1.39 · 0 / 2                             | 2.45 · 0 / 0
mp3_128 (LAME) | **0.09 · 50 / 69**  ← generic ~128k pull  | 1.51 · 0 / 1
mp3_320 (LAME) | 0.89 · 1 / 10       ← family-locked       | 2.46 · 0 / 0
fhg31_320      | 0.72 · 2 / 13       ← generation-locked   | 2.36 · 0 / 1
fhgacm_320     | 0.08 · 69 / 72      (self)                | 2.44 · 0 / 0
fhgacm_128     | 0.06 · 44 / 68                           | 0.37 · 0 / 8 (self)

- **Matched-rate family-locking holds both ways now** (LAME probes blind to FhG arms; the ACM probe blind to LAME-320 and FhG-3.1-320).
- **The cross-rate generic pull is real and large**: any ~128k MP3 falls under the ACM-320 probe. An ACM-320 leg therefore needs the
  `mp3_128` probe as its disambiguator (LAME-128 at its own fixed point ~0.2 there; ACM-320 reads ~4.3).
- **SQUAD-E tail (12 files), four probes**: mp3_128 1.8–7.3 · mp3_320 3.1–4.9 · fhgacm_128 1.8–3.7 · fhgacm_320 0.015–0.126 —
  the ACM-320-arm pattern, no other. Named family: Fraunhofer ACM-generation 320 kbps (WMP-era).
- Direction: normal on every cell. Still owed: wild replication on the E:\ headerless-CBR class (calibration only); a 60-s pricing if
  the leg is ever wired (these are 30-s numbers).
