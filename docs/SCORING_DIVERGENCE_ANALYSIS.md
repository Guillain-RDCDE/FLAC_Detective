# 🔍 SCORING DIVERGENCE ANALYSIS: Need you vs Soô

## Summary of the Problem

Two files from the same album exhibit **drastically different verdicts** despite having:
- Similar spectrograms (both show minimal energy above 20 kHz)
- Similar bitrates (~921-927 kbps)
- Same audio codec (FLAC)
- Same artist/album

| File | Cutoff | Bitrate | Verdict | Score |
|------|--------|---------|---------|-------|
| **Need you.flac** | 20.2 kHz | 921.6 kbps | **FAKE_CERTAIN** | **100/100** |
| **Soô.flac** | 19.25 kHz | 927.6 kbps | ??? (likely SUSPICIOUS or AUTHENTIC) | ??? |

---

## The 11-Rule Scoring System

FLAC Detective uses 11 rules that accumulate points. The verdict depends on the final score:

| Score Range | Verdict |
|-------------|---------|
| 0-30 | ✅ AUTHENTIC |
| 31-60 | ⚠️ WARNING |
| 61-85 | ⚠️ SUSPICIOUS |
| **≥86** | **❌ FAKE_CERTAIN** |

### Key Feature: Short-Circuit at ≥86 Points

When the score reaches **≥86**, the analysis **STOPS IMMEDIATELY**. This means:
- Fast rules 1-6 always execute
- Rules 7, 9, 11 (expensive) only run if score < 86
- Rule 10 only runs if score < 86

---

## Rule Breakdown

### **Fast Rules (Always Execute - Score < 86)**

#### Rule 1: MP3 Bitrate Detection (Spectral Signature)
- **Detects**: Spectral patterns typical of MP3 transcoding
- **Maximum**: 30+ points
- **Why Need you scored high**: 20.2 kHz cutoff triggers MP3 signature detection
- **Why Soô might score lower**: 19.25 kHz might be treated differently (cassette protection?)

#### Rule 2: Cutoff Frequency Analysis
- **Detects**: Unnaturally sharp cutoff (not 44.1k, 48k, or 96k boundaries)
- **Maximum**: 15+ points
- **Both files**: Have suspicious cutoffs (20.2k and 19.25k)

#### Rule 3: Source vs Container Bitrate Mismatch
- **Detects**: Estimated bitrate from spectral analysis vs actual FLAC bitrate
- **Maximum**: 20+ points
- **Impact**: Only if Rule 1 detected MP3 bitrate

#### Rule 4: 24-bit Suspect
- **Detects**: Uncommon 24-bit depth combined with MP3 signature
- **Maximum**: 15+ points

#### Rule 5: High Bitrate Variance
- **Detects**: Inconsistent frame bitrates (sign of FLAC from MP3)
- **Maximum**: 10+ points

#### Rule 6: Variable Bitrate Protection
- **Detects**: Protective patterns indicating authentication
- **Maximum**: Negative points (reduces score)
- **Both files**: Might have similar protection

### **Expensive Rules (Only if score < 86)**

#### Rule 7: Silence Analysis (19k-21.5k band)
- **Detects**: Unnatural silence in frequency band
- **Maximum**: 20+ points
- **Status**: Only runs if score hasn't reached 86

#### Rule 8: Nyquist Exception
- **Detects**: Specific frequency patterns at Nyquist
- **Maximum**: Variable
- **Protective**: Often reduces score

#### Rule 9: Compression Artifacts (MP3 detection)
- **Detects**: Specific MP3 compression patterns in waveform
- **Maximum**: 15+ points
- **Trigger**: If cutoff < 21 kHz OR MP3 detected

#### Rule 10: Multi-Segment Consistency
- **Detects**: Inconsistent scoring across file segments
- **Maximum**: Variable
- **Complex**: Analyzes multiple segments

#### Rule 11: Cassette Detection
- **Detects**: Cassette tape noise patterns
- **Trigger**: **cutoff_freq < 19,000 Hz**
- **Maximum**: 10+ points
- **Status**: Only runs if score < 86

---

## Why Need you Scores 100/100 (FAKE_CERTAIN)

```
Score Accumulation Path:
│
├─ Rule 1 (MP3 Signature): +X points
│  └─ Reason: 20.2 kHz cutoff matches MP3 encoder behavior
│
├─ Rule 2 (Cutoff Analysis): +Y points
│  └─ Reason: 20.2 kHz is suspicious (not standard boundary)
│
├─ Rule 3 (Source vs Container): +Z points
│  └─ Reason: If estimated bitrate from spectral ≠ 921.6 kbps
│
├─ Rule 4 (24-bit suspect): +W points
│  └─ Reason: If file is 24-bit + MP3 detected
│
├─ Rule 5 (Variance): +V points
│  └─ Reason: High bitrate variance across FLAC frames
│
├─ Rule 6 (Protection): ±U points
│  └─ Reason: Protective features analysis
│
└─ **TOTAL: X + Y + Z + W + V ± U = ≥86 points**

⚡ SHORT-CIRCUIT: Analysis stops here (rules 7, 9, 11 don't run)
└─ Result: FAKE_CERTAIN immediately
```

