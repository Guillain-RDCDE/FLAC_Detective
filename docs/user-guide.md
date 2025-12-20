# User Guide

Complete guide to using FLAC Detective effectively.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Command-Line Options](#command-line-options)
- [Understanding Results](#understanding-results)
- [Real-World Examples](#real-world-examples)
- [Batch Processing](#batch-processing)
- [Docker Usage](#docker-usage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Basic Usage

### Analyze a Directory

```bash
# Analyze current directory
flac-detective .

# Analyze specific folder
flac-detective /path/to/music

# Analyze with full path (Windows)
flac-detective "C:\Users\YourName\Music\FLAC"
```

### Analyze a Single File

```bash
flac-detective /path/to/file.flac
```

### Recursive Analysis

FLAC Detective automatically scans subdirectories:

```
Music/
├── Artist 1/
│   ├── Album A/
│   │   ├── 01 - Track.flac  ← Analyzed
│   │   └── 02 - Track.flac  ← Analyzed
│   └── Album B/
│       └── 01 - Track.flac  ← Analyzed
└── Artist 2/
    └── Album C/
        └── 01 - Track.flac  ← Analyzed
```

All `.flac` files are found and analyzed automatically.

## Command-Line Options

### Output Formats

```bash
# Default: Text report to console + file
flac-detective /music

# JSON output (for automation)
flac-detective /music --format json

# Save to specific file
flac-detective /music --output custom-report.txt

# JSON to file
flac-detective /music --format json --output results.json
```

### Analysis Options

```bash
# Verbose mode (show detailed rule execution)
flac-detective /music --verbose

# Faster analysis (15 seconds per file, less accurate)
flac-detective /music --sample-duration 15

# Longer analysis (60 seconds, more accurate)
flac-detective /music --sample-duration 60

# Auto-repair corrupted files
flac-detective /music --repair
```

### Combining Options

```bash
# Verbose + JSON + repair
flac-detective /music --verbose --format json --repair

# Fast scan with custom output
flac-detective /music --sample-duration 15 --output quick-scan.txt
```

## Understanding Results

### The Four Verdicts

#### ✅ AUTHENTIC (Score ≤ 30)

**Meaning**: Genuine lossless audio, very high confidence

**Typical characteristics**:
- Cutoff frequency at or near Nyquist (22050 Hz for 44.1kHz)
- No compression artifacts detected
- High spectral variance
- May have analog source signatures (vinyl, cassette)

**Example**:
```
VERDICT: AUTHENTIC ✅ (Score: 12/100)
REASON: Full spectrum preserved, no artifacts
RECOMMENDATION: File is genuine lossless. Keep as-is.
```

**Action**: Keep the file, it's authentic.

---

#### ⚡ WARNING (Score 31-60)

**Meaning**: Uncertain case, manual review needed

**Typical characteristics**:
- Cutoff slightly below Nyquist (20-21 kHz)
- Some minor artifacts but protected by other rules
- Could be legitimate high-quality source
- Could be borderline transcode

**Example**:
```
VERDICT: WARNING ⚡ (Score: 45/100)
REASON: Cutoff at 20500 Hz, minor artifacts
RECOMMENDATION: Verify with external tools. Could be legitimate.
```

**Action**:
1. Listen to the file carefully
2. Check source credibility
3. Use complementary tool (Fakin' the Funk, Spek)
4. Consider re-downloading if suspicious

---

#### ⚠️ SUSPICIOUS (Score 61-85)

**Meaning**: High confidence MP3 transcode

**Typical characteristics**:
- MP3 spectral signature detected (Rule 1: +50 pts)
- Cutoff matches known MP3 bitrate (128-256 kbps)
- Compression artifacts present
- Consistent patterns across file

**Example**:
```
VERDICT: SUSPICIOUS ⚠️ (Score: 72/100)
REASON: MP3 192 kbps signature detected
ANALYSIS:
  ✓ Rule 1: +50 pts - CBR pattern at 192 kbps
  ✓ Rule 2: +15 pts - Cutoff at 19500 Hz
  ✓ Rule 9: +7 pts - Pre-echo artifacts
RECOMMENDATION: High confidence transcode. Replace if possible.
```

**Action**:
1. Replace file from better source if available
2. Accept quality loss if no alternative
3. Document for future reference

---

#### ❌ FAKE_CERTAIN (Score ≥ 86)

**Meaning**: Definite MP3 transcode, absolute confidence

**Typical characteristics**:
- Multiple MP3 indicators confirmed
- Strong compression artifacts
- Suspicious metadata (fake 24-bit)
- Consistent MP3 patterns throughout

**Example**:
```
VERDICT: FAKE_CERTAIN ❌ (Score: 103/100)
REASON: Multiple MP3 signatures confirmed
ANALYSIS:
  ✓ Rule 1: +50 pts - MP3 128 kbps signature
  ✓ Rule 2: +30 pts - Cutoff at 16000 Hz
  ✓ Rule 4: +30 pts - Suspicious 24-bit encoding
  ✓ Rule 9: +15 pts - Multiple compression artifacts
RECOMMENDATION: Definitely transcoded. Delete and replace.
```

**Action**:
1. Delete the file
2. Find authentic source
3. Report to distributor if applicable

### Understanding Rule Contributions

Each rule can add or subtract points:

**Positive Rules** (Add points → Indicates fake):
- Rule 1: MP3 Spectral Signature (+50)
- Rule 2: Low Cutoff Frequency (+30)
- Rule 3: Bitrate Mismatch (+50)
- Rule 4: Suspicious 24-bit (+30)
- Rule 9: Compression Artifacts (+30)
- Rule 10: Multi-Segment Consistency (+20)

**Protection Rules** (Subtract points → Protects authentic):
- Rule 5: High Variance Protection (-40)
- Rule 6: High Quality Protection (-30)
- Rule 7: Vinyl & Silence Analysis (-100)
- Rule 8: Nyquist Exception (-50)
- Rule 11: Cassette Detection (-60)

### Report File Format

FLAC Detective saves a detailed text report:

```
FLAC AUTHENTICITY ANALYSIS REPORT
Generated: 2025-12-20 14:30:22
Analyzer Version: 0.9.0
Scan Path: /music/collection
======================================================================

SUMMARY
======================================================================
Total files analyzed: 245
Authentic files: 215 (87.8%)
Warning files: 18 (7.3%)
Suspicious files: 9 (3.7%)
Fake certain files: 3 (1.2%)

======================================================================
DETAILED RESULTS
======================================================================

[Individual file entries follow...]
```

## Real-World Examples

### Example 1: Cleaning Your Library

**Scenario**: You have 1000 FLAC files and want to identify fakes.

```bash
# Run analysis
flac-detective ~/Music/FLAC > analysis.txt

# Review summary
head -30 analysis.txt

# Find all fakes
grep "FAKE_CERTAIN" analysis.txt

# Find suspicious files
grep -E "SUSPICIOUS|FAKE_CERTAIN" analysis.txt
```

**Result interpretation**:
- 950 AUTHENTIC → Keep these
- 35 WARNING → Review manually
- 12 SUSPICIOUS → Replace if possible
- 3 FAKE_CERTAIN → Delete immediately

---

### Example 2: Verifying Downloads

**Scenario**: You downloaded an album from the internet.

```bash
# Analyze the album
flac-detective "/downloads/Pink Floyd - DSOTM (2011 Remaster)"

# Check results
```

**Outcomes**:
- All AUTHENTIC → Safe to import to library
- Some WARNING → Check source reputation, verify samples
- Any SUSPICIOUS/FAKE → Find better source

---

### Example 3: Pre-Upload Quality Check

**Scenario**: Before uploading to Bandcamp/streaming service.

```bash
# Verify your mastered album
flac-detective "/projects/my-album/masters"

# Ensure all files are AUTHENTIC
# Fix any issues before upload
```

---

### Example 4: Marketplace Purchase Verification

**Scenario**: Bought FLAC collection from seller.

```bash
# Verify authenticity
flac-detective "/purchased/jazz-collection"

# Calculate fake percentage
# >20% fakes → Request refund
# <5% fakes → Accept (normal variation)
```

## Batch Processing

### Process Multiple Folders

```bash
#!/bin/bash
# analyze-all.sh

for artist in ~/Music/FLAC/*/; do
    echo "Analyzing: $(basename "$artist")"
    flac-detective "$artist" --output "reports/$(basename "$artist").txt"
done
```

### Find and Move Suspicious Files

```bash
#!/bin/bash
# quarantine-fakes.sh

mkdir -p ~/Music/quarantine

# Run analysis and save
flac-detective ~/Music/FLAC --format json > results.json

# Parse JSON and move files (requires jq)
jq -r '.files[] | select(.score >= 61) | .filepath' results.json | while read file; do
    mv "$file" ~/Music/quarantine/
done
```

### Parallel Processing (Advanced)

```bash
#!/bin/bash
# Fast parallel analysis using GNU parallel

find ~/Music -name "*.flac" | parallel -j 4 "flac-detective {} --format json >> results.jsonl"
```

## Docker Usage

### Basic Docker Commands

```bash
# Pull latest image
docker pull ghcr.io/guillainm/flac-detective:latest

# Analyze directory
docker run --rm \
  -v /path/to/music:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data

# Save report outside container
docker run --rm \
  -v /path/to/music:/data \
  -v /path/to/reports:/reports \
  ghcr.io/guillainm/flac-detective:latest \
  /data --output /reports/report.txt
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  flac-detective:
    image: ghcr.io/guillainm/flac-detective:latest
    volumes:
      - ./music:/data
      - ./reports:/reports
    command: /data --output /reports/analysis.txt
```

Run:

```bash
docker-compose up
```

### Windows Docker Examples

```powershell
# Windows PowerShell
docker run --rm `
  -v "C:\Users\YourName\Music":/data `
  ghcr.io/guillainm/flac-detective:latest `
  /data
```

## Best Practices

### 1. Regular Library Audits

```bash
# Monthly check
flac-detective ~/Music/FLAC --output "reports/audit-$(date +%Y%m).txt"
```

### 2. Verify Before Archiving

Always check files before long-term storage:

```bash
flac-detective /staging/to-archive
# Only archive if all AUTHENTIC
```

### 3. Document Questionable Files

Keep a log of WARNING files:

```bash
grep "WARNING" report.txt > warnings.txt
# Review periodically
```

### 4. Use Multiple Tools for Confirmation

FLAC Detective is excellent but not perfect:
- Use Fakin' the Funk for second opinion
- Visual inspection with Spek
- Listen with quality headphones

### 5. Understand Your Sources

Different sources have different characteristics:
- **Vinyl rips**: May trigger Rule 7 (protected)
- **Cassette transfers**: May trigger Rule 11 (protected)
- **High-quality MP3 320**: Rule 6 provides some protection
- **Streaming rips**: Often SUSPICIOUS or FAKE_CERTAIN

## Troubleshooting

### Issue: High False Positive Rate

**Symptoms**: Many authentic files marked as SUSPICIOUS

**Causes**:
- Vinyl or cassette sources
- Aggressive mastering
- Special audio processing

**Solution**: Check if files are protected by Rules 7 or 11. If not, file a bug report with samples.

---

### Issue: Slow Performance

**Symptoms**: Analysis takes >10 seconds per file

**Causes**:
- Network drives
- Very large files (>100MB)
- Slow disk I/O

**Solutions**:
```bash
# Use shorter sample duration
flac-detective /music --sample-duration 15

# Copy to local disk first
cp -r /network/music /tmp/local-copy
flac-detective /tmp/local-copy
```

---

### Issue: "ModuleNotFoundError"

**Symptoms**: Python import errors

**Solution**:
```bash
# Reinstall dependencies
pip install --upgrade flac-detective

# Or install from source
pip install -e ".[dev]"
```

---

### Issue: Corrupted FLAC Files

**Symptoms**: "FLAC decoder error" messages

**Solution**:
```bash
# Enable auto-repair
flac-detective /music --repair

# Manual repair with flac tool
flac --verify --decode-through-errors file.flac
```

---

### Issue: Docker Volume Permissions

**Symptoms**: "Permission denied" in Docker

**Solution** (Linux):
```bash
# Run with current user
docker run --rm \
  --user $(id -u):$(id -g) \
  -v /path/to/music:/data \
  ghcr.io/guillainm/flac-detective:latest \
  /data
```

## Advanced Tips

### Customize Thresholds (Python)

```python
from flac_detective import FLACAnalyzer

analyzer = FLACAnalyzer(sample_duration=45.0)
# Analyze with custom parameters
```

### Integration with Music Players

```bash
# Create playlist of authentic files
flac-detective ~/Music --format json | jq -r '.files[] | select(.score <= 30) | .filepath' > authentic.m3u
```

### Automated Quality Monitoring

```bash
# Cron job: daily library check
0 2 * * * /usr/local/bin/flac-detective ~/Music --output ~/reports/daily-$(date +\%Y\%m\%d).txt
```

## Getting More Help

- **Detailed technical info**: [Technical Details](technical-details.md)
- **Python API usage**: [API Reference](api-reference.md)
- **Development & bugs**: [Contributing](contributing.md)
- **Installation issues**: [Getting Started](getting-started.md)

---

**Happy analyzing!** For questions, visit [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions).
