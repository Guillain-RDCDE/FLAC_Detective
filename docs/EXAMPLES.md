# 📚 Examples & Usage Scenarios

## Basic Usage

### Analyze a Folder

```bash
python -m flac_detective /path/to/music/folder
```

Output:
```
======================================================================
  FLAC AUTHENTICITY ANALYZER
  Detection of MP3s transcoded to FLAC
======================================================================

⠋ Analyzing audio files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  15% 0:02:34

======================================================================
  ANALYSIS COMPLETE
======================================================================
  FLAC files analyzed: 245
  Fake/Suspicious FLAC files: 3 (including 1 certain fakes)
  Text report: flac_report_20251218_123456.txt
======================================================================
```

### Analyze Single File

```bash
python -m flac_detective /path/to/single/file.flac
```

### Check Specific Artist Folder

```bash
python -m flac_detective "/music/Metallica - Master of Puppets (2015 Remaster)"
```

---

## Understanding Results

### Report File Example

```
FLAC AUTHENTICITY ANALYSIS REPORT
Generated: 2025-12-18 12:34:56
===============================================================

FILE 1: Metallica - Enter Sandman.flac
Location: /music/Metallica/
Duration: 5:29 | Sample Rate: 44100 Hz | Channels: 2 | Bit Depth: 16

VERDICT: SUSPICIOUS ⚠️ (Score: 72/100)
Confidence: High

ANALYSIS:
  ✓ Rule 1 (MP3 Spectral): +50 pts
    Reason: Constant MP3 bitrate detected (Spectral): 192 kbps
  
  ✓ Rule 2 (Cutoff vs Nyquist): +15 pts
    Reason: Cutoff frequency (19500 Hz) is 2500 Hz below threshold
  
  ✓ Rule 9 (Compression Artifacts): +7 pts
    Reason: Pre-echo detected in vocals section
  
  ✓ Rule 5 (VBR Protection): -10 pts
    Reason: High bitrate variance indicates legitimate encoding

RECOMMENDATION: Manually verify with external tools (Fakin the Funk, etc)
===============================================================
```

---

## Interpreting Scores

### Score ≤ 30: AUTHENTIC ✅

```
Example reasons:
- Cutoff frequency at Nyquist (22050 Hz)
- High spectral variance (VBR patterns)
- No compression artifacts detected
- Cassette tape characteristics identified (analog source)

Action: Keep file as-is. Very high confidence.
```

### Score 31-60: WARNING ⚡

```
Example reasons:
- Cutoff slightly below Nyquist (20000-21000 Hz)
- Some compression artifacts detected
- Moderate bitrate variance

Action: Investigate further. Use another tool (Fakin the Funk).
        Listen for quality issues. Consider re-downloading.
```

### Score 61-85: SUSPICIOUS ⚠️

```
Example reasons:
- MP3 spectral signature detected (+50 pts)
- Cutoff frequency matches 192-256 kbps MP3 range
- Compression artifacts confirmed
- Container bitrate high but matches MP3 pattern

Action: High confidence MP3 upscale. Replace with authentic source
        or accept quality loss.
```

### Score ≥ 86: FAKE_CERTAIN ❌

```
Example reasons:
- Multiple MP3 signatures confirmed
- 24-bit suspicious encoding detected
- Pre-echo and aliasing artifacts
- Consistent MP3 patterns across entire file

Action: Definitely MP3 upscale. Replace immediately.
        Report source if from music service.
```

---

## Real-World Scenarios

### Scenario 1: Verifying Music Collection Quality

```bash
# Analyze entire music library
python -m flac_detective ~/Music/FLAC_Collection

# Results show:
# - 2450 authentic files ✅
# - 18 suspicious files ⚠️
# - 3 fake certain files ❌

# Action: Manually review the 21 files
# Re-download suspicious ones from trusted source
```

### Scenario 2: Quality Control Before Upload

```bash
# Before uploading to music service, verify sources
python -m flac_detective /staging/new_album

# FAKE_CERTAIN files detected? → Don't upload
# SUSPICIOUS files? → Review metadata, check source
# AUTHENTIC files? → Safe to upload
```

### Scenario 3: Marketplace Verification

```bash
# Received FLAC collection from seller
python -m flac_detective /downloaded_collection

# If >50% suspicious/fake → Dispute purchase
# If <5% suspicious → Accept (normal variations)
# If >20% suspicious → Request refund
```

---

## Batch Processing

### Process Multiple Folders

```bash
#!/bin/bash
for folder in /music/*/; do
    echo "Analyzing: $folder"
    python -m flac_detective "$folder"
done
```

### Process and Move Fakes

```bash
#!/bin/bash
# Run analysis and capture results
python -m flac_detective /music > analysis.txt

# Move suspicious files
mkdir -p /music/review
grep "FAKE_CERTAIN" analysis.txt | while read line; do
    file=$(echo "$line" | awk '{print $1}')
    mv "$file" /music/review/
done
```

---

## Advanced Usage

### Custom Threshold Configuration

```python
from flac_detective.config import Config

# Adjust thresholds
Config.SCORE_THRESHOLD_FAKE = 80  # Lower = more aggressive
Config.SCORE_THRESHOLD_SUSPICIOUS = 50

from flac_detective.analysis.analyzer import AudioAnalyzer
analyzer = AudioAnalyzer()
context = analyzer.analyze_file("test.flac")
print(f"Verdict: {context.verdict}")
```

### Integrate with Scripts

```python
from pathlib import Path
from flac_detective.analysis.analyzer import AudioAnalyzer

def check_audio_files(folder):
    """Check all FLAC files in folder."""
    analyzer = AudioAnalyzer()
    results = {}
    
    for flac_file in Path(folder).glob("*.flac"):
        context = analyzer.analyze_file(str(flac_file))
        results[flac_file.name] = {
            "score": context.score,
            "verdict": context.verdict,
            "reasons": context.reasons
        }
    
    return results

# Use it
results = check_audio_files("/music/album")
for filename, data in results.items():
    print(f"{filename}: {data['verdict']} ({data['score']}/100)")
```

---

## Troubleshooting Examples

### Issue: High false positive rate

```bash
# Lower the threshold
# Edit src/flac_detective/config.py
# Change: SCORE_THRESHOLD_SUSPICIOUS from 60 to 70

# Re-run analysis
python -m flac_detective /music
```

### Issue: Slow analysis on network drive

```bash
# Copy files locally first
cp -r /network/music /tmp/music_copy

# Then analyze
python -m flac_detective /tmp/music_copy
```

### Issue: Memory issues with large files

```bash
# Process one file at a time
for file in /music/*.flac; do
    python -m flac_detective "$file"
    sleep 1  # Cool down
done
```

---

## See Also

- [RULES.md](RULES.md) - Understand each detection rule
- [ARCHITECTURE.md](ARCHITECTURE.md) - How the system works
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
