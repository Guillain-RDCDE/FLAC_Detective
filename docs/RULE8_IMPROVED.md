# Improved Rule 8: Nyquist Exception with Safeguards

## 📅 Date: December 3, 2025

## 🎯 Objective

Improve Rule 8 so that it is **always applied** with intelligent safeguards, instead of completely blocking the bonus in the presence of an MP3 signature.

## ❌ Old Behavior (Complete Block)

```python
if mp3_bitrate_detected is not None:
    if silence_ratio is None or silence_ratio >= 0.15:
        # COMPLETELY BLOCK the bonus
        return 0, []
```

**Problem**: Authentic files with cutoff close to Nyquist (21.5+ kHz) but having an MP3-like signature received NO bonus, even if they were legitimate.

## ✅ New Behavior (Intelligent Safeguards)

### Step 1: Base Bonus Calculation

The bonus is **ALWAYS calculated** based on the cutoff/Nyquist ratio:

```python
if cutoff_ratio >= 0.98:  # 21.6+ kHz for 44.1kHz
    base_bonus = -50  # Very close to limit
elif cutoff_ratio >= 0.95:  # 21.0+ kHz for 44.1kHz
    base_bonus = -30  # Probably authentic
else:
    base_bonus = 0  # No bonus
```

### Step 2: Applying Safeguards

If an MP3 signature is detected, the bonus is adjusted according to the `silence_ratio`:

| Condition | Final Bonus | Reason |
|-----------|-------------|--------|
| **No MP3 signature** | Base bonus (-50 or -30) | Authentic, full bonus |
| **MP3 + ratio ≤ 0.15** | Base bonus (-50 or -30) | Authentic silence despite signature |
| **MP3 + 0.15 < ratio ≤ 0.2** | **-15 points** | Grey zone, reduced bonus |
| **MP3 + ratio > 0.2** | **0 points** | Suspect dither, bonus cancelled |

## 📊 Scoring Examples

### Example 1: Authentic HQ File (No MP3)

```
Cutoff: 21.8 kHz (98.9% of Nyquist at 44.1kHz)
MP3 detected: No
Silence ratio: N/A

→ Bonus: -50 points
→ Reason: "R8: Cutoff at 98.9% of Nyquist → Very close to limit (-50pts)"
```

### Example 2: Vinyl with High Cutoff (MP3 + Authentic Silence)

```
Cutoff: 21.6 kHz (98.0% of Nyquist)
MP3 detected: 320 kbps
Silence ratio: 0.05 (< 0.15, natural silence)

→ Bonus: -50 points
→ Reason: "R8: Cutoff at 98.0% of Nyquist → Very close to limit 
          (-50pts, MP3 signature but authentic silence)"
```

### Example 3: Grey Zone (MP3 + Ambiguous Ratio)

```
Cutoff: 21.6 kHz (98.0% of Nyquist)
MP3 detected: 320 kbps
Silence ratio: 0.18 (0.15 < ratio ≤ 0.2, grey zone)

→ Bonus: -15 points (REDUCED)
→ Reason: "R8: Cutoff at 98.0% of Nyquist → Reduced bonus 
          (MP3 signature + grey zone) (-15pts)"
```

### Example 4: Suspect Dither (MP3 + High Ratio)

```
Cutoff: 21.6 kHz (98.0% of Nyquist)
MP3 detected: 320 kbps
Silence ratio: 0.3 (> 0.2, artificial dither)

→ Bonus: 0 points (CANCELLED)
→ Reason: "R8: Nyquist bonus cancelled (MP3 signature 320 kbps + 
          suspect dither 0.30 > 0.2)"
```

## 🔍 Detailed Logic

### Case 1: No MP3 Signature

```python
if mp3_bitrate_detected is None:
    # APPLY bonus unconditionally
    final_bonus = base_bonus
```

**Affected files**: Authentic high-quality FLACs

### Case 2: MP3 Signature + Authentic Silence

