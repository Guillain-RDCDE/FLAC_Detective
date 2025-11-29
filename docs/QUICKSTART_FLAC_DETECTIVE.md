# 🚀 FLAC Detective - Quick Start Guide

```
🔍 FLAC DETECTIVE v0.1
"Every FLAC file tells a story... I find the truth"
```

---

## ⚡ Quick Installation (2 minutes)

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/flac-detective.git
cd flac-detective
```

### 2. Install Python dependencies

```bash
# Create virtual env (recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install package
pip install -e .
```

All dependencies will be installed automatically.
No external tools required!

---

## 🎯 First Test (30 seconds)

### Test on ONE file

```bash
python -m flac_detective.main --file "E:\Music\your_file.flac"
```

**You will see:**
```
🔍 FLAC DETECTIVE v0.1

🎵 DETAILED ANALYSIS: your_file.flac
================================================================================

📋 METADATA
  Sample Rate    : 44100 Hz
  Bit Depth      : 16 bits
  Duration       : 249.1 seconds

⏱️  DURATION CHECK
  Status         : ✅ OK (normal tolerance)

🔬 SPECTRAL ANALYSIS (3 samples)
  Cutoff         : 22050 Hz
  Energy >16kHz  : 0.000009

🎯 VERDICT
  Score: 95% 🟢
  Reason: Full spectrum up to 22050 Hz | Minimal ultra-high content
  
  ✅ AUTHENTIC FLAC - Very likely original lossless
```

**Score ≥90%?** → Your file is authentic! ✅

---

## 📊 Full Analysis (for 80,000 files)

### Launch analysis

```bash
cd E:\Music
python -m flac_detective.main
```

**What happens:**
1. 🔍 Scans all .flac files
2. 📊 Analyzes 4 criteria per file
3. 💾 Saves progress every 50 files
4. 📄 Generates final text report

**Estimated time:** 8-15 hours for 80,000 files

### Interruptible!

- **Interrupt:** `Ctrl+C`
- **Resume:** Just relaunch the script
- **Restart:** `del progress.json` then relaunch

---

## 📈 Generated Text Report

**File:** `flac_report_YYYYMMDD_HHMMSS.txt`

### "Summary" Section

```
FLAC ANALYSIS REPORT
================================================================================
Files analyzed:                     80,000
Authentic (90-100%):                74,200  (92.8%)
Probably authentic (70-89%):         1,100  (1.4%)
Suspicious (50-69%):                 3,850  (4.8%)
Very suspicious (<50%):                850  (1.1%)

DURATION ISSUES
Files with duration mismatch:        1,280  (1.6%)
Critical mismatch (>1 second):         160  (0.2%)
```

### "Suspicious Files" Section

Contains ONLY files < 90% with:
- Full path
- Score with color code 🟢🟡🟠🔴
- Detailed reason
- Cutoff frequency
- **Duration Issue** (new!)
- Complete metadata

---

## 🔧 Fixing Problems

### Repair a file

**1. Simulation test:**
```bash
python -m flac_detective.repair "file.flac" --dry-run
```

**2. Real repair:**
```bash
python -m flac_detective.repair "file.flac"
```

**Result:**
- ✅ File repaired
- 💾 Backup created (`.bak`)
- 📋 All metadata preserved
- 🖼️ All artwork preserved

### Repair a full album

```bash
python -m flac_detective.repair "E:\Music\Album\" --recursive
```

---

## 🎓 Score Interpretation

| Score | Meaning | Action |
|-------|---------|--------|
| **95-100%** | Excellent, authentic | ✅ Nothing to do |
| **90-94%** | Authentic | ✅ OK |
| **70-89%** | Probably authentic | ⚠️ Check if critical |
| **50-69%** | Suspicious | 🔍 Manual check |
| **0-49%** | Very suspicious | ❌ Delete/replace |

### Common Examples

**Score 95% - Electronic Music**
```
Reason: Full spectrum 22kHz | Minimal ultra-high content (mastering)
→ ✅ NORMAL for this musical style
```

**Score 20% - Transcoded MP3**
```
Reason: Cutoff 18kHz (MP3 192k) | No energy >16kHz
→ ❌ FAKE FLAC, it's a disguised MP3
```

**Score 80% - Corrupted Metadata**
```
Reason: Full spectrum | Inconsistent duration (2000ms)
→ ⚠️ REPAIRABLE with flac_detective.repair
```

---

## 🎯 Complete Workflow (3 Steps)

### STEP 1: ANALYSIS
```bash
python -m flac_detective.main
```
→ Generates text report

### STEP 2: SORT
1. Open text report
2. Search for files with low score
3. Spot "Duration Issue" ≠ "✓ OK"
4. Note files to process

### STEP 3: ACTIONS

**For scores < 50%:**
```bash
# Delete fake FLACs
del "fake_file.flac"
```

**For duration issues:**
```bash
# Repair
python -m flac_detective.repair "file.flac"
```

**For scores 50-89%:**
```bash
# Check manually
python -m flac_detective.main --file "file.flac"
```

---

## 💡 Interactive Helper

**For beginners, use the helper:**

```bash
python scripts/interactive_helper.py
```

**Guided Menu:**
1. 📖 Complete workflow
2. 💡 Practical examples
3. ⚠️ Important notes
4. 🔧 Launch analysis
5. 🛠️ Repair a file
6. 📁 Repair a folder

---

## ⚠️ Important Points

### Automatic Backups

During repair, a `.bak` file is created:
```
file.flac
file.flac.bak  ← Automatic backup
```

**After verification:**
```bash
# Delete backups
del *.bak
```

### Processing Time

**Analysis:**
- 1 file: ~3-7 seconds
- 1,000 files: ~1-2 hours
- 80,000 files: ~8-15 hours

**Repair:**
- 1 file: ~5-15 seconds
- 1 album (10 tracks): ~2-3 minutes

### Disk Space

**During repair:**
- Backup = original size
- Temporary WAV file = ~10x FLAC size

**Example:** 30 MB FLAC file
- Backup: 30 MB
- Temporary: 300 MB (deleted afterwards)

---

## 🆘 Common Issues

**"flac not found" error**
→ No longer an issue! We now use internal libraries.

**Script finds 0 files**
→ Check you are in the correct folder.

**All files at 100%**
→ Good news, your library is clean!

**Electronic music at 75%**
→ Normal! The v0.1 script is smart and adapts scores.

**Python Error**
→ Check Python 3.10+: `python --version`

---

## 📚 Complete Documentation

**Available files:**

- **README.md** - Main documentation
- **docs/README_FLAC_DETECTIVE.md** - Detailed guide

---

## 🎯 Quick Checklist

- [ ] Repository cloned / installed
- [ ] Test on 1 file successful
- [ ] Full analysis launched
- [ ] Text report generated
- [ ] Suspicious files identified
- [ ] Repairs performed (if necessary)
- [ ] Final verification OK

---

## 🏆 Final Result

**After analysis + repair:**

✅ Library cleaned of fake FLACs  
✅ Duration issues repaired  
✅ Professional report generated  
✅ Metadata 100% preserved  

**Your music library is now certified authentic!** 🎵

---

```
🔍 FLAC DETECTIVE v0.1
"Every FLAC file tells a story... I find the truth"

Version 0.1 - November 2025
Hunting Down Fake FLACs Since 2025
```
