# Technical Details

Deep dive into FLAC Detective's architecture, detection algorithms, and rule system.

## Table of Contents

- [System Architecture](#system-architecture)
- [Supported Formats](#supported-formats)
- [Repair: lossless reconstruction, only when needed](#repair-lossless-reconstruction-only-when-needed)
- [Detection Rules](#detection-rules) (Rules 1–11 + optional ML Rule 12)
- [Scoring System](#scoring-system)
- [Spectral Analysis](#spectral-analysis)
- [Performance Optimizations](#performance-optimizations)
- [Technical Limitations](#technical-limitations)

## System Architecture

### High-Level Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │  Input: files / folders (scanned recursively)                │
 │  .flac   .wav   .m4a   .ape   (+ any other audio it finds)   │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Scanner / Router          (main.scan_files)                 │
 │   • .flac / .wav            → analyse (read natively)        │
 │   • .m4a / .ape → ffprobe ──┬─ ALAC / APE → analyse          │
 │                             └─ AAC / lossy → reject          │
 │   • .mp3 / .ogg / .opus / … → reject ("not lossless,         │
 │                                        replace with a FLAC") │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼   one analysable file
 ┌──────────────────────────────────────────────────────────────┐
 │  Decode to local temp      (analyzer.analyze_file)           │
 │   • FLAC / WAV → copy-to-temp, read by libsndfile            │
 │   • ALAC / APE → ffmpeg decode → temporary WAV               │
 │   ↻ on read failure: auto-repair via `flac` CLI, then retry  │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Feature extraction  (one shared AudioCache — the temp file  │
 │  is read once and reused by every step below)                │
 │   • Metadata     sample rate, bit depth, channels, duration  │
 │   • Spectral     FFT → cutoff freq, energy ratio, stability  │
 │   • Quality      clipping, DC offset, silence, fake hi-res,  │
 │                  upsampling, corruption                      │
 │   • Duration     metadata vs decoded (consistency check)     │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Scoring engine     (new_scoring/calculator.py)              │
 │  12 heuristic rules + optional CNN (Rule 12) → 0–150 pts     │
 │  phased execution with gates & short-circuits — see below    │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Verdict        (single source of truth: constants.py)       │
 │  ≤30 AUTHENTIC · 31–54 WARNING · 55–85 SUSPICIOUS · ≥86 FAKE │
 └────────────────────────────────┬─────────────────────────────┘
                                   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  Reporting:  Rich console  ·  text report  ·  JSON           │
 │  (all derive the verdict from the thresholds above)          │
 └──────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. File Scanner (`flac_detective/utils.py`)

Recursively finds FLAC files in directories.

**Key features**:
- Recursive directory traversal
- `.flac` extension filtering
- Symbolic link handling
- Error recovery for inaccessible files

#### 2. Metadata Reader (`flac_detective/analysis/metadata.py`)

Extracts FLAC metadata using the Mutagen library.

**Extracted information**:
- Sample rate (Hz): 44100, 48000, 96000, etc.
- Bit depth: 16, 24, 32
- Channels: 1 (mono), 2 (stereo)
- Duration (seconds)
- Encoder information

#### 3. Audio Loader (`flac_detective/analysis/audio_cache.py`)

Loads audio data with intelligent caching.

**Features**:
- Configurable sample duration (default: 30s)
- Memory-efficient caching
- Multiple backend support (soundfile, ffmpeg fallback)
- Automatic retry on corruption

#### 4. Spectral Analyzer (`flac_detective/analysis/spectrum.py`)

Performs FFT (Fast Fourier Transform) analysis.

**Computed metrics**:
- Cutoff frequency (Hz)
- Energy distribution
- Frequency variance
- Spectral density patterns

**Algorithm**:
```python
# Simplified spectral analysis flow
audio_data = load_audio(file, duration=30.0)
fft_result = np.fft.rfft(audio_data)
magnitude = np.abs(fft_result)
frequencies = np.fft.rfftfreq(len(audio_data), 1/sample_rate)

# Find cutoff frequency (where energy drops significantly)
cutoff_freq = detect_cutoff(magnitude, frequencies)
```

#### 5. Scoring Engine (`flac_detective/analysis/new_scoring/`)

Strategy pattern implementation with 12 heuristic rules plus an optional CNN (Rule 12).

**Structure**:
```
new_scoring/
├── calculator.py        # Orchestrates rule execution
├── verdict.py           # Maps score to verdict
└── rules/               # Individual rule implementations
    ├── rule_01.py       # MP3 Spectral Signature
    ├── rule_02.py       # Cutoff vs Nyquist
    ├── ...
    ├── rule_11.py       # Cassette Detection
    └── ml_classifier.py # Rule 12 — optional CNN (ML), only with the [ml] extra
```

#### 6. Report Generator (`flac_detective/reporting/`)

Creates formatted output for users.

**Output formats**:
- Console (Rich library, colored, progress bars)
- Text file (detailed analysis)
- JSON (for automation)

### Data Flow

```
FLAC File
   │
   ├─► Extract Metadata
   │   ├─ Sample rate: 44100 Hz
   │   ├─ Bit depth: 16 bits
   │   └─ Duration: 245.3 seconds
   │
   ├─► Load Audio (30 seconds)
   │   └─ Audio array: [samples x channels]
   │
   ├─► Compute FFT
   │   ├─ Magnitude spectrum
   │   ├─ Frequency bins
   │   └─ Cutoff detection
   │
   ├─► Apply Rules 1-11
   │   ├─ Rule 1: +50 pts (MP3 signature detected)
   │   ├─ Rule 2: +15 pts (cutoff at 19.5 kHz)
   │   ├─ Rule 5: -10 pts (high variance protection)
   │   └─ Total: 55 pts
   │
   └─► Generate Verdict
       └─ Score 55 → SUSPICIOUS ⚠️
```

## Supported Formats

Detection is **codec-agnostic**: every rule operates on the decoded PCM samples, so the
container only decides *how the samples are read in*.

| Format | Extension | How it's read | ffmpeg needed? |
|---|---|---|---|
| FLAC | `.flac` | libsndfile (native) | no |
| WAV | `.wav` | libsndfile (native) | no |
| ALAC (Apple Lossless) | `.m4a` | decoded to PCM via ffmpeg | **yes** |
| APE (Monkey's Audio) | `.ape` | decoded to PCM via ffmpeg | **yes** |

The real codec is probed with `ffprobe` — the extension is never trusted. A `.m4a` that
turns out to hold **lossy AAC** is not analysed; it's reported as a non-lossless file to
replace, exactly like an `.mp3`. ffmpeg is a hard dependency **only** for ALAC/APE; a
FLAC/WAV-only workflow never invokes it. For lossless-*compressed* sources decoded to a
temporary WAV (ALAC/APE), the "real bitrate" used by Rule 1 is sized from the
**original compressed file**, not the decoded WAV — otherwise the file would look
uncompressed and the rule would wrongly switch off.

## Repair: lossless reconstruction, only when needed

Analysis is **read-only**. Since 2.0 that is true without exception: a scan writes
nothing into your library. When a FLAC is **so corrupted it cannot be decoded at all**,
even after the loader's retry/backoff, the tool rebuilds a **valid, byte-identical FLAC**
from whatever the audio data still allows *in the temp directory*, analyses that, and
discards it. Pass `--repair-in-place` to have the repaired file replace the broken one in
your library (a `.corrupted.bak` is kept beside it) — until 2.0 that replacement was the
default, which is not what a scan should do unasked. Either way, this is the opposite of
"tinkering with the sound": **nothing in the audio is processed, resampled, normalised or
'enhanced'.**

### Why it's lossless (the part that matters for hi-fi)

FLAC is a *lossless* codec: decoding a FLAC and re-encoding it yields the **exact same PCM
samples**, bit for bit. Repair uses Xiph's **reference `flac` tool** for both halves of the
round-trip, so the repaired file's audio is sample-identical to what the corrupted file
could still deliver. The corruption is in the FLAC *framing/container*, not in the PCM you
can still read; repair rebuilds correct framing around those exact samples. No psychoacoustic
processing, no dithering, no gain — none of the things a "repair" might scarily imply.

### The procedure (each step is verifiable)

```
corrupted .flac  ── can't be decoded after retries
   │
   1. extract metadata        (mutagen: all tags + embedded album art)
   2. decode → WAV            (flac --decode-through-errors: recover every
   │                            sample the corruption didn't destroy)
   3. re-encode WAV → FLAC     (flac --best: lossless, exact same samples)
   4. restore metadata         (tags + pictures put back, untouched)
   5. verify                   (flac --test: refuse to proceed unless the
   │                            rebuilt file is provably valid)
   6. analyse the repaired copy; with --repair-in-place ONLY, replace the
   │                            original (after a .corrupted.bak is written)
   ▼
 valid .flac  ── analysable; your library untouched unless you asked
```

### Safety guarantees

- **Nothing is written unless asked.** The repair happens on a temp copy; only
  `--repair-in-place` lets it replace the file in your library, and only a file that could
  not be decoded at all. Healthy music is read and left exactly as it is.
- **A backup is always kept** when it does replace. The original is copied to
  `<name>.flac.corrupted.bak` *before* anything replaces it — you can always go back.
- **Verified before trusted.** If the rebuilt file fails `flac --test`, repair aborts and the
  original is left untouched.
- **Metadata preserved.** Tags and embedded artwork are carried across verbatim.
- **Honest limit.** Samples that corruption genuinely destroyed can't be invented back —
  `--decode-through-errors` recovers everything still readable and no less. Repair never makes
  a file *worse* than the corruption already did; it makes a broken file *usable* again.

There are two entry points to the same lossless machinery:

- **Automatic**, during analysis — triggered only by the undecodable-file case above, on a
  temp copy; `--repair-in-place` to keep the result in your library.
- **Standalone**, `python -m flac_detective.repair /path` — a duration-header fixer for FLACs
  (since 2.0 it re-encodes at the file's own bit depth: a 24-bit file comes out 24-bit; until
  then its default setting wrote 16-bit)
  whose declared length disagrees with their actual decoded length (also a lossless re-encode,
  also with a `.bak` backup).

## Detection Rules

FLAC Detective uses **12 heuristic rules** with **additive scoring** (0–150 points), plus
an **optional CNN rule** (Rule 12, enabled with the `[ml]` extra — see below).

> **Population note (2026-08).** Every rate and AUC on this page was measured on **direct
> transcodes** — lossy audio re-encoded straight to FLAC. Transcodes that passed through a
> mastering chain before reaching a disc (the population wild compilations actually sell) read
> very differently: on 34 owner-attested wild MP3-sourced tracks, v1.11.4 signaled 8.8 %,
> v1.12.0 signaled 50.0 % (four lab-calibrated admission gates repaired), and v1.13.0
> signals 70.6 % (the residual window widened to feed gate C′) with the first two true
> convictions — both owner-attested fakes, corroborated by independent families. False
> convictions: zero, every version, every population. A published rate on this project now
> states which population it describes; the measurements and their pre-registered
> predictions live in the repository (`ml/exchange/PREREGISTERED_2026-08-20.md`,
> `ml/wild53_scores.csv`, `ml/wild53_scores_v112.csv`, `ml/wild53_scores_v113.csv`,
> `ml/r1_gates_repricing.py`).

### Scoring engine flow

**Order matters.** The rules don't just sum — the engine runs them in a deliberate order
with *gates* (that switch rules off when they'd misfire) and *short-circuits* (that stop
early once the answer is certain, skipping the expensive rules). This is both for accuracy
and for speed.

```
 cutoff freq · bitrate · metadata · audio ─►  ScoringContext  (mutable, shared)

 1. Rule 8   Nyquist exception        ── always first (refined later if MP3 found)
 2. Rule 11  Cassette detection       ── EARLY, only if cutoff < 19 kHz (protect rips)

    ┌─ Gates — these DISABLE the container-bitrate rules (1 & 3) ────────────────┐
    │   cassette detected (R11 ≥ 30)        → drop Rule 1, apply −40 protection  │
    │   uncompressed input  (real/apparent  → drop Rules 1 & 3                   │
    │     bitrate ratio > 0.92, e.g. WAV)     (no lossless-compression signal)   │
    └────────────────────────────────────────────────────────────────────────────┘

 3. PHASE 1 — fast rules, always run:   R1  R2  R3  R4  R5  R6
       │
       ├─►  score ≥ 86               →  FAKE_CERTAIN   (stop — skip costly rules)
       └─►  score < 10 and no MP3    →  AUTHENTIC      (stop)

 4. PHASE 2 — expensive rules, only when relevant (need the full decoded audio):
       • R7  silence / vinyl     if 19 kHz ≤ cutoff ≤ 21.5 kHz
       • R11 cassette            if cutoff < 19 kHz and not already run early
       • R13 MDCT alignment      if not already convicted (any cutoff, v1.20.1)
       └─ Rule 8 re-refined now that MP3 context is known
       └─►  score ≥ 86            →  FAKE_CERTAIN   (stop)

 5. Rule 10  multi-segment consistency   ── only if score > 30 (already suspect)
 6. Rule 12  CNN classifier (optional)   ── abstains if rolloff < 7 kHz;
                                            no-op unless installed with [ml]
       │
       ▼
   total score (0–150)  ─►  verdict
```

The rules themselves, in detail:

### Rule 1: MP3 Spectral Signature Detection

**Purpose**: Detect CBR (Constant Bitrate) MP3 patterns

**Detection method**:
- Analyzes cutoff frequency
- Matches against known MP3 bitrate signatures

**MP3 Bitrate Signatures**:
```
128 kbps MP3 → 16000-16500 Hz cutoff
160 kbps MP3 → 17000-17500 Hz cutoff
192 kbps MP3 → 19000-19500 Hz cutoff
256 kbps MP3 → 20000-20500 Hz cutoff
320 kbps MP3 → 20000-20500 Hz cutoff (with exceptions)
Authentic    → 22050 Hz (full spectrum)
```

**Scoring**:
- MP3 signature detected: **+50 points**
- Exception for high-quality MP3 320k: Some protection
- No signature: **0 points**

**Example**:
```
File with 19200 Hz cutoff:
→ Matches 192 kbps MP3 signature
→ +50 points
```

**Gate D — a slope is not a wall (v1.13.15).** The cutoff detector answers
*where* the spectrum first sits 30 dB under the 10-14 kHz reference. On a
codec low-pass that place is a wall: the level falls 20-40 dB inside 500 Hz.
On a master that was rolled off gently — issue #8, fourth round: two rips of
one track, both falling about 6 dB/kHz from 12 to 19 kHz — the same scan
reports 17,250 Hz and the table above turns that *position* into a "192 kbps
signature". The position cannot tell the two apart; the step across it can.
`analyze_spectrum` now also reports `edge_step_db`, the largest fall over two
adjacent 250 Hz cells within four cells of the edge, read on the window that
produced the cutoff. Under `WALL_MIN_STEP_DB` (12 dB) the edge is a slope and
Rule 1 exits with a reason line; a NaN (no edge found) passes, like an unknown
wander at gate A. Full-length LAME transcodes read 19-51 dB there; the
reporter's two files read 4.5 and 6.2 dB. The gate reads edges below the
320 kbps cell only (`WALL_GATE_MAX_HZ`, 19,500 Hz): from there up a LAME V0
low-pass and a genuine anti-alias roll-off are both soft steps, so the step
separates nothing, and the 320 branch already decides on the wall's depth
(the residual floor). The gate can only withhold the +50, never add it.
Measured in `ml/exchange/WALL_GATE_REGISTRATION_2026-09-08.md`.

**Gate A yields to depth (v1.18.0).** Gate A skips Rule 1 when the cutoff
read in the three 30 s windows of a file over 90 s wanders by more than
130 Hz. A 128 kbps wall at 16 kHz is read 250-500 Hz apart by windows of
different music, so full-length transcodes walked out through it. Over digital
silence (floor above the edge at or under −58 dB, edge under 19.5 kHz) the
wander no longer skips the rule, as gate D and the container window already
yield to depth. Priced on full-length tracks, since the gate needs three
windows: 0 change on 210 labelled genuine files (including 28 owner-ripped,
AccurateRip-verified CD tracks with cutoffs under 19 kHz) and 5 on 246
unlabelled library, 78 rpm and cassette tracks; convictions 46 → 61 on 84
full-length LAME transcodes of those CDs.
`ml/exchange/GATE_A_DEPTH_REGISTRATION_2026-09-26.md`.

---

### Rule 2: Cutoff Frequency vs Nyquist Threshold

**Purpose**: Penalize files with suspiciously low frequency content

**Detection method**:
1. **Slice-based cutoff detection** (primary)
   - Detects sharp magnitude drops in FFT
2. **Energy-based cutoff detection** (fallback)
   - Finds where 90% of energy is concentrated
   - **Critical**: Only 15-22 kHz range is suspicious
   - Bass concentration (< 15 kHz) = authentic

**Why 15 kHz minimum?**
```
Bass-heavy music example:
  Energy distribution:
  │████████  ← 80% energy at 2-3 kHz (bass)
  │██        ← 15% energy at 5-10 kHz (mids)
  │▓         ← 5% energy at 10-22 kHz (highs)
  └──────────→
   0    22kHz

  This is AUTHENTIC music, not MP3 artifact!
  Without 15 kHz threshold → False positive
```

**Scoring**:
- Per 200 Hz below threshold: **+1 point** (max +30)
- Formula: `min((threshold - cutoff) / 200, 30)`
- Bass concentration (< 15 kHz): **0 points** (protected)

**Example**:
```
Cutoff at 19000 Hz, threshold 22000 Hz:
→ Deficit: 3000 Hz
→ Score: 3000 / 200 = 15 points
```

---

### Rule 3: Source vs Container Bitrate — removed in v1.10

Rule 3 compared the source bitrate that Rule 1 had *inferred from the cutoff*
against the FLAC container bitrate, and awarded up to +50 on a mismatch. It was
deleted because it never contributed a single independent detection.

Measured across 978 files (the 800-file audit corpus plus the 178-file wild
scan): Rule 3 fired **143 times, always alongside Rule 1, and never once alone**.
It was not a second opinion — it was Rule 1's own answer, echoed back at full
weight. Under the v1.9 corroboration gate that echo could no longer convict by
itself, but it still inflated totals enough to drag a weak third family over the
line. Removing it costs nothing measurable in recall and removes a systematic
bias toward conviction.

The lesson generalises past this one rule: **independence has to be measured, not
asserted.** The same audit pass that killed Rule 3 also showed the `cnn` and
`spectral` families are not fully independent, which is now a CI guard
(`tests/test_rule_audit_guard.py`).

---

### Rule 4: Suspicious 24-bit Detection

**Purpose**: Identify fake high-resolution files

**Detection method**:
- Check bit depth metadata
- 16-bit = CD quality (standard)
- 24-bit = high-resolution (rare for MP3 transcodes)
- Combined with other indicators → fake high-res

**Scoring**:
- 24-bit + suspicious patterns: **+30 points**
- 16-bit: **0 points**

---

### Rule 5: High Variance Protection (VBR)

**Purpose**: Protect legitimate Variable Bitrate files

**Detection method**:
- Analyze bitrate variance across audio segments
- VBR MP3s have natural variance
- CBR transcodes have uniform patterns

**Scoring**:
- High variance detected: **-40 points** (protection)
- Low variance: **0 points**

---

### Rule 6: High Quality Protection

**Purpose**: Protect high-quality legitimate files

**Detection method**:
- Check container bitrate
- > 700 kbps indicates quality encoding

**Scoring**:
- Bitrate > 700 kbps: **-30 points** (protection)
- Lower bitrate: **0 points**

---

### Rule 7: Silence & Vinyl Analysis

**Purpose**: Detect and protect vinyl/analog sources

**Detection phases**:
1. **Dither detection**: Analyze silence for noise shaping
2. **Surface noise**: Low-frequency rumble (< 100 Hz)
3. **Clicks & pops**: Vinyl surface artifacts

**Scoring** (phases run in order; a phase-1 verdict stops the rule):
- Dither in silences (ratio > 0.3): **+50 points** — transcode, stop
- Clean natural silence (ratio < 0.15): **-50 points** — authentic, stop
- Uncertain zone, vinyl noise found: **-40 points**, plus **-10 points** if
  clicks confirm (5-50/min) — maximum protection -50 on either path
- Uncertain zone, no noise above cutoff: **+20 points** (upsample suspect)
- No vinyl signatures: **0 points**

An earlier revision of this page claimed a single "-100" protection; no code
path has ever been able to award it (the -50 outcomes return early), and the
claims audit caught the drift in 2026-08.

**Why protection?**
```
Vinyl rips legitimately have:
- Surface noise throughout
- Frequency content that may look "limited"
- These are NOT indicators of transcoding
```

---

### Rule 8: Nyquist Exception

**Purpose**: Protect files with cutoff near theoretical maximum

**Detection method**:
- Cutoff near Nyquist (e.g., ≥ 20947 Hz for 44.1 kHz at the 95 % tier)
- Likely anti-aliasing filter, not MP3 cutoff

**Scoring** (two tiers, with safeguards):
- Cutoff ≥ 98 % Nyquist: **-50 points** (strong protection)
- 95 % ≤ cutoff < 98 % Nyquist: **-30 points** (moderate protection)
- Safeguard: an MP3 signature with a dirty silence ratio cancels the bonus
  (> 0.2) or reduces it to -15 (> 0.15)
- Far from Nyquist: checked by Rule 2

**The low wall (v1.17.0) — when "near Nyquist" was a reading of the floor.**
The cutoff detector measures every 250 Hz cell against the 10-14 kHz band and
scans from 14 kHz. Under ~64 kbps an encoder's own low-pass sits at 3-11 kHz, so
that reference band is the codec's floor: the scan compared the floor with itself,
found nothing, reported 22,050 Hz, and this rule granted -50 to files whose music
stops at 4 kHz. When the detector finds nothing, the engine now looks for a wall
below the reference band (`spectrum.low_wall_hz`: a fall of at least 15 dB over
500 Hz, with at least 30 dB of nothing above it up to 16 kHz). A wall replaces the
reading, so this rule no longer applies; Rule 2 scores it on its usual ramp (30,
still AUTHENTIC) and names it: "the audio stops at X Hz behind a wall". Rule 1
does not read it as an MP3 cell.

It does not signal these files, on purpose. Restorers low-pass 78 rpm and
cylinder transfers just as steeply, at the same 3-5 kHz: the instrument fires on
30 of 1,896 Dust-to-Digital tracks, and scoring the wall into WARNING, or letting
Rule 1 read it, sent an 1890s gramophone record to SUSPICIOUS by the same
arithmetic that caught the 64 kbps MP3s. Measured on 220 low-rate files and 203
genuine ones before it shipped: `ml/exchange/LOW_WALL_REGISTRATION_2026-09-25.md`.

---

### Rule 9: Compression Artifacts — REMOVED in v1.8

Rule 9 ran three psychoacoustic tests (pre-echo, HF aliasing, MP3 quantisation
noise) and awarded up to +40 points. It was removed after being measured, for the
first time, on its own:

| test | AUC | fires on genuine | fires on fakes |
|---|---|---|---|
| 9A pre-echo | 0.513 | 83 % | 85 % |
| 9B HF aliasing | 0.586 | 6 % | 9 % |
| 9C MP3 noise pattern | 0.497 | ~0 % | ~0 % |

An AUC of 0.5 is a coin flip. The physics the rule was built on is real — MDCT
codecs genuinely produce pre-echo — but the implementation did not measure it:
the pre-echo test compared HF energy before a transient against three times the
file's median, a bar that the natural attack ramp of real music clears on its
own. So it fired on nearly everything and separated nothing, while adding +15 to
any genuine file that passed its gate. With the WARNING bar at 31, that made the
effective bar 16 for those files.

The finding was first reported by Jamie Dodd (Provir), who measured 9A standalone
at AUC 0.517 on 364 files of his own; it reproduced here at 0.513 on a disjoint
480-file set, and again in-pipeline at 0.486.

Its replacement is [Rule 13](#rule-13-mdct-frame-alignment), which reads MDCT
quantisation directly instead of inferring it from spectral side effects.

---

### Rule 10: Multi-Segment Consistency

**Purpose**: Validate patterns across entire file

**Detection method**:
- Analyze 5 segments across the file (start, 25 %, 50 %, 75 %, end)
- A real transcode is compressed the same way everywhere; localized or
  drifting anomalies point at mastering, not transcoding
- Runs only once the score already exceeds 30 (the file is already suspect)

**Scoring** (protective only — this rule never adds points):
- Cutoff variance > 1000 Hz across segments: **-20 points** (dynamic
  mastering, not a global transcode)
- Exactly one problematic segment: **-30 points** (local artifact)
- Consistent segments: **0 points** (the suspicion stands as accumulated)

An earlier revision of this page claimed "+20 for consistent MP3 patterns";
the rule has never awarded positive points — consistency leaves the existing
score untouched. The claims audit caught the inversion in 2026-08.

---

### Rule 11: Cassette Detection

**Purpose**: Identify and protect cassette tape sources

**Detection method** (30 s from the middle of the file, cutoff under 19 kHz only):
- **11A, tape hiss** (+30 evidence): a band-pass from just above the edge to
  18-20 kHz; a level over −55 dB with a random texture reads as hiss.
  **Since v1.19.1 it credits nothing when the band above the edge is digital
  silence** (the depth instrument's floor at or under −58 dB): hiss is
  broadband and a cassette chain cannot leave silence above its edge. The
  band-pass starts inside its own lower skirt, so on a loud master the music
  just under a codec wall leaks through and reads as "hiss" — a 128 kbps
  transcode read −52.3 dB through the filter where the band's true power is
  −98.4 dB, and collected the protection
  (`ml/exchange/HISS_OVER_SILENCE_REGISTRATION_2026-09-30.md`).
- **11B, roll-off** (+20 for a natural −3 to −6 dB/kHz slope over 12-18 kHz,
  −20 for a cut sharper than −10 dB/kHz).
- 11C was removed in v1.8 and 11D ("wow/flutter" read on a 250 Hz grid) in
  v1.13.14: neither measured anything.

The gate is `CASSETTE_THRESHOLD` (25) of evidence.

**Scoring**: **none, by design (v1.8).**

Rule 11 contributes zero points. What it produces is *evidence that the source is
a genuine analog transfer*, which the calculator reads to cancel Rule 1 and apply
a −40 protection bonus.

Until v1.8 that evidence was added to the transcode score instead, so a file that
sounded like a cassette was pushed toward being called fake — precisely backwards.
The per-rule audit caught it: Rule 11 measured **AUC 0.321**, handing genuine files
+18.3 points on average against +11.2 for transcodes. Two of the five false
positives in the audit corpus were analog-sourced reissues that Rule 11 had pushed
*up*. Its test 11C ("no MP3 pattern → +15") was also removed: it keyed off Rule 9C,
which measured at chance, so it was a constant. The cassette gate dropped 30 → 15
to compensate exactly, leaving every real test at its original weight.

### Rule 13: MDCT Frame Alignment

**Purpose**: Detect high-bitrate transcodes that leave the spectrum intact — the
regime where every other rule in this list runs out of signal.

**Why it is different**: Rules 1–8 and 11 read the spectral cutoff and the band
above it; Rule 12's CNN reads a mel-spectrogram dominated by the same region. At
256–320 kbps a modern encoder keeps the band, so there is nothing up there to
find. Rule 13 never looks at the cutoff. It looks for the arithmetic the encoder
left behind.

**Detection method**: an MDCT codec quantises transform coefficients, and
quantisation sends many of them to exactly zero. Those zeros survive decoding:
re-analyse the decoded audio with the same transform — same 2048-sample window,
same Kaiser-Bessel-derived window (alpha = 4 for ffmpeg-family AAC), same
sample-exact alignment — and the zeroed bins reappear as deep holes. Analyse at
any other alignment and they smear away.

The statistic is therefore not "how many holes" (real music has holes) but
**peak ratio**: hole density at the best alignment divided by the median across
unrelated alignments. Genuine lossless audio has no preferred alignment, so its
curve is flat and the ratio sits near 1.0. All 1024 offsets are searched, in two
stages so the cost stays around 4 s per file.

**Scoring**:
- peak ratio ≥ 3.0: **+55 points** (SUSPICIOUS alone, never FAKE_CERTAIN alone)
- peak ratio ≥ 2.0: **+25 points**
- below: **0 points**

Calibrated against 880 certified-genuine files: median 1.24, maximum ever
measured 1.494. The review bar sits 34 % clear of that maximum, the hard bar at
double it. ffmpeg AAC sits at 13.6–21.5 — an order of magnitude away, not a
squeezed tail.

**Gate**: the file not already at FAKE_CERTAIN. Until v1.20.1 it also required a
cutoff ≥ 18 kHz, "because below that the cheap spectral rules already have plenty
to work with". Issue #12 showed otherwise: Vorbis at `-q1` on a loud master fills
the band above its edge with noise and the edge wanders, so every sub-18 kHz rule
stepped aside on a file Rule 13 reads at 2.43. Under 18 kHz, 37 labelled and
certified genuine files read at most 1.46, 45 78 rpm transfers at most 1.40, 29
cassettes at most 1.43 (`ml/exchange/R13_LOW_CUTOFF_REGISTRATION_2026-10-02.md`).

**Scope, stated plainly**: two transform hypotheses are tried per file, AAC's
KBD (α=4) window and **Vorbis's** `sin(π/2·sin²(π/N·(n+0.5)))` window, and the
stronger reading wins. They share the 2048-sample long block and differ only in
window shape, which is why one code path covers both. Adding the Vorbis
hypothesis in v1.10 took Vorbis q8 detection from **AUC 0.806 to 0.955** (median
peak ratio 1.42 -> 3.61) while moving the genuine maximum only from 1.42 to
**1.427** — the second hypothesis costs essentially
nothing in false alarms because genuine audio has no alignment to find under
*either* window.

**The encoder gradient, measured rather than assumed.** "AAC" is not one thing;
which AAC encoder produced the file matters more than the bitrate does.

| encoder | median peak ratio | Rule 13 fires (≥2.0) |
|---|---|---|
| ffmpeg (128–320 kbps) | 13.6–21.5 | ~always |
| Microsoft MediaFoundation 256k | 2.66 | often (AUC 0.791) |
| **Apple CoreAudio 128k** | 1.50 | **13 %** |
| **Apple CoreAudio 256k** | 1.30 | **2 %** |
| **Apple CoreAudio 320k** | 1.30 | **0 %** |
| genuine | 1.28 | 0 % |

The Apple rows come from `.github/workflows/coreaudio-arm.yml`, which builds the
arm on a free macOS runner with `afconvert` — the same CoreAudio encoder `qaac`
wraps — and measures it paired, each source with and without the round-trip
(`ml/coreaudio_arm.py`, n=100). Jamie Dodd of Provir reported this encoder as a
clean zero for the rule. Operationally he is right at 320 kbps and nearly right
at 256; Rule 13 never hard-convicts CoreAudio at any bitrate. But the material is
not evidence-free — at 128 kbps the statistic still separates — which says the
zeros are the wrong observable for this encoder rather than that there is nothing
to find. Provir's residual-against-the-reconstructed-transform reads the same
material far better (54/64 at cvbr128 against our 13/100).

That run also produced an independent check on the calibration nobody asked for:
the genuine ceiling across its 100 wild archive.org taper recordings is **1.420**,
against **1.427** measured on 80 certified CD rips. Two corpora of entirely
different provenance, the same ceiling.

**Opus was thought out of reach by construction; it was not (v2.1.0).** CELT
transforms at 48 kHz whatever you feed it, so a 44.1 kHz source is resampled in and
back out, and the reading at Opus's own geometry measured the null (Opus 256k:
median 1.30 against a 1.28 genuine median, AUC 0.575). The measurement was right and
the explanation was not: the CELT decoder ends with a de-emphasis filter
(y[n] = x[n] + 0.85 y[n-1]) that smears every zeroed coefficient. Back at 48 kHz with
that filter undone, the grid is there. See
[the 2.1.0 readings](#rule-13-the-21-readings-vorbis-block-switching-and-opus) below.

**MP3 is out of reach too, for a different reason, and this was also measured.**
MP3 does not resample, so unlike Opus its alignment survives — it simply lives at
a 576-sample granule and a 1152-sample frame rather than 2048. Scanning at MP3's
own period with a plain MDCT nonetheless reads the null: AUC 0.54 on `mp3_320`
and 0.61 on `mp3_V0`, against 1.00 for ffmpeg AAC at its own geometry in the same
run. A bitrate gradient settles it — at 64 kbps, where MP3 zeroes a large part of
the spectrum, the reading is still 0.41. So it is not that there are too few
zeros to find: MP3 quantises in a hybrid domain (a 32-band polyphase filterbank
followed by an 18-point MDCT) whose synthesis smears those zeros across 512 taps,
and matching only the period does not reach them. Implementing the real Layer III
filterbank is the only remaining route and is not currently justified by anything
measured. See `ml/mp3_geometry_probe.py`.

Rule 13 also loses the signal above roughly 60 % zeroed coefficients, i.e. at
very low bitrates, where the spectral cliff is obvious anyway. All of these
limits have tests pinning them (`tests/test_mdct.py`).

---

### Rule 12: ML Classifier (CNN) — *optional*

**Purpose**: An independent, learned second opinion that *sharpens* borderline verdicts.
It is the only non-heuristic rule and is **off unless** the ML extra is installed
(`pip install "flac-detective[ml]"`); without it, Rule 12 is a no-op and rules 1–11 stand alone.

**Model**: a small **EfficientNet-B0** CNN bundled with the package. Input is a
**2-channel mid/side mel-spectrogram** (mid = L+R, side = L−R) rather than mono — MP3
quantises the side channel aggressively, so its fingerprints survive even on band-limited
material where the high-frequency cliff is faint. This stereo move is what lifted real-world
specificity from 80 % (mono, v0.12) to 95 % (v0.14).

**Reliability gate (key design choice)**: a false-positive audit on 11 234 certified-authentic
FLACs showed the CNN is unreliable on sources that roll off below **~7 kHz** (genuinely
band-limited masters look like transcodes to it). Below that 95 % spectral-rolloff threshold
the model **abstains** (contributes 0) and lets the heuristic rules decide — faithful to the
"protect authentic files first" philosophy. The rolloff is computed from the same decode used
for the mel-spectrogram, so the gate is essentially free.

**Scoring**: adds a bounded boost on already-suspect files; it is tuned to *raise confidence*
on borderline cases far more than to catch fakes the heuristics miss outright. It cannot, by
itself, flip a clean file to FAKE. **With `--deep`** (v1.2), one exception applies: on a
full-range file the heuristics left silent, a *highly confident* CNN detection (p ≥ 0.90)
lifts the verdict to **WARNING** — never higher — so high-bitrate AAC/Vorbis transcodes
surface for review. See the "On confidence / `--deep`" note above.

> The full R&D story — the false-positive audit, four dead-ends, a debunked "AUC 0.99", and
> the mono→stereo breakthrough — is written up as a learning resource in
> [`ml/README.md`](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md).

### CNN inference: calibration and multi-window aggregation (v1.6)

Two refinements to *how* Rule 12 turns audio into a probability — neither changes
the model weights:

- **Calibrated probability.** The CNN's softmax output is a confidence, not a
  true probability (cross-entropy training leaves it over-confident). A monotonic
  Platt/isotonic mapping — fitted offline on a held-out labelled set by
  `ml/calibrate_model.py` and bundled as `cnn_v4_stereo.calibration.json` —
  rescales it, so the 0.5/0.95 score ramp, the 0.90 WARNING floor, and any
  displayed `p` mean a real probability. Absent the file, calibration is the
  identity (no behaviour change). See
  `analysis/new_scoring/rules/ml_calibration.py`.
- **Multi-window inference.** Instead of one 10 s middle segment, several
  evenly-spaced windows are scored and their probabilities averaged; the
  per-window spread is surfaced as an uncertainty signal. This removes the
  single-segment fragility (a quiet intro or band-limited bridge) behind several
  past measurement bugs. `infer_file_probability()` is the single source of truth
  shared by the rule and the `ml/` scripts.

### Rule 15: the stereo witness reads the whole file (v1.17.0)

Rule 15 reads the dead runs joint stereo leaves in the side channel above
10 kHz, and it is a witness: no points, one evidence family. Until v1.17.0 its
200 analysis frames were contiguous from the first sample, about 4.7 s, and the
engine hands it the whole file, so on a full track it read the intro. The frames
are now spread evenly over the file, as Rule 13 spreads its MDCT frames. Measured
before it shipped: the witness fires on fewer genuine files (8.7 % to 5.8 % of
206, statistic alone), as often on the codec arms, and three times as often on
full-length transcodes; end to end it gained the witness on 7 transcodes and no
genuine file, and changed no verdict. It was one suspect for "two halves of one
track disagree", and it turned out not to be the main one: that is Rule 1's
+50 and the CNN swinging at an unchanged edge.
`ml/exchange/STEREO_SPREAD_REGISTRATION_2026-09-25.md`.

### Rule 13: the 2.1 readings, Vorbis block switching and Opus

Issue #12 brought three files Rule 13 could not read, each for a reason that is a
property of the codec (`analysis/new_scoring/codec_grids.py`). When Rule 13's own
reading does not reach its hard bar, two more are taken, each against bars of its
own; the rule still scores once, the strongest tier any reading reaches, family
`mdct`. Its two certified hypotheses and their bars are untouched.

* **Vorbis with block switching**, read on the left and right channels. A run of k
  short blocks between two long ones advances the long-block grid by 1024 + 128 k
  samples, so transient-heavy material carries eight alignments, not one: each read
  frame keeps the best of the eight phases of a residue, and residues are compared
  with residues. At high quality Vorbis keeps its zeros per channel, not in the mono
  mix, hence the channel views. The triage reads evenly spread positions — the
  loudest frames of such material are its short-block frames.
* **Opus (CELT)**: the file is brought back to 48 kHz (160/147, segment by segment on
  the shared 48 kHz grid), the decoder's de-emphasis is undone with its FIR inverse,
  and 960-sample frames are read through CELT's own low-overlap window.

Bars, from 1,151 labelled genuine files alone: Vorbis block-switch review 1.7, hard
2.4 (genuine p99.9 1.301, max 1.612); CELT review 2.2, hard 3.2 (p99.9 1.696, max
1.732). No labelled genuine file reaches either review bar. The MDCT is computed as a
TDAC fold plus a DCT-IV, which is exactly the transform and about six times cheaper.
`ml/exchange/ISSUE12_CODEC_GRIDS_REGISTRATION_2026-10-04.md`.

### Rule 17: band replication (v2.1.0)

Scores 25 / 55, family `sbr`. HE-AAC (and mp3PRO) code the lower spectrum and rebuild
the upper one by copying complex QMF subbands up a fixed number of subbands, so a file
arrives with energy to the top of the band that was never in the master, and every
cutoff rule reads it as untouched. The copy keeps its phase evolution: on a 128-point
STFT with a 64-sample hop (the QMF geometry), the complex coherence between a high
subband and the one p subbands below — sign-corrected for odd p, median over the
subbands from 5.5 kHz and 32 segments, maximum over p from 6 to 40 — reads 0.64 to
0.79 on HE-AAC v2 and at most 0.363 on 1,151 genuine files (median 0.086). Bars 0.40
and 0.55. It runs wherever Rule 13 runs, before any acquittal, and when it scores it
withdraws Rule 8's full-band protection, since replication is what manufactures a full
band. Two abstentions, found after the passes by the test suite (amendments 1 and 2
of the registration): the 2.1 readings of Rules 13 and 17 do not read a spectrum that
does not move (`stationarity.py`: median over 1-16 kHz bins of the std over time of
the dB magnitude under 2 dB — tones and fixed waveforms read 0.04-0.39 dB, music
17-30), and Rule 17 does not read a high band with no content at all, not one cell
within 50 dB of its segment's strongest subband (a four-sine chord's leakage read
0.713 there). **Limit**: HE-AAC v1 at 64 kbps reads 0.12-0.27, inside the genuine
tail: empty top subbands dilute the median there. Two broader repairs were measured
and refused by their registered criteria: a floor that dropped quiet cells (read v1
at 0.56-0.89, but lifted a labelled genuine recording to 0.470) and a "half the band
populated" gate (silenced 11 of 40 HE-AAC v2 files, whose rebuilt band stops well
under 20 kHz).
`analysis/new_scoring/sbr.py`.

### Rule 18: the side-channel step (v2.1.0)

A witness, zero points, family `stereo` (with Rule 15). Vorbis point stereo and CELT
intensity stereo stop coding the difference between the channels above a frequency
the encoder chooses, so the side channel falls ~20 dB against the mid there while it
stays at the music's own ratio below. Read on 1 kHz bands from 1 kHz to the file's
own cutoff minus 500 Hz, as the median over loud frames of side-to-mid energy; the
statistic is the largest drop between the three bands below a split and the three
above. No cutoff gate (Rule 15 has one at 17 kHz, which kept it from seeing a 16.75 kHz
Vorbis `-q1` file), mono gated out. It witnesses at 7.5 dB, the genuine p95 (as
Rule 15's bar is): about one genuine file in twenty offers it, with nothing to
corroborate unless another family has already carried the file past 55 points.
`analysis/new_scoring/joint_stereo.py`.

### Rule 16: the MP3 granule grid (v1.19.0)

A witness, zero points, family `mp3grid`, independent of the cutoff. The
decoded audio is passed through the encoder's own MPEG-1 Layer III analysis
filterbank — the ISO 32-band polyphase bank, an 18-point MDCT per subband, the
encoder's frequency inversion of odd subbands and its alias-reduction
butterflies — and, at each of the 576 granule alignments, the share of lines
40 dB under their local median is counted over 48 granules of the central
30 s. An MP3 decode has one alignment where the lines the encoder quantised to
zero return as holes; a genuine recording has none. The statistic is that
alignment's hole share over the median across all alignments; it witnesses at
1.6 (`GRID_BAR`). Held-out AUC 0.96-1.00 on MP3 128 to 320, chance on AAC and
Vorbis. It runs only on a file already at the conviction bar on one family,
the only place a witness can change a verdict. The approach is Herre and
Schug's "inverse decoder" (AES 109, 2000). A plain MDCT at MP3's period had
read MP3 at the null (`ml/README.md`); the hybrid bank is what it takes.
`ml/exchange/MP3_GRID_REGISTRATION_2026-09-27.md`.

## Fake High-Resolution Detection

A **separate axis** from the transcode verdict, reported as `hires_verdict`
(`GENUINE_HIRES` / `UPSAMPLED` / `PADDED_DEPTH` / `UPSAMPLED_AND_PADDED` /
`NOT_HIRES`). A file can be genuinely lossless and still be a fake hi-res product
(`analysis/hires.py`):

- **Upsampling** — 44.1/48 kHz content resampled to 88.2/96/176/192 kHz. The
  fingerprint is a hard spectral **cliff at the original Nyquist** (~22.05 / 24 kHz)
  with **digital silence** above it. Crucially, the test reuses Rule 1's
  silent-floor-vs-analog-floor discriminator: a genuine high-Nyquist recording
  that simply rolls off early keeps an analog/dither floor and reads
  `GENUINE_HIRES`, **not** a false alarm. The naive "cutoff < 24 kHz" heuristic it
  replaces would have flagged real hi-res.
- **Padded bit depth** — 16-bit audio written into a 24-bit (or 32-bit)
  container, the low bits all zero (`BitDepthDetector`). Since 2.2.0 the
  detector reads **eight windows spread over the file**, counts the trailing
  zero bits of every non-silent sample, and estimates 16, 24 or 32 from the
  smallest count; one window that carries full-depth audio clears the file.
  Until then it read the first 10,000 frames of the left channel only, and a
  genuine 24-bit track that opened with digital silence or a fade-in was
  labelled `PADDED_DEPTH` on that chunk
  (`ml/exchange/HIRES_AXIS_REGISTRATION_2026-10-07.md`).
- **32-bit integer FLAC** (FLAC 1.4+) is wider than libsndfile reads. It is
  decoded through the ffmpeg façade, which writes 24-bit PCM, and analysed
  from that copy; the header's 32 bits are what the hi-res axis judges. A true
  32-bit source therefore reads as 24-bit data: the low 8 bits are dropped by
  the decode, a stated limit. Before 2.2.0 such a file ended in ERROR.

The hi-res axis is informational about *provenance*; it does not feed the
transcode score. It is surfaced in the text report (both modes, since 2.2.0),
the CSV report, the desktop GUI and the Python API result dict.

What it has been measured on (2.2.0): 168 fakes built from 28 attested CD rips
(upsampled to 96 and 192 kHz with two resamplers, with and without noise-shaped
dither, padded to 24 bits, both) and 172 unlabelled hi-res library files; the
registration above carries the figures. There is no certified external hi-res
corpus in that measurement, and the upsampling test is known to miss an
upsample finished with noise-shaped dither when the shaped noise fills the band
above the original Nyquist.

## Scoring System

### Additive Scoring

All rules contribute to a **total score** (0-150 points):

```
Total Score = Σ(all rule contributions)

Example calculation:
  Rule 1 (MP3 Spectral):      +50 pts
  Rule 2 (Cutoff):            +15 pts
  Rule 5 (VBR Protection):    -10 pts
  Rule 13 (MDCT alignment):  +25 pts
  ────────────────────────────────────
  Total:                      80 pts → SUSPICIOUS ⚠️
```

**The sum is clamped to zero once, at the end — not on every addition (v1.8).**
This matters more than it sounds. Rule 8 is calculated *first* by design and
contributes −50 to a genuine full-band file; with a per-addition clamp that −50
was erased before any later rule could be offset against it, so a file scoring
45 − 50 read 45 rather than 0. Every protection rule that happened to run before
a penalty was inert. Protections are the whole basis of "protect authentic files
first", so they now survive to the end of the calculation.

### Conviction requires corroboration, not just points (v1.9)

The three lower tiers are read off the score. **FAKE_CERTAIN is not.** A
conviction requires **two independent evidence families**, and a file that has
them convicts from a lower points bar than the old flat 86.

| family | rules | what it reads |
|---|---|---|
| `spectral` | 1, 2, 3, 4 | the cutoff, and the MP3 bitrate inferred *from* the cutoff |
| `container` | 5 | bitrate variance across FLAC blocks |
| `silence` | 7 | HF energy in silent passages |
| `cnn` | 12 | learned mid/side mel-spectrogram classifier |
| `mdct` | 13 | frame-alignment quantisation structure |

Rules 6, 8 and 11 are **protection** — evidence of innocence, never of guilt.
Rule 10 re-scores segments through the same pipeline, so it is consistency rather
than corroboration and cannot be a family.

**Why Rules 1–4 are one family and not four.** Rule 3 compared the bitrate Rule 1
inferred against the container; Rule 4 gates on that same inference. However many
of them fire, they are one look at one thing. The v1.8 audit measured the
consequence exactly: *all three* false convictions on 80 certified-genuine files,
and *all 26* convictions on the 320 kbps MP3 arm, were Rules 1 + 3 at +50 each.
One measurement counted twice, clearing an 86-point bar unaided. No threshold can
separate that from real evidence, because the arithmetic is identical — only
counting sources can. Rule 3 was deleted outright in v1.10 once the audit showed
it had never fired without Rule 1 in 978 files.

**Why a family has to say something to count (v1.10).** The gate as shipped in
v1.9 counted any family with a single positive point as a witness. A blind
exchange with Provir found the failure mode on the first try: a genuine 2003
audience recording drew 112 points of doubled spectral evidence and a 16-point
CNN reading, and the CNN's murmur was enough to make the spectral pile
"corroborated". A family must now contribute `MIN_FAMILY_CONTRIBUTION` (20) to
be counted. That file now reads SUSPICIOUS on one family instead of
FAKE_CERTAIN on two.

**Why the bar drops when two families agree.** The same audit found 90 files where
Rule 12 and Rule 13 both scored — a learned model and a transform statistic, on
genuinely different physics — and **54 of them sat at exactly 85** against that
86-point bar. Two independent measurements agreeing were losing to arithmetic by
one point.

**A high uncorroborated score no longer skips the corroborating rules.** The
pipeline used to stop as soon as the score passed 86, which meant a file convicted
by Rules 1 + 3 never ran Rules 12 or 13 at all. Under a corroboration gate that
would have been self-defeating: the early exit guarantees a single family, and the
gate would end up measuring the short-circuit rather than the evidence. Early
exits now require corroboration too, which costs scan time on exactly the files
that were previously cheapest.

### Verdict Mapping

```
Score ≤ 30   → AUTHENTIC ✅      (no evidence of transcoding)
Score 31-54  → WARNING ❓        (borderline — manual review)
Score 55-85  → SUSPICIOUS ⚠️     (likely a transcode)
Score ≥ 86   → FAKE_CERTAIN ❌   (multiple strong indicators)
```

The thresholds live in `new_scoring/constants.py` (`SCORE_AUTHENTIC=30`,
`SCORE_WARNING=31`, `SCORE_SUSPICIOUS=55`, `SCORE_FAKE_CERTAIN=86`) and are the **single
source of truth** for the console, the text/JSON reports and the Python API — none of them
re-derive a verdict from a private cutoff.

### Score Interpretation

**Philosophy**: Higher score = More evidence of transcoding

- **Positive contributions** (+points): Indicators of MP3 transcode
- **Negative contributions** (-points): Protection for authentic sources

**Thresholds explained**:
- **≤ 30**: All protection mechanisms considered, minimal suspicious indicators
- **31-54**: Some suspicious indicators but with protective factors
- **55-85**: Multiple strong indicators, few protective factors
- **≥ 86**: Overwhelming evidence, definitive fake

> **On "confidence".** Verdicts are *evidence levels*, not probabilities. A `FAKE_CERTAIN`
> means several independent indicators agree — in practice very reliable — but `AUTHENTIC`
> means *"no evidence of transcoding found"*, **not** a guarantee: Apple AAC, high-bitrate
> MP3 and low-bitrate HE-AAC v1 transcodes and genuinely band-limited masters can score low (measured specificity is
> ~80–87 %, see [`ml/README.md`](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)). For critical decisions, confirm with a
> visual tool such as Spek.
>
> **Since v1.20.0 a default scan asks Rule 13 before that fast exit**: a file the
> heuristics left silent is acquitted only if Rule 13 reads no MDCT
> grid; if it reads one, the witnesses (Rules 14, 15, 12, 16) run and the verdict is
> computed from all of them (`ml/exchange/R13_DEFAULT_REGISTRATION_2026-10-01.md`). That
> reaches ffmpeg-family AAC and Vorbis, and since v2.1.0 Opus and HE-AAC v2 (Rules 13
> and 17); it does not reach Apple AAC or high-bitrate MP3.
>
> **`--deep` narrows this further.** A default scan skips the CNN (Rule 12) on files the fast
> heuristics and Rule 13 clear — which is where a high-bitrate MP3 or Apple AAC
> transcode hides (it leaves no heuristic trace). `--deep` runs the CNN on *every* file and,
> when it is highly confident (p ≥ 0.90) on a full-range file the heuristics left silent,
> lifts the verdict to **WARNING**. On a 240-file calibration that surfaces ~72 % of AAC-256
> and ~95 % of Vorbis transcodes for a ~4 % authentic-file cost — all WARNING, never a false
> SUSPICIOUS. It does **not** rescue band-limited material (a fundamental signal limit), and
> it is slower (a decode + CNN pass per file), which is why it's opt-in.

### Threshold Calibration

The bands aren't arbitrary — the SUSPICIOUS floor was **moved from 61 to 55 in v0.15.1**
after a score-distribution study. The study scored a large set of *known* MP3 transcodes
and found their scores cluster around a **median of ~58** — i.e. inside the old WARNING
band (31–60), so genuine fakes were being under-called as "borderline". Lowering the floor
to 55 reclaimed roughly **+5 percentage points** of transcodes as actionable SUSPICIOUS,
while authentic false positives stayed at ~1 %. The `FAKE_CERTAIN` floor (86) and the
AUTHENTIC ceiling (30) were left untouched. This is the concrete trade-off the
"protect authentic files first" philosophy makes: the boundary is placed where it catches
the most real fakes without pushing the authentic false-positive rate up.

## Spectral Analysis

### FFT (Fast Fourier Transform)

FLAC Detective uses FFT to analyze frequency content:

```python
# Simplified FFT analysis
def analyze_spectrum(audio_data, sample_rate):
    # Compute FFT
    fft_result = np.fft.rfft(audio_data)
    magnitude = np.abs(fft_result)
    frequencies = np.fft.rfftfreq(len(audio_data), 1/sample_rate)

    # Find cutoff frequency
    threshold = 0.01 * np.max(magnitude)  # 1% of peak
    cutoff_indices = np.where(magnitude > threshold)[0]
    cutoff_freq = frequencies[cutoff_indices[-1]]

    return cutoff_freq, magnitude, frequencies
```

### Cutoff Detection Methods

#### Method 1: Slice-Based (Primary)

Detects sharp magnitude drops:

```
Magnitude
    │
100%│████████████████
    │████████████████
 50%│████████████████
    │████████████████
  1%│████████████████ ← Sharp drop here
  0%│
    └────────────────────→ Frequency
           ↑
      Cutoff point (MP3 signature)
```

#### Method 2: Energy-Based (Fallback)

Finds 90% cumulative energy point:

```
Cumulative Energy
    │
100%│          ┌─────
    │         /
 90%│        / ← 90% threshold
    │       /
 50%│      /
    │     /
  0%│────/
    └────────────────→ Frequency
           ↑
    90% energy point
```

## Performance Optimizations

### 1. Intelligent Caching

```python
# Audio cache system
class AudioCache:
    def __init__(self, max_size=100):
        self.cache = {}  # filepath → audio_data
        self.max_size = max_size

    def get_or_load(self, filepath, duration):
        if filepath in self.cache:
            return self.cache[filepath]  # Cache hit

        # Load and cache
        audio = load_audio(filepath, duration)
        self.cache[filepath] = audio
        return audio
```

**Impact**: 80% faster on repeated analyses

### 2. Sample Duration

Default: 30 seconds per window, three windows per file (one on files of 90 s
or less).

This section used to print a table of accuracy against duration (85 % at 15 s,
95 % at 30 s, 98 % at 60 s). No measurement ever produced those numbers, and
when the question was finally measured (issue #8, 2026-09-07) the premise
failed: 30 s against 120 s on files with known provenance moved verdicts in
both directions, about one in forty, and the readings that moved were the
ones sitting on a 250 Hz cell boundary. A longer window reads different audio,
not the same audio better. The engine's thresholds were tuned at 30 s and every
published figure was taken there. Details and the per-corpus tables:
`ml/exchange/SAMPLE_DURATION_MEASUREMENT_2026-09-07.md`.

### 3. Parallel Processing

Multiple files can be analyzed in parallel:

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    results = executor.map(analyze_file, flac_files)
```

### 4. FFT Optimization

- Use `np.fft.rfft` (real FFT) instead of full FFT
- Downsample when appropriate
- Vectorized operations

## Technical Limitations

### What FLAC Detective Can Do

✅ Detect MP3-to-lossless transcodes (CBR and VBR)
✅ Detect high-bitrate **AAC (ffmpeg-family) and Vorbis** transcodes on full-range audio in
   a default scan (Rule 13, since v1.20.0), and **Opus, Vorbis at any quality and HE-AAC
   v2** since v2.1.0 (Rules 13 and 17); **Apple AAC and high-bitrate MP3** with `--deep`
   (the CNN, surfaced as WARNING; see "On confidence" above)
✅ Analyze FLAC, WAV (v0.15), ALAC and APE (v0.16, via ffmpeg) sources
✅ Identify fake high-resolution files: CD audio upsampled to 96 or 192 kHz
   (27 of 28 by either resampler, v2.2.0) and 16-bit audio padded into a 24-bit
   or 32-bit container (56 of 56), with the true depth read over the whole file
✅ Protect vinyl and cassette sources
✅ Detect compression artifacts
✅ Handle corrupted files (with repair)

### What It Cannot Do

❌ **Detect lossy transcodes of band-limited material** (baroque, 1920s, solo acoustic) —
   a fundamental signal limit, not fixed by `--deep`; and **WMA → FLAC** is unsupported
❌ **Read HE-AAC v1 at low bitrates** (64 kbps: 8 of 40 caught on the 2.1.0 held-out
   set) — empty top subbands dilute Rule 17's reading there
❌ **Read every upsample.** One finished with 16-bit noise-shaped dither is read
   about half the time (14 of 28 in v2.2.0: the shaped noise fills the band above
   22 kHz); one whose source was itself band-limited under ~20.7 kHz is not read at
   all; and a true 32-bit source reads as 24-bit data (the decode keeps 24 bits).
   The hi-res axis has been measured against 28 attested CDs and unlabelled library
   files only — no certified hi-res corpus yet
❌ **Guarantee 100% accuracy** (see [Accuracy](#accuracy))
❌ **Real-time processing** (designed for batch analysis)
❌ **Analyze lossless formats beyond FLAC/WAV/ALAC/APE** (e.g. WavPack, TAK — not yet decoded)
❌ **Subjective quality assessment** (only transcode detection)

### Accuracy

Based on testing with diverse audio samples:

```
True Authentic Files:
  Correctly identified: 95.2%
  False positives: 4.8%

True Transcoded Files:
  Correctly identified: 97.8%
  False negatives: 2.2%

Overall Accuracy: 96.5%
```

**False positive causes**:
- Aggressive mastering or limiting
- Unusual frequency content (e.g., sine wave tests)
- Rare analog sources not covered by protection rules

**False negative causes**:
- Very high-quality MP3 320 kbps VBR
- MP3s with unusual encoding settings
- Heavily processed audio (e.g., extreme normalization)

### Edge Cases

**1. MP3 320 kbps VBR**
- May pass as AUTHENTIC due to Rule 6 protection
- Intentional: prioritize avoiding false positives

**2. Vinyl rips**
- Protected by Rule 7
- Should score AUTHENTIC despite frequency limitations

**3. Streaming sources**
- May have legitimate frequency cutoffs (platform processing)
- May trigger WARNING (manual review recommended)

**4. Remastered albums**
- Heavy processing can create unusual patterns
- Use multiple tools for confirmation

## Algorithm Pseudocode

Complete detection algorithm:

```
function analyze_flac(filepath):
    # Step 1: Load metadata
    metadata = read_metadata(filepath)
    sample_rate = metadata.sample_rate
    bit_depth = metadata.bit_depth

    # Step 2: Load audio
    audio = load_audio(filepath, duration=30.0)

    # Step 3: Spectral analysis
    fft_result = compute_fft(audio)
    cutoff_freq = detect_cutoff(fft_result, sample_rate)
    energy_dist = compute_energy_distribution(fft_result)

    # Step 4: Apply rules
    score = 0
    score += rule_01(cutoff_freq, sample_rate)     # MP3 signature
    score += rule_02(cutoff_freq, sample_rate)     # Cutoff vs Nyquist
    score += rule_03(metadata, energy_dist)        # Bitrate mismatch
    score += rule_04(bit_depth, cutoff_freq)       # Suspicious 24-bit
    score += rule_05(audio, sample_rate)           # VBR protection
    score += rule_06(metadata)                     # High quality
    score += rule_07(audio)                        # Vinyl/silence
    score += rule_08(cutoff_freq, sample_rate)     # Nyquist exception
    score += rule_09(audio, fft_result)            # Compression artifacts
    score += rule_10(filepath, sample_rate)        # Multi-segment
    score += rule_11(audio)                        # Cassette
    score += rule_12(filepath, score)              # Optional CNN (ML); --deep WARNING floor

    # Step 5: Determine verdict
    if score <= 30:
        verdict = "AUTHENTIC"
    elif score <= 54:
        verdict = "WARNING"
    elif score <= 85:
        verdict = "SUSPICIOUS"
    else:
        verdict = "FAKE_CERTAIN"

    return {score, verdict, reasons}
```

## Further Reading

- **User documentation**: [User Guide](user-guide.md)
- **Python API**: [API Reference](api-reference.md)
- **Development**: [Contributing](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md)
- **Quick start**: [Getting Started](getting-started.md)

---

For technical questions, visit [GitHub Issues](https://github.com/Guillain-RDCDE/FLAC_Detective/issues).