```python
if mp3_bitrate_detected and silence_ratio <= 0.15:
    # APPLY bonus (override)
    final_bonus = base_bonus
```

**Affected files**: Vinyls, cassettes with naturally high cutoff

### Case 3: MP3 Signature + Grey Zone

```python
if mp3_bitrate_detected and 0.15 < silence_ratio <= 0.2:
    # REDUCE bonus
    final_bonus = -15
```

**Affected files**: Ambiguous cases requiring caution

### Case 4: MP3 Signature + Suspect Dither

```python
if mp3_bitrate_detected and silence_ratio > 0.2:
    # CANCEL bonus
    final_bonus = 0
```

**Affected files**: Transcoded 320 kbps MP3s with artificial dither

## 🧪 Tests

### Updated Tests

```python
def test_strong_bonus_98_percent():
    """Strong bonus for cutoff >= 98% of Nyquist."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, None, None)
    assert score == -50

def test_applied_with_authentic_silence():
    """Bonus APPLIED despite MP3 if authentic silence."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.05)
    assert score == -50
    assert "MP3 signature but authentic silence" in reasons[0]

def test_reduced_in_grey_zone():
    """Bonus REDUCED if MP3 + grey zone."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.18)
    assert score == -15
    assert "Reduced bonus" in reasons[0]

def test_cancelled_by_mp3_signature_and_dither():
    """Bonus CANCELLED if MP3 + suspect dither."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.3)
    assert score == 0
    assert "cancelled" in reasons[0]
```

**Result**: ✅ **7/7 tests passing**

## 📈 Impact

### Before (Complete Block)

| File | Cutoff | MP3 | Ratio | Old Bonus |
|------|--------|-----|-------|-----------|
| HQ FLAC | 21.8 kHz | No | N/A | **-50** ✅ |
| HQ Vinyl | 21.6 kHz | 320 | 0.05 | **0** ❌ (blocked) |
| Grey Zone | 21.6 kHz | 320 | 0.18 | **0** ❌ (blocked) |
| Transcoded MP3 | 21.6 kHz | 320 | 0.3 | **0** ✅ |

**Problem**: Legitimate vinyls penalized!

### After (Intelligent Safeguards)

| File | Cutoff | MP3 | Ratio | New Bonus |
|------|--------|-----|-------|-----------|
| HQ FLAC | 21.8 kHz | No | N/A | **-50** ✅ |
| HQ Vinyl | 21.6 kHz | 320 | 0.05 | **-50** ✅ (applied) |
| Grey Zone | 21.6 kHz | 320 | 0.18 | **-15** ⚡ (reduced) |
| Transcoded MP3 | 21.6 kHz | 320 | 0.3 | **0** ✅ (cancelled) |

**Improvement**: Vinyl protection while still detecting fakes!

## 🎯 Benefits

1. **Always applied**: Rule always calculates base bonus
2. **Intelligent safeguards**: Adjustment based on context (MP3 + silence)
3. **Granularity**: 4 bonus levels (-50, -30, -15, 0)
4. **Vinyl protection**: Authentic files with MP3-like signature protected
5. **Detection maintained**: Real transcodes still detected (ratio > 0.2)

## 📝 Modified Code

### Files

- `src/flac_detective/analysis/new_scoring/rules.py`: Function `apply_rule_8_nyquist_exception()`
- `tests/test_rule8.py`: Updated tests

### Lines Added/Modified

- **Added**: ~30 lines (safeguard logic)
- **Modified**: ~20 lines (documentation, tests)
- **Removed**: ~15 lines (old block)

## 🚀 Next Steps

1. ✅ Passing unit tests (7/7)
2. ⏳ Field validation on real files
3. ⏳ Threshold adjustment if necessary (0.15, 0.2)
4. ⏳ User documentation

---

**Version**: 0.3.1  
**Date**: December 3, 2025  
**Status**: ✅ Implemented and tested  
**Tests**: 7/7 passing
