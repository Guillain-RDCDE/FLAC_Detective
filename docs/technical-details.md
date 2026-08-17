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
 │  11 heuristic rules + optional CNN (Rule 12) → 0–150 pts     │
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

Strategy pattern implementation with 11 heuristic rules plus an optional 12th (the CNN).

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

Analysis is **read-only**. There is exactly one case where FLAC Detective writes: when a
FLAC is **so corrupted it cannot be decoded at all**, even after the loader's retry/backoff.
A file that won't decode can't be analysed — so, rather than skip it, the tool rebuilds a
**valid, byte-identical FLAC** from whatever the audio data still allows, and then analyses
that. This is the opposite of "tinkering with the sound": **nothing in the audio is
processed, resampled, normalised or 'enhanced'.**

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
   6. replace original         (only after a .corrupted.bak backup is written)
   ▼
 valid .flac  ── now analysable; backup of the original kept beside it
```

### Safety guarantees

- **Only broken files.** A file that decodes normally is *never* rewritten. Healthy music is
  read and left exactly as it is.
- **A backup is always kept.** The original is copied to `<name>.flac.corrupted.bak` *before*
  anything replaces it — you can always go back.
- **Verified before trusted.** If the rebuilt file fails `flac --test`, repair aborts and the
  original is left untouched.
- **Metadata preserved.** Tags and embedded artwork are carried across verbatim.
- **Honest limit.** Samples that corruption genuinely destroyed can't be invented back —
  `--decode-through-errors` recovers everything still readable and no less. Repair never makes
  a file *worse* than the corruption already did; it makes a broken file *usable* again.

There are two entry points to the same lossless machinery:

- **Automatic**, during analysis — triggered only by the undecodable-file case above, so a
  scan of a healthy library never writes anything.
- **Standalone**, `python -m flac_detective.repair /path` — a duration-header fixer for FLACs
  whose declared length disagrees with their actual decoded length (also a lossless re-encode,
  also with a `.bak` backup).

## Detection Rules

FLAC Detective uses **11 heuristic rules** with **additive scoring** (0–150 points), plus
an **optional 12th rule** (a CNN, enabled with the `[ml]` extra — see Rule 12 below).

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
       • R13 MDCT alignment      if cutoff ≥ 18 kHz and not already convicted
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

**Scoring**:
- Vinyl characteristics detected: **-100 points** (strong protection)
- No vinyl signatures: **0 points**

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
- Cutoff ≥ 95% Nyquist (e.g., ≥ 20947 Hz for 44.1 kHz)
- Likely anti-aliasing filter, not MP3 cutoff

**Scoring**:
- Near Nyquist: **-50 points** (protection)
- Far from Nyquist: checked by Rule 2

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
- Analyze 3+ segments of the file
- MP3s show consistent compression throughout
- Authentic files have variable spectral content

**Scoring**:
- Consistent MP3 patterns: **+20 points**
- Variable patterns: **0 points**

---

### Rule 11: Cassette Detection

**Purpose**: Identify and protect cassette tape sources

**Detection method**:
- Wow & flutter (speed variations)
- Age-related noise floor elevation
- Dropout patterns

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

**Gate**: cutoff ≥ 18 kHz and the file not already at FAKE_CERTAIN — below that
the cheap spectral rules already have plenty to work with.

**Scope, stated plainly**: two transform hypotheses are tried per file, AAC's
KBD (α=4) window and **Vorbis's** `sin(π/2·sin²(π/N·(n+0.5)))` window, and the
stronger reading wins. They share the 2048-sample long block and differ only in
window shape, which is why one code path covers both. Adding the Vorbis
hypothesis in v1.10 took Vorbis q8 detection from **AUC 0.806 to 0.955** (median
peak ratio 1.42 -> 3.61) while moving the genuine maximum only from 1.42 to
**1.427** — the second hypothesis costs essentially
nothing in false alarms because genuine audio has no alignment to find under
*either* window.

**Opus is out of reach by construction, and this was measured.** CELT transforms
at 48 kHz whatever you feed it, so a 44.1 kHz source is resampled in and back
out, and resampling destroys the sample-exact alignment the statistic depends
on. Measured reading on Opus 256k under both hypotheses: **median 1.30, against a
1.28 genuine median — AUC 0.575.** Indistinguishable, and no threshold fixes it. MP3 has different framing
entirely, and the cutoff rules already convict there.

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
- **Padded bit depth** — 16-bit audio written into a 24-bit container, the low
  8 bits all zero (`BitDepthDetector`).

The hi-res axis is informational about *provenance*; it does not feed the
transcode score. It is surfaced in the CSV report, the desktop GUI and the Python
API result dict.

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
> means *"no evidence of transcoding found"*, **not** a guarantee: high-bitrate AAC/Opus
> transcodes and genuinely band-limited masters can score low (measured specificity is
> ~80–87 %, see [`ml/README.md`](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)). For critical decisions, confirm with a
> visual tool such as Spek.
>
> **`--deep` narrows this.** A default scan skips the CNN (Rule 12) on files the fast
> heuristics clear instantly — which is exactly where a high-bitrate AAC/Opus/Vorbis
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

### 2. Sample Duration Optimization

Default: 30 seconds (balance of speed vs accuracy)

```
Duration    Accuracy    Speed
15s         85%         Fast
30s         95%         Balanced ← Default
60s         98%         Slow
```

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
✅ Detect high-bitrate **AAC / Opus / Vorbis** transcodes on full-range audio — with
   `--deep` (the CNN, surfaced as WARNING; see "On confidence" above)
✅ Analyze FLAC, WAV (v0.15), ALAC and APE (v0.16, via ffmpeg) sources
✅ Identify fake high-resolution files
✅ Protect vinyl and cassette sources
✅ Detect compression artifacts
✅ Handle corrupted files (with repair)

### What It Cannot Do

❌ **Detect lossy transcodes of band-limited material** (baroque, 1920s, solo acoustic) —
   a fundamental signal limit, not fixed by `--deep`; and **WMA → FLAC** is unsupported
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

For technical questions, visit [GitHub Discussions](https://github.com/Guillain-RDCDE/FLAC_Detective/discussions).
