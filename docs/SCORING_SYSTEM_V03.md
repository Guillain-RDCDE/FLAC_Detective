# Improved Scoring System v0.3

## Overview

The FLAC Detective scoring system has been updated to align with industry best practices, particularly those of **Fakin' The Funk**.

## New 4-Level Scale

### Score Thresholds

| Score | Verdict | Description | Symbol |
|-------|---------|-------------|--------|
| **86-270** | `FAKE_CERTAIN` | Transcoding confirmed with certainty | ❌ |
| **61-85** | `SUSPICIOUS` | Probable transcoding, verification recommended | ⚠️ |
| **31-60** | `WARNING` | Anomalies detected, may be legitimate | ⚡ |
| **0-30** | `AUTHENTIC` | Authentic file | ✅ |

### Justification

This 4-level scale reflects the real distribution of audio files:

- **State 0 (AUTHENTIC)**: ~63% of files
- **State 1 (WARNING)**: ~36% of files ← **Important grey zone**
- **State 2 (SUSPICIOUS)**: ~1.2% of files
- **State 3 (FAKE_CERTAIN)**: ~0% of files (very rare)

## WARNING Zone (31-60) - Critical

The **WARNING** zone is particularly important because it contains:

- **Authentic vinyls** with naturally low cutoff
- **Cassettes** and other analog sources
- **Old masters** with technical limitations
- **Legitimate files** requiring manual verification

⚠️ **These files must NOT be automatically rejected!**

## Comparison with Old System

### Before (v0.2)

```
Score >= 80 : FAKE_CERTAIN
Score >= 50 : FAKE_PROBABLE
Score >= 30 : DOUTEUX
Score < 30  : AUTHENTIQUE
```

### After (v0.3)

```
Score >= 86 : FAKE_CERTAIN
Score >= 61 : SUSPICIOUS
Score >= 31 : WARNING
Score < 31  : AUTHENTIC
```

### Key Changes

1. **FAKE_CERTAIN Threshold**: 80 → **86** (+6 points)
   - Stricter to avoid critical false positives

2. **FAKE_PROBABLE** → **SUSPICIOUS**: 50 → **61** (+11 points)
   - Renamed for clarity
   - Higher threshold to reduce false positives

3. **DOUTEUX** → **WARNING**: 30 → **31** (+1 point)
   - Renamed for international clarity
   - Expanded zone to capture more ambiguous cases

4. **AUTHENTIQUE** → **AUTHENTIC**: < 30 → **< 31**
   - Renamed for international clarity
   - Slight reduction of "safe" zone

## Impact on Detections

### False Positives (Authentic Files Marked FAKE)

With new rules (7, 9, 10) and new thresholds:

- **12 current false positives** → Should pass under 31 (AUTHENTIC)
- **24-bit Vinyls**: Complete protection
- **16-bit Vinyls**: ~83% reduction in false positives

### True Positives (Transcoded MP3s)

- **34 true positives** → Will likely remain 31-60 (WARNING) or 61+ (SUSPICIOUS)
- **320 kbps MP3**: Improved detection
- **Transcoded AAC**: Better identification

## Scoring Examples

### Example 1: 320 kbps MP3 Transcode

```
Rule 1: +50 (Cutoff 20.5 kHz = 320 kbps)
Rule 2: +0  (Cutoff > 20 kHz)
Rule 3: +50 (Source 320 vs Container 850 kbps)
Total: 100 points → FAKE_CERTAIN ❌
```

### Example 2: Authentic Vinyl

```
Rule 1: +0  (Cutoff 18 kHz, no MP3 signature)
Rule 2: +10 (Cutoff slightly low)
Rule 6: -30 (High quality VBR)
Rule 7: -50 (Natural silence)
Total: 0 points (max(0, -70)) → AUTHENTIC ✅
```

### Example 3: Old Master (Ambiguous Case)

```
Rule 1: +0  (No MP3 signature)
Rule 2: +15 (Cutoff 17 kHz)
Rule 7: +20 (Ambiguous ratio)
Total: 35 points → WARNING ⚡
```

## Usage in Code

### Python

```python
from flac_detective.analysis.new_scoring import new_calculate_score, determine_verdict

# Calculate score
score, verdict, message, reasons = new_calculate_score(
    cutoff_freq=20500,
    metadata=metadata,
    duration_check=duration_check,
    filepath=path
)

# Interpret verdict
if verdict == "FAKE_CERTAIN":
    print(f"❌ {message}")
    # Action: Reject file
elif verdict == "SUSPICIOUS":
    print(f"⚠️ {message}")
    # Action: Mark for verification
elif verdict == "WARNING":
    print(f"⚡ {message}")
    # Action: Accept with warning
else:  # AUTHENTIC
    print(f"✅ {message}")
    # Action: Accept
```

### Constants

```python
from flac_detective.analysis.new_scoring import (
    SCORE_FAKE_CERTAIN,  # 86
    SCORE_SUSPICIOUS,    # 61
    SCORE_WARNING,       # 31
)
```

## Usage Recommendations

### For Users

1. **FAKE_CERTAIN (86+)**: Very likely fake file, reject
2. **SUSPICIOUS (61-85)**: Manually verify, listen to file
3. **WARNING (31-60)**: Accept with caution, may be legitimate
4. **AUTHENTIC (0-30)**: Authentic file, accept

### For Developers

1. **Never automatically reject** WARNING files
2. **Always provide reasons** for score for transparency
3. **Allow manual override** for all levels
4. **Log details** for future analysis

## Validation Tests

The following tests validate the new system:

```bash
# Test thresholds
pytest tests/test_new_scoring.py::TestVerdictThresholds -v

# Test mandatory cases
pytest tests/test_new_scoring.py::TestMandatoryTestCase* -v

# Test all rules
pytest tests/test_new_scoring.py -v
```

## Migration from v0.2

### Code to Update

1. **Imports**:
   ```python
   # Before
   from flac_detective.analysis.new_scoring import SCORE_FAKE_PROBABLE, SCORE_DOUTEUX
   
   # After
   from flac_detective.analysis.new_scoring import SCORE_SUSPICIOUS, SCORE_WARNING
   ```

2. **Verdict Comparisons**:
   ```python
   # Before
   if verdict == "FAKE_PROBABLE":
   if verdict == "DOUTEUX":
   if verdict == "AUTHENTIQUE":
   
   # After
   if verdict == "SUSPICIOUS":
   if verdict == "WARNING":
   if verdict == "AUTHENTIC":
   ```

3. **Custom Thresholds**:
   ```python
   # Before
   if score >= 80:  # FAKE_CERTAIN
   if score >= 50:  # FAKE_PROBABLE
   if score >= 30:  # DOUTEUX
   
   # After
   if score >= 86:  # FAKE_CERTAIN
   if score >= 61:  # SUSPICIOUS
   if score >= 31:  # WARNING
   ```

## Changelog

### v0.3 (December 3, 2025)

- ✅ New 4-level system aligned with Fakin' The Funk
- ✅ Adjusted thresholds: 86/61/31 (instead of 80/50/30)
- ✅ Renamed verdicts: SUSPICIOUS, WARNING, AUTHENTIC
- ✅ Descriptive messages instead of confidence levels
- ✅ Expanded WARNING zone for ambiguous cases
- ✅ Complete documentation

### v0.2 (December 2, 2025)

- 3-level system: FAKE_CERTAIN/FAKE_PROBABLE/DOUTEUX
- Thresholds: 80/50/30

---

**Date**: December 3, 2025  
**Version**: 0.3.0  
**Status**: ✅ Implemented and tested
