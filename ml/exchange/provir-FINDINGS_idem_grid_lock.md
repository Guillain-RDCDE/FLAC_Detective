# FINDINGS 2026-08-21 (22:25) — THE IDEM FIXED POINT IS GRID-LOCKED: period 576 samples, zero tolerance

**Found while chasing a mis-read.** LAME 3.99.1 (built tonight from the owner's tarball) read 0/72 on the V0 era bench with a
median of 3.02 — *above* lossless — while 3.99 and 3.99.2 read 42/72 at 0.28. The encoder is the same (LAME's own history says
3.99.1 changed only ID3v2 tag handling). The difference was the **extended Xing tag: 3.99.1 writes the version string `L3.99`
instead of `LAME3.99`**; ffmpeg keys gapless trimming on that string, so 3.99.1 output decodes UNTRIMMED — 1,105 samples late
(576 encoder delay + 529 decoder delay), 1,800 samples longer. Controlled test: the 3.99.2 file with the four bytes `LAME`
overwritten by `L3.9` — identical audio — reads **6.80 instead of 4.33, to three decimals the same as 3.99.1's read.**

**Then the experiment that matters (`idem_phase_search.py` notes; scratch, one file, two probes):** the same decoded 3.99.2 V0
file under the mp3_V0 probe, cropped k samples from the start:

| k | 0 | 1 | 8 | 32 | 96 | 144 | 288 | 432 | **576** | 720 | 864 | 1008 | 1105 | **1152** | 1153 | **2304** | 2305 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R_b03_16k | **4.33** | 7.14 | 6.96 | 6.77 | 7.05 | 7.05 | 6.60 | 6.91 | **4.35** | 7.08 | 6.71 | 6.90 | 6.89 | **4.31** | 7.13 | **4.33** | 7.12 |

Same shape on the CBR-320 probe with a LAME-320 arm (0.65 at 0/576/1152, 1.05–1.16 at 1/288/1105), and for the UNTRIMMED decode
of that file the aligned crops are **529 / 1105 / 1681** (0.64–0.67) while 0 / 576 read 1.09–1.12.

## What it means

1. **R measures the fixed point ONLY when the arm's sample grid coincides with the original encode's granule grid.** One sample
   off and the file reads lawful. Period 576 (one MDCT granule, not the 1152 frame). There is no tolerance band.
2. **Every fixture row we hold is the best case**: arms are ffmpeg decodes of our own tagged encodes → phase 0 by construction
   (V0-end, MP3_IDEM, the ACM row, the cross rows, the lawful pricings — the lawful population too: lossless masters have no
   grid, so their reads are phase-free, which is why the null is stable).
3. **The wild reads at an unknown phase.** A headerless file (Fraunhofer, Xing, iTunes-CBR, any stripped file), or any file
   decoded by a decoder that does not strip the encoder delay — the converter tool, WMP, most 2000s software — sits at phase 529;
   a trimmed, re-wrapped, DAW-edited, resampled, crossfaded file sits anywhere. **This is the wild-recall gap in one sentence**
   (wild V0 27% vs fixtures 57%; Walsh 0/14; the 08-07 lattice "grid fragility"; the converter tool's silence trim).
4. **Family-locking survives the correction** (three stems, 22:30): a LAME-320 arm decoded untrimmed drops under the LAME-320
   probe from ~3.4 to 0.56–2.2 once cropped to phase 529/1105, while ACM-320 and FhG-3.1-320 arms stay at 1.6–4.3 at every
   phase. "A Fraunhofer file needs a Fraunhofer probe" is real. The reverse rows (LAME arms under the ACM probe) were at phase 0
   already (trimmed decodes) and stand.
5. **The SQUAD-E attribution is being re-checked at the best phase** — if the twelve read low under a LAME probe at SOME phase,
   they are LAME after all and the ACM read was phase luck; if they stay high under LAME at every phase and low under ACM, the
   Fraunhofer-ACM-320 attribution stands (running 22:33: all 576 phases, mp3_320 and mp3_128).

## What it changes in the instrument

- **A phase search is part of the idem read from now on.** Cheap form: the three canonical phases {0, 529, 47}. Full form: all 576
  phases on a 4-s excerpt by d1 alone (one probe encode per phase), then the full R at the best — ~90 s per file per probe.
  `idem_phase_search.py` does both. Wiring it into idemlib.idem as `phase='canon'|'full'` is the next instrument change.
- The lawful pricings do not need re-running for the fixture-vs-lawful question (lossless has no grid), but **every wild
  number** — the 27%, Walsh, Guillain's W-series on the 53, the FhG-consistent "lawful-like" reads — must be re-read at the best
  phase before it is quoted again, and the claims register gets the caveat.
- Tag DNA gained a tell: `L3.99` in the extended Xing tag = LAME 3.99.1 (5–18 Nov 2011); such files decode untrimmed everywhere.

## Why it was invisible until tonight
Every arm and every probe was built by the same ffmpeg, which trims what it tagged. The first untrimmed arm to enter the bench was
a build whose tag ffmpeg did not recognise. [[instrument-integrity]]: a positive control that enters by the real door is exactly
what catches a convention nobody wrote down — "phase 0" was one.
