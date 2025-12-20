# 📖 Detection Rules Reference

## Overview

FLAC Detective uses 11 independent detection rules to score audio authenticity. Each rule contributes to a final verdict:

| Verdict | Score Range | Meaning |
|---------|-------------|---------|
| AUTHENTIC | ≤ 30 | 99.5% confidence - genuine FLAC |
| WARNING | 31-60 | Manual review recommended |
| SUSPICIOUS | 61-85 | High confidence - likely MP3 upscale |
| FAKE_CERTAIN | ≥ 86 | 100% confidence - definitely MP3 upscale |

---

## Rule 1: MP3 Spectral Signature Detection

**Purpose**: Detect MP3 bitrate patterns via spectral cutoff

**How it works:**
- Analyzes the cutoff frequency of MP3s (typically 16-20.5 kHz depending on bitrate)
- Authentic FLAC preserves full spectrum (22050 Hz)
- CBR MP3 upscales show characteristic frequency boundaries

**Scoring:**
- Match found: **+50 points**
- No match: **0 points**

**Key thresholds:**
- 128 kbps MP3: ~16-16.5 kHz cutoff
- 160 kbps MP3: ~17-17.5 kHz cutoff
- 192 kbps MP3: ~19-19.5 kHz cutoff
- 256 kbps MP3: ~20-20.5 kHz cutoff
- 320 kbps MP3: ~20-20.5 kHz cutoff
- Authentic FLAC: 22050 Hz (full spectrum)

**Special cases:**
- Cutoff = 20000 Hz exactly: Checked for high-frequency energy (ambiguous)
- Cutoff ≥ 95% Nyquist: Skipped (likely anti-aliasing filter)

---

## Rule 2: Cutoff vs Nyquist Threshold

**Purpose**: Check if frequency cutoff is unusually low

**How it works:**
- Compares cutoff frequency to theoretical Nyquist limit
- Authentic files near Nyquist, MP3s can be far below

**Scoring:**
- Per 200 Hz below threshold: **up to +30 points**
- Formula: `min((threshold - cutoff) / 200, 30)`

**Example:**
- Threshold: 22000 Hz
- Detected: 16000 Hz (6000 Hz gap)
- Score: `min(6000/200, 30)` = **30 points**

---

## Rule 3: Source vs Container Bitrate

**Purpose**: Compare metadata bitrate with actual file bitrate

**How it works:**
- Calculates source bitrate from frame headers
- Compares with container (FLAC) bitrate
- Large discrepancies indicate upscaling

**Scoring:**
- High discrepancy: **+50 points**
- Moderate discrepancy: **+20-30 points**
- Low discrepancy: **0 points**

---

## Rule 4: Suspicious 24-bit Detection

**Purpose**: Identify unusual 24-bit encoding (often indicates upscaling)

**How it works:**
- Detects 24-bit PCM encoding
- 16-bit is standard for CD-quality audio
- 24-bit is rare and sometimes used for upscaled MP3s

**Scoring:**
- 24-bit detected: **+30 points**
- 16-bit (standard): **0 points**

---

## Rule 5: High Variance Protection

**Purpose**: Protect legitimate Variable Bitrate (VBR) encoded files

**How it works:**
- Analyzes bitrate variance across frames
- VBR has high variance, CBR has low variance
- High variance typically indicates authentic encoding

**Scoring:**
- High variance: **-10 points** (protection)
- Low variance: **0 points**

---

## Rule 6: Variable Bitrate Protection

**Purpose**: Protect high-quality legitimate files

**How it works:**
- Checks for high container bitrate (>700 kbps)
- Indicates legitimate lossless encoding

**Scoring:**
- High quality (>700 kbps): **-20 points** (strong protection)
- Normal quality: **0 points**

---

## Rule 7: Silence & Vinyl Analysis

**Purpose**: Detect and protect vinyl/analog source characteristics

**Scoring phases:**
1. **Dither Detection**: Analyze silence for dithering patterns
2. **Vinyl Surface Noise**: Detect low-frequency rumble
3. **Clicks & Pops**: Identify vinyl surface artifacts

**Scoring:**
- Vinyl characteristics: **-30 points** (protects analog sources)
- No vinyl signatures: **0 points**

---

## Rule 8: Nyquist Exception

**Purpose**: Handle edge cases near Nyquist frequency

**How it works:**
- Files with cutoff ≥ 95% Nyquist: likely authentic
- Files with cutoff ≥ 90% Nyquist: likely authentic (less certain)

**Scoring:**
- Both thresholds met: **0 points** (no penalty)
- Below threshold: checked by Rule 2

---

## Rule 9: Compression Artifacts

**Purpose**: Detect MP3 compression artifacts

**Sub-rules:**
- **Test A**: Pre-echo (MDCT ghosting)
- **Test B**: High-frequency aliasing
- **Test C**: MP3 quantization noise

**Scoring:**
- One artifact: **+15 points**
- Two artifacts: **+30 points**
- Three artifacts: **+50 points**
- No artifacts: **0 points**

---

## Rule 10: Multi-Segment Consistency

**Purpose**: Detect consistent patterns across entire file

**How it works:**
- Analyzes multiple segments of the audio
- MP3s show consistent compression artifacts across all segments
- Authentic files have variable spectral content

**Scoring:**
- Consistent artifacts: **+20 points**
- Inconsistent: **0 points**

---

## Rule 11: Cassette Detection

**Purpose**: Identify and protect authentic cassette tape sources

**How it works:**
- Detects characteristic cassette tape artifacts:
  - Speed variation (wow & flutter)
  - Age-related noise floor
  - Dropout patterns

**Scoring:**
- Cassette characteristics detected: **-20 points** (protects authentic analog)
- No cassette signatures: **0 points**

---

## Verdict Logic

```
Total Score = Sum of all rule contributions

if score >= 86:      FAKE_CERTAIN ❌
elif score >= 61:    SUSPICIOUS ⚠️
elif score >= 31:    WARNING ⚡
else:                AUTHENTIC ✅
```

## Tips for Users

- **AUTHENTIC (≤30)**: File passes all authenticity checks
- **WARNING (31-60)**: Review manually; might be legitimate
- **SUSPICIOUS (61-85)**: Likely MP3 upscale; high confidence
- **FAKE_CERTAIN (≥86)**: Definitely MP3 upscale; absolute confidence

---

## See Also

- [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) - Deep technical details
- [../technical/LOGIC_FLOW.md](../technical/LOGIC_FLOW.md) - Analysis algorithm flow
