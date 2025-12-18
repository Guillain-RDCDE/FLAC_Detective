# 📋 Documentation Version Status

## Current Version: v0.7.0

Last Updated: December 18, 2025

---

## 🟢 Current & Maintained Documentation

### User Documentation
- ✅ [GETTING_STARTED.md](GETTING_STARTED.md) - Installation & first scan
- ✅ [ARCHITECTURE.md](ARCHITECTURE.md) - System design (spectral-only Rule 1)
- ✅ [RULES.md](RULES.md) - 11-rule reference (spectral-only Rule 1)
- ✅ [EXAMPLES.md](EXAMPLES.md) - Real-world usage scenarios
- ✅ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues & solutions

### Developer Documentation
- ✅ [development/CONTRIBUTING.md](development/CONTRIBUTING.md)
- ✅ [development/DEVELOPMENT_SETUP.md](development/DEVELOPMENT_SETUP.md)
- ✅ [development/TESTING.md](development/TESTING.md)

### Technical Documentation
- ✅ [technical/LOGIC_FLOW.md](technical/LOGIC_FLOW.md) - Pipeline with spectral-only Rule 1
- ✅ [technical/TECHNICAL_DETAILS.md](technical/TECHNICAL_DETAILS.md)
- ✅ [technical/ERROR_HANDLING.md](technical/ERROR_HANDLING.md)

### Navigation
- ✅ [INDEX.md](INDEX.md) - Documentation hub
- ✅ [STRUCTURE_GUIDE.md](../STRUCTURE_GUIDE.md) - Project structure

---

## 🟡 Historical/Legacy Documentation (OBSOLETE)

### ⚠️ OUTDATED - DO NOT USE FOR IMPLEMENTATION

These files describe Rule 1 with **direct bitrate thresholds** (< 128 kbps, < 160 kbps) 
which were **reverted in v0.7.0**. They are kept for historical reference only.

- 📜 [RULE1_ENHANCEMENT_BITRATE_DETECTION.md](RULE1_ENHANCEMENT_BITRATE_DETECTION.md) - **OBSOLETE**
  - Documents direct bitrate checks (reverted)
  - See [BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md) for updated analysis

- 📜 [RULE1_ENHANCEMENT_SUMMARY.md](RULE1_ENHANCEMENT_SUMMARY.md) - **OBSOLETE**
  - Contains implementation that was reverted
  - Kept for git history

- 📜 [CHANGELOG_RULE1_20251217.md](CHANGELOG_RULE1_20251217.md) - **OBSOLETE**
  - Documents changes that were later reverted
  - Kept for git history

- 📜 [IMPLEMENTATION_SUMMARY_20251217.md](IMPLEMENTATION_SUMMARY_20251217.md) - **OBSOLETE**
  - Describes reverted implementation
  - Kept for git history

- 📜 [COLLECTION_ZANZIBARA_IMPLICATIONS.md](COLLECTION_ZANZIBARA_IMPLICATIONS.md) - **OBSOLETE**
  - Analysis based on reverted bitrate thresholds
  - Conclusions about Vol. 2 & 3 no longer apply

- 📜 [INDEX_RULE1_ENHANCEMENT.md](INDEX_RULE1_ENHANCEMENT.md) - **OBSOLETE**
  - Navigation for reverted enhancement
  - Kept for git history

---

## 📊 Implementation Status

### Rule 1: MP3 Spectral Signature Detection (v0.7.0)

**Current Status**: ✅ **SPECTRAL-ONLY**

```
┌─────────────────────────────────────────┐
│  Rule 1 Implementation Summary           │
├─────────────────────────────────────────┤
│ Method          │ Spectral analysis      │
│ Bitrate checks  │ ❌ Reverted (v0.7.0)   │
│ Points awarded  │ +50 if match found     │
│ Safety checks   │ ✅ 5 implemented       │
│ False positives │ 0 in production scan   │
│ False negatives │ ~15 (Vol. 2&3 auth.)   │
│ Status          │ ✅ Production ready    │
└─────────────────────────────────────────┘
```

