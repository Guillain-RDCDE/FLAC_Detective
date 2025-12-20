# 📋 Troubleshooting Guide

## Common Issues & Solutions

### Installation Issues

#### "pip: command not found"
```bash
# Make sure Python is installed
python --version

# Or use python3
python3 -m pip install -r requirements.txt
```

#### "FFmpeg not found"
```bash
# Install FFmpeg:
# Windows (chocolatey):
choco install ffmpeg

# macOS (homebrew):
brew install ffmpeg

# Linux (Ubuntu/Debian):
sudo apt-get install ffmpeg

# Verify:
ffmpeg -version
```

#### "ModuleNotFoundError: No module named 'flac_detective'"
```bash
# Reinstall in development mode
pip install -e .

# Or ensure you're in project root
cd /path/to/FLAC_Detective
python -m flac_detective /path/to/files
```

---

### Runtime Issues

#### "No FLAC files found"
```bash
# Check path exists
ls /path/to/files

# Make sure files have .flac extension
# FLAC Detective only processes .flac files
```

#### "Permission denied"
```bash
# Ensure you have read access
# macOS/Linux:
ls -l /path/to/files

# Windows: Check file properties
# Give read access if needed
chmod +r /path/to/files/*.flac
```

#### "File too large to analyze"
```bash
# Large files may cause memory issues
# Try analyzing individual files or smaller batches
python -m flac_detective /path/to/single/file.flac

# Check available memory
free -h  # Linux
vm_stat  # macOS
wmic OS get TotalVisibleMemorySize  # Windows
```

---

### Analysis Issues

#### "All files scoring as AUTHENTIC but I expected fakes"
```
Possible causes:
1. Files ARE authentic (not MP3 upscales)
2. High-quality MP3 (320 kbps) upscale with full spectrum preserved
3. Too conservative thresholds

Check using Fakin the Funk or other tools to verify.
See docs/COLLECTION_ZANZIBARA_IMPLICATIONS.md for details.
```

#### "Files scoring inconsistently"
```bash
# Clear cache and rescan
rm -rf src/flac_detective/analysis/__pycache__
pytest tests/ --cache-clear

# Ensure FFmpeg is consistent
ffmpeg -version
```

#### "Memory usage very high"
```bash
# Disable caching (uses more CPU but less RAM)
# Edit config.py:
# ENABLE_AUDIO_CACHE = False

# Or process files one at a time
for file in /path/to/files/*.flac; do
    python -m flac_detective "$file"
done
```

---

### Output Issues

#### "No output file generated"
```bash
# Check if analysis completed
# Look for: "Analysis complete" message

# Try specifying output directory
python scripts/run_detective.py --output /tmp/reports
```

#### "Report file is empty"
```bash
# This shouldn't happen - file a bug report with:
# - Number of files analyzed
# - File types
# - Error messages from console
# - Python version (python --version)
```

#### "Console output garbled (Unicode issues)"
```bash
# Set UTF-8 encoding
export PYTHONIOENCODING=utf-8
python -m flac_detective /path/to/files

# Or on Windows:
$env:PYTHONIOENCODING = "utf-8"
```

---

### Testing Issues

#### "Tests fail with import errors"
```bash
# Install in development mode
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest tests/ -v
```

#### "Some tests hang or timeout"
```bash
# Run with timeout (10 seconds per test)
pytest tests/ --timeout=10

# Or skip slow tests
pytest tests/ -m "not slow"
```

#### "Test coverage report not generated"
```bash
# Install coverage
pip install pytest-cov

# Generate report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # View in browser
```

---

### Performance Issues

#### "Analysis is very slow"
```
Possible causes:
1. Network-mounted files (slow I/O)
2. FFT computation on very long files
3. Parallel analysis disabled

Solutions:
1. Copy files locally first
2. Process files in batches
3. Check CPU usage (might be maxed out)
```

#### "High CPU usage"
```bash
# This is normal during FFT computation
# If sustained >80% idle time, might indicate issue

# Check active processes
top -p $(pgrep -f flac_detective)  # macOS/Linux
tasklist | find "python"           # Windows
```

---

### Reporting Issues

When reporting a bug, include:

1. **Python version**: `python --version`
2. **OS**: Windows/macOS/Linux
3. **Sample FLAC file**: If possible, provide for analysis
4. **Console output**: Full error messages
5. **Steps to reproduce**: Exact commands you ran
6. **Expected vs actual**: What should happen vs what did

**Example report:**
```
Title: Rule 1 scores all files as SUSPICIOUS

Environment:
- Python 3.9.2
- Windows 10
- FLAC Detective v0.7.0

Steps:
1. Copied 100 authentic FLAC files to D:\FLACs
2. Ran: python -m flac_detective D:\FLACs

Expected:
- Most files score AUTHENTIC (≤30)

Actual:
- All files score SUSPICIOUS (65+)

Attachments:
- Console output (console.txt)
- Sample file (sample.flac)
```

---

## Getting Help

- **Documentation**: Check [INDEX.md](INDEX.md)
- **GitHub Issues**: https://github.com/GuillainM/FLAC_Detective/issues
- **Source Code**: Browse [../src/](../src/) for implementation details
- **Tests**: Check [tests/](../../tests/) for usage examples

---

## Frequently Asked Questions

**Q: Why does my authentic FLAC score as WARNING?**
A: Some characteristics of your file might match MP3 patterns. Manually review or use another tool.

**Q: Can I tune the thresholds?**
A: Yes! Edit `src/flac_detective/config.py` to adjust scoring weights.

**Q: Does FLAC Detective work with other formats (ALAC, WavPack)?**
A: Currently FLAC only. Other formats could be added - open an issue if interested.

**Q: How accurate is the detection?**
A: ~89.1% authentic detection with <0.5% false positives (based on test suite).

**Q: Can I use this commercially?**
A: Yes! MIT licensed - attribution appreciated but not required.

---

**Still stuck?** Open an issue with details from the "Reporting Issues" section above.