---

## Why Soô Might Score Different

### Hypothesis 1: Cutoff Below 19,000 Hz Triggers Cassette Rule
```
Need you.flac:  20.2 kHz  → Normal Rule 1 applies → Full MP3 detection
Soô.flac:       19.25 kHz → Rule 11 triggers (< 19 kHz?) → Cassette exception
```

**Impact**: Cassette detection might:
- Skip Rule 1 penalties
- Apply protective rule (negative points)
- Result in lower total score

### Hypothesis 2: Different Spectral Characteristics
Despite similar visual appearance, the spectrograms might have:
- Different energy distributions in key frequency bands
- Different variance patterns
- Different frame-by-frame consistency
- Different silence characteristics

### Hypothesis 3: Short-Circuit Didn't Trigger
```
Soô.flac score accumulation:
├─ Rule 1: +15 points
├─ Rule 2: +10 points
├─ Rule 3: +5 points
├─ Rule 4: 0 points
├─ Rule 5: +8 points
├─ Rule 6: -2 points (protective)
└─ Total: 36 points (< 86, no short-circuit)

Result: AUTHENTIC or WARNING (depending on rules 7-11)
```

---

## How to Debug This

### Option 1: Run Enhanced Analysis
```bash
# Create detailed scoring report
python scripts/debug_compare_files.py "path/to/Soô.flac" "path/to/Need you.flac"
```

This will show:
- Exact cutoff frequencies
- Exact bitrate calculations
- All rule points accumulated
- Why verdicts differ

### Option 2: Check Logs
Run FLAC Detective with `--debug` flag:
```bash
python -m flac_detective "/path/to/album/" --debug
```

This will show:
- Rule-by-rule scoring
- Short-circuit trigger points
- Specific reason for each rule's points

### Option 3: Add Detailed Report Mode
Request an enhanced report showing:
- Rule-by-rule breakdown for every file
- Reason text for each rule
- Point accumulation path
- Short-circuit trigger information

---

## Key Insights

### 1. **The Short-Circuit is the Key**
- **Need you**: Probably hit 86 points after rules 1-4, so rules 7, 9, 11 never ran
- **Soô**: Likely stayed < 86, so additional rules might have reduced or increased score

### 2. **Cutoff Frequency Threshold (19,000 Hz)**
- At **19.25 kHz**, Soô is dangerously close to the cassette detection threshold (< 19k)
- This might trigger protective rules that lower the score
- At **20.2 kHz**, Need you bypasses cassette logic entirely

### 3. **"Same Album" Assumption is Dangerous**
- Different tracks can have different:
  - Original source quality
  - Compression history
  - Spectral characteristics
  - Metadata patterns

### 4. **Spectrograms Show Only Cutoff, Not Full Pattern**
- While both show minimal energy above 20 kHz
- The energy DISTRIBUTION below 20 kHz might differ significantly
- MP3 compression leaves specific artifacts that vary by bitrate and psychoacoustic model

---

## Recommendations

### To Resolve This Ambiguity:

1. **Run Detailed Debug Analysis** (see "How to Debug This")
2. **Export Point Breakdown** for both files
3. **Compare Rule-by-Rule**:
   - Which rules scored each file differently?
   - By how many points?
   - What's the reason?

4. **Validate** with manual inspection:
   - Listen to both files
   - Check metadata
   - Compare with originals if available

5. **Consider Tuning** if score divergence seems unfair:
   - Adjust thresholds if needed
   - Add special case for cassette-like files
   - Implement manual review workflow for borderline cases

---

## Score Threshold Configuration

**Current Thresholds** (defined in `constants.py`):

```python
SCORE_AUTHENTIC = 30           # ≤ 30: AUTHENTIC
SCORE_SUSPICIOUS_START = 61    # 61-85: SUSPICIOUS
SCORE_FAKE_CERTAIN = 86        # ≥ 86: FAKE_CERTAIN
```

**Adjustment Recommendations**:
- If too many false positives: Increase `SCORE_FAKE_CERTAIN` to 90-95
- If too many false negatives: Decrease to 80-85
- If borderline cases: Add separate "REVIEW" category at 60-85

---

## Next Steps

**Immediate Action**: Run comparative analysis to see exact scores for both files:
```bash
python compare_two_files.py "path/to/Soô.flac" "path/to/Need you.flac"
```

**Expected Output**:
- Exact scores for each rule
- Cumulative score at each step
- Which rule triggered short-circuit (if any)
- Precise reason for verdict difference

---

*Analysis Date: v0.7.0 Release*
*Question: Why do similar spectrograms get different verdicts?*
*Answer: The 11-rule system accumulates points differently - investigate rules 1-6 and short-circuit behavior.*
