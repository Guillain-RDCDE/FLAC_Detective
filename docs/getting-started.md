# Getting Started with FLAC Detective

This guide will help you install and run your first FLAC analysis in minutes.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [First Analysis](#first-analysis)
- [Understanding Results](#understanding-results)
- [Next Steps](#next-steps)

## System Requirements

### Required
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux

### Optional (Recommended)
- **FLAC command-line tool**: For advanced repair features
  - Linux: `sudo apt-get install flac`
  - macOS: `brew install flac`
  - Windows: Download from [Xiph.org](https://xiph.org/flac/download.html)

## Installation

### Option 1: Install via pip (Recommended)

The easiest way to install FLAC Detective:

```bash
pip install flac-detective
```

Verify installation:

```bash
flac-detective --version
```

### Option 2: Install via Docker

Pull the pre-built Docker image:

```bash
docker pull ghcr.io/guillainm/flac-detective:latest
```

Test it:

```bash
docker run --rm ghcr.io/guillainm/flac-detective:latest --version
```

### Option 3: Install from Source

For development or the latest features:

```bash
# Clone the repository
git clone https://github.com/GuillainM/FLAC_Detective.git
cd FLAC_Detective

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## First Analysis

### Analyze a Directory

```bash
# Basic usage - analyze current directory
flac-detective .

# Analyze specific directory
flac-detective /path/to/your/music

# Example on Windows
flac-detective "C:\Users\YourName\Music\FLAC Collection"
```

### Analyze a Single File

```bash
flac-detective /path/to/song.flac
```

### Docker Usage

```bash
# Mount your music directory and analyze
docker run --rm -v /path/to/music:/data ghcr.io/guillainm/flac-detective:latest /data

# Windows example
docker run --rm -v "C:\Users\YourName\Music":/data ghcr.io/guillainm/flac-detective:latest /data
```

### What Happens During Analysis

When you run FLAC Detective, it will:

1. **Scan** for all `.flac` files recursively
2. **Analyze** each file using 11 detection rules
3. **Display** progress with a real-time progress bar
4. **Generate** a detailed report
5. **Save** results to a timestamped text file

## Understanding Results

### Console Output

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
  Text report: flac_report_20251220_143022.txt
======================================================================
```

### The Four Verdicts

FLAC Detective assigns one of four verdicts to each file:

| Verdict | Score Range | Icon | Meaning | What to Do |
|---------|-------------|------|---------|-----------|
| **AUTHENTIC** | ≤ 30 | ✅ | Genuine lossless audio | Keep the file |
| **WARNING** | 31-60 | ⚡ | Uncertain, needs review | Manual verification recommended |
| **SUSPICIOUS** | 61-85 | ⚠️ | Likely MP3 transcode | Replace if possible |
| **FAKE_CERTAIN** | ≥ 86 | ❌ | Definite MP3 transcode | Delete and replace |

### Sample Report Entry

```
FILE: Metallica - Enter Sandman.flac
Location: /music/Metallica/Black Album/
Duration: 5:29 | Sample Rate: 44100 Hz | Bit Depth: 16

VERDICT: SUSPICIOUS ⚠️ (Score: 72/100)

REASON: MP3 192 kbps signature detected

ANALYSIS DETAILS:
  ✓ Rule 1 (MP3 Spectral): +50 pts - CBR pattern at 192 kbps
  ✓ Rule 2 (Cutoff Frequency): +15 pts - Cutoff at 19500 Hz
  ✓ Rule 9 (Compression): +7 pts - Pre-echo artifacts

RECOMMENDATION: Likely MP3 transcode. Consider re-downloading from source.
```

### Score Interpretation

- **0-30**: File passes all authenticity checks → Keep it
- **31-60**: Borderline case → Verify manually
- **61-85**: Strong indicators of transcode → Likely fake
- **86-150**: Multiple definitive indicators → Definitely fake

## Common Use Cases

### Case 1: Verify Downloaded Album

```bash
# You downloaded an album and want to verify quality
flac-detective "/downloads/Pink Floyd - Dark Side of the Moon"

# If all files are AUTHENTIC → Good to go!
# If some are SUSPICIOUS → Re-download from better source
# If FAKE_CERTAIN → Report to source, find alternative
```

### Case 2: Clean Your Music Library

```bash
# Analyze your entire collection
flac-detective ~/Music/FLAC

# Review the generated report
# Delete or replace suspicious files
# Keep authentic files
```

### Case 3: Quality Control Before Sharing

```bash
# Before uploading to a music platform
flac-detective "/staging/my-album"

# Only upload if all files are AUTHENTIC
```

## Command-Line Options

```bash
# Generate JSON output instead of text
flac-detective /path/to/music --format json

# Save output to specific file
flac-detective /path/to/music --output my-report.txt

# Verbose mode (show detailed analysis)
flac-detective /path/to/music --verbose

# Enable auto-repair of corrupted files
flac-detective /path/to/music --repair

# Analyze only first 15 seconds (faster, less accurate)
flac-detective /path/to/music --sample-duration 15
```

## Troubleshooting

### "Command not found: flac-detective"

**Solution**: The package isn't in your PATH. Try:
```bash
python -m flac_detective /path/to/music
```

### "No FLAC files found"

**Solution**:
- Verify you're pointing to the correct directory
- Check that files have `.flac` extension (not `.FLAC` on Linux)
- Use `ls` or `dir` to confirm files exist

### "Permission denied" errors

**Solution**:
```bash
# On Linux/macOS, you may need to fix permissions
chmod +r /path/to/music/*.flac

# Or run with sudo (not recommended)
sudo flac-detective /path/to/music
```

### Analysis is very slow

**Causes**: Network drives, very large files, slow disk

**Solutions**:
- Copy files to local disk first
- Use `--sample-duration 15` for faster analysis
- Close other applications

### Docker: "Cannot access /data"

**Solution**: Ensure volume mount is correct
```bash
# Windows - use forward slashes or escape backslashes
docker run --rm -v "C:/Users/Name/Music":/data ghcr.io/guillainm/flac-detective:latest /data

# Linux/macOS - use absolute paths
docker run --rm -v "/home/user/music":/data ghcr.io/guillainm/flac-detective:latest /data
```

## Next Steps

Now that you've completed your first analysis:

1. **Learn more about usage** → Read the [User Guide](user-guide.md)
2. **Understand how it works** → Read [Technical Details](technical-details.md)
3. **Use the Python API** → Read [API Reference](api-reference.md)
4. **Contribute or customize** → Read [Contributing](contributing.md)

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
- **Bug reports**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Documentation**: [Documentation Index](index.md)

---

**Ready to analyze?** Run `flac-detective /path/to/music` and you're good to go!