**Key Safety Checks**:
1. Nyquist threshold exception (≥95%)
2. Ambiguous 20 kHz handling (energy ratio + variance)
3. High-quality cutoff skip (>21.5 kHz)
4. Variance detection (authentic vs CBR)
5. Container bitrate range matching

**History**:
- v0.7.0: Spectral-only Rule 1 with safety guards (current, stable)
- (Experimental phases: Direct bitrate checks tested and reverted)

---

## 🔄 What Changed & Why

### Detection Change

**REVERTED** (v0.7.0):
```python
# Direct bitrate thresholds (caused faux positifs)
if container_bitrate < 128 kbps:
    return +60 points  # REMOVED - too aggressive
elif container_bitrate < 160 kbps:
    return +40 points  # REMOVED - false positives
```

**CURRENT** (v0.7.0):
```python
# Spectral signature only (reliable)
cutoff_freq = estimate_spectral_cutoff()
estimated_bitrate = estimate_mp3_bitrate(cutoff_freq)

if estimated_bitrate matches container range:
    return +50 points  # Reliable MP3 signature
else:
    return 0 points    # No evidence
```

### Why the Revert?

1. **Bitrate Container ≠ Bitrate Source**
   - FLAC is lossless container preserving full spectrum
   - Low FLAC bitrate ≠ low source quality
   - Direct bitrate checks created false positives

2. **Vol. 2 & 3 Analysis**
   - All files show 22050 Hz cutoff (full spectrum)
   - Characteristic of authentic FLAC, not MP3 upscales
   - Direct bitrate thresholds incorrectly flagged authentic files

3. **Production Results**
   - 122 files analyzed
   - 1 certain suspect (Vol. 9, clear MP3 signature)
   - Zero false positives with spectral-only approach

---

## 📖 How to Use This Documentation

### For New Users
1. Start: [GETTING_STARTED.md](GETTING_STARTED.md)
2. Learn: [ARCHITECTURE.md](ARCHITECTURE.md)
3. Reference: [RULES.md](RULES.md)
4. Explore: [EXAMPLES.md](EXAMPLES.md)
5. Troubleshoot: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### For Developers
1. Setup: [development/DEVELOPMENT_SETUP.md](development/DEVELOPMENT_SETUP.md)
2. Contribute: [development/CONTRIBUTING.md](development/CONTRIBUTING.md)
3. Test: [development/TESTING.md](development/TESTING.md)
4. Deep Dive: [technical/LOGIC_FLOW.md](technical/LOGIC_FLOW.md)

### For Researchers
1. Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
2. Logic: [technical/LOGIC_FLOW.md](technical/LOGIC_FLOW.md)
3. Technical: [technical/TECHNICAL_DETAILS.md](technical/TECHNICAL_DETAILS.md)
4. Error Handling: [technical/ERROR_HANDLING.md](technical/ERROR_HANDLING.md)

---

## ✅ Verification Checklist

- [x] BEFORE_AFTER_COMPARISON.md updated to reflect spectral-only
- [x] RULES.md confirms Rule 1 spectral implementation
- [x] ARCHITECTURE.md system diagram accurate
- [x] LOGIC_FLOW.md pipeline description current
- [x] All ASCII diagrams validated
- [x] Legacy files marked as obsolete
- [x] Current implementation documented

---

## 🚀 Next Steps

When updating documentation:
1. Update main docs first (GETTING_STARTED, ARCHITECTURE, RULES)
2. Update technical details (LOGIC_FLOW, TECHNICAL_DETAILS)
3. Mark legacy files with deprecation notice
4. Never delete historical files (preserve git history)
5. Link from current to legacy for reference

---

**For detailed implementation**: See [src/flac_detective/analysis/new_scoring/rules/spectral.py](../src/flac_detective/analysis/new_scoring/rules/spectral.py)
