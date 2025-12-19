# Diagnostic & Troubleshooting Guide

## Overview

FLAC Detective includes a comprehensive diagnostic system that tracks and handles file reading issues during analysis. This ensures reliable results even when encountering temporary I/O errors or decoder problems.

## How It Works

### Automatic Error Handling

The analyzer implements a multi-layered approach to handle file reading issues:

1. **Retry Mechanism**: Temporary decoder errors (e.g., "lost sync") are retried up to 5 times with exponential backoff
2. **Partial Read Fallback**: If full file reading fails, the system attempts to read as much data as possible in chunks
3. **Repair Attempts**: For persistent errors, FLAC files are re-encoded using the official `flac` tool
4. **Copy-to-Temp Strategy**: Files are copied to local temp storage before analysis to minimize I/O issues from network/USB drives

### Issue Types Tracked

The diagnostic system tracks 7 types of issues:

- **PARTIAL_READ**: File was analyzed using partial data (still valid for MP3 detection)
- **DECODER_SYNC_LOST**: FLAC decoder lost synchronization temporarily
- **READ_FAILED**: Complete failure to read file data
- **REPAIR_ATTEMPTED**: System attempted to repair the FLAC file
- **REPAIR_FAILED**: FLAC repair process failed
- **SEEK_FAILED**: Error seeking to specific position in file
- **CORRUPTED**: File appears to be genuinely corrupted

## Understanding the Output

### During Analysis

With the improved logging system, you'll see a clean progress bar without error spam:

```
Analyzing FLAC files...
[████████████████████████████████████] 273/273 files (100%)
```

### After Analysis

At the end, you'll see a summary if issues were encountered:

```
======================================================================
  ANALYSIS COMPLETE
======================================================================
  FLAC files analyzed: 273
  Fake/Suspicious FLAC files: 2 (including 2 certain fakes)
  ⚠️  Files with reading issues: 15 (0 critical)
  Text report: flac_report_20251219_095028.txt
  Diagnostic report: flac_diagnostic_20251219_095028.txt
======================================================================
```

### Interpreting Results

- **Files with reading issues**: Number of files that had temporary problems but were still analyzed
- **Critical failures**: Files that could not be analyzed at all (rare)
- **Diagnostic report**: Detailed file listing all issues encountered

## The Diagnostic Report

When issues are detected, a `flac_diagnostic_[timestamp].txt` file is generated with:

### Summary Section
```
SUMMARY:
  Total files analyzed: 273
  Files with issues: 15 (5.5%)
  Clean files: 258
  Critical failures: 0
```

### Issue Types Breakdown
```
ISSUE TYPES:
  partial_read: 8
  decoder_sync_lost: 5
  repair_attempted: 2
```

### Detailed File Issues
```
[WARNING] 04 - Stop whispering.flac
  Path: D:\FLAC\Internal\Radiohead\(1993) Pablo honey\04 - Stop whispering.flac
  Issue 1: decoder_sync_lost
    Time: 10:15:42
    Message: Error : flac decoder lost sync.
    Retries: 5
  Issue 2: partial_read
    Time: 10:15:43
    Message: Partial read after decoder errors
    Data read: 8847360/19404800 frames (45.6%)
    Retries: 5
```

## Important Notes

### Partial Analysis is Valid

Files marked with "partial_read" are **still reliable** for MP3 transcode detection because:

- MP3 transcodes show frequency cutoffs consistently throughout the file
- Only 30 seconds of audio are needed for spectral analysis
- Partial reads typically provide 200+ seconds of data
- The analysis explicitly notes when it's partial: `(analysé à partir d'une lecture partielle du fichier)`

### File Integrity vs. I/O Errors

Many "decoder errors" are actually temporary I/O issues, not file corruption:

- Reading from USB/network drives can cause transient errors
- The copy-to-temp strategy minimizes these issues
- Use `tools/diagnose_flac.py` to verify actual file integrity

## Troubleshooting Tools

### Check File Integrity

Located in `tools/diagnose_flac.py`, this script uses the official FLAC tool to verify file integrity:

```bash
python tools/diagnose_flac.py "D:\FLAC\Internal\Radiohead"
```

Output shows which files are truly corrupted vs. just having I/O issues:
```
[273/273] Testing: 15 Step.flac                              [OK]

DIAGNOSTIC REPORT
================================================================================
Total files:       273
Healthy files:     262 (95.9%)
Corrupted files:   11 (4.0%)
```

### Test Diagnostic System

Located in `tools/test_diagnostic.py`, verifies the diagnostic tracking works correctly:

```bash
python tools/test_diagnostic.py
```

### Manual Analysis Runner

Located in `tools/run_analysis.py`, runs analysis with encoding fixes:

```bash
python tools/run_analysis.py "D:\FLAC\Internal\Radiohead"
```

## Reducing I/O Errors

If you experience many I/O errors:

1. **Copy files locally**: Move FLAC collection to internal drive before analysis
2. **Check drive health**: Run disk diagnostic tools (e.g., `chkdsk` on Windows)
3. **Reduce workers**: Use fewer parallel workers with `--workers` flag (if implemented)
4. **Check USB connection**: For external drives, try different USB ports/cables

## When to Worry

You should investigate further if:

- **High critical failure rate** (>5%): Indicates genuinely corrupted files
- **Consistent errors on same files**: Specific files may need repair
- **100% failure rate**: Drive or connection issues

You can usually ignore:

- **Low partial read rate** (<10%): Normal for large collections on external drives
- **Occasional decoder sync lost**: Handled automatically with retries
- **Repair attempts**: System is working as designed

## FAQ

**Q: Will partial analysis affect fake FLAC detection accuracy?**
A: No. MP3 transcodes show consistent frequency cutoffs, detectable in any 30-second segment.

**Q: Should I re-encode files that show errors?**
A: Only if `diagnose_flac.py` confirms actual corruption. Most errors are temporary I/O issues.

**Q: Why do I see fewer errors now compared to before?**
A: Console logging level was changed from INFO to WARNING to reduce noise. All errors are still tracked in the diagnostic report.

**Q: Can I disable diagnostic tracking?**
A: No, it's integral to the analysis system and ensures result reliability.

## Technical Details

### Retry Configuration

Default retry parameters (defined in `audio_loader.py`):
- **max_attempts**: 5 retries
- **initial_delay**: 0.2 seconds
- **backoff_multiplier**: 2.0 (exponential backoff)

### Temporary Error Patterns

Errors that trigger automatic retry:
- "lost sync"
- "decoder error"
- "sync error"
- "invalid frame"
- "unexpected end"
- "unknown error"

### Logging Levels

- **Console**: WARNING level (shows only important messages)
- **File log**: DEBUG level (captures everything)
- **Diagnostic report**: All issues with full context

## Related Documentation

- [README.md](README.md) - Main documentation
- [GETTING_STARTED_NEW_USERS.md](GETTING_STARTED_NEW_USERS.md) - Quick start guide
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Technical architecture
