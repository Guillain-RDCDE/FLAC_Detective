# FLAC Detective - Development Tools

This directory contains utility scripts for testing, diagnostics, and development.

## Scripts

### `diagnose_flac.py`

**Purpose**: Verify FLAC file integrity using the official `flac` command-line tool.

**Usage**:
```bash
python tools/diagnose_flac.py "D:\FLAC\Internal\Radiohead"
```

**Output**: Generates a diagnostic report showing which files are healthy vs. corrupted, with error type classification (LOST_SYNC, BAD_HEADER, CRC_MISMATCH, etc.)

**When to Use**:
- To distinguish between temporary I/O errors and actual file corruption
- After seeing many "reading issues" in FLAC Detective analysis
- To identify files that need repair or re-download

---

### `test_diagnostic.py`

**Purpose**: Test the diagnostic tracking system functionality.

**Usage**:
```bash
python tools/test_diagnostic.py
```

**Output**: Simulates various file issues and displays diagnostic statistics and reports.

**When to Use**:
- To verify diagnostic system is working correctly after code changes
- For development and testing of error tracking features

---

### `run_analysis.py`

**Purpose**: Run FLAC Detective with encoding fixes for Windows console issues.

**Usage**:
```bash
python tools/run_analysis.py "D:\FLAC\Internal\Radiohead"
```

**Features**:
- Automatically sets UTF-8 encoding on Windows
- Avoids LOGO display issues in some terminal environments
- Useful for CI/CD or automated scripts

**When to Use**:
- If you encounter encoding errors with the standard CLI
- For integration with other scripts or automation tools
- In environments where Rich formatting causes issues

---

## Requirements

All scripts require FLAC Detective to be installed:

```bash
pip install -e .
```

For `diagnose_flac.py`, the `flac` command-line tool must be installed:

- **Linux/Debian**: `sudo apt-get install flac`
- **macOS**: `brew install flac`
- **Windows**: Download from [xiph.org](https://xiph.org/flac/download.html)

---

## Development Notes

These tools are designed for:
- **Testing**: Verifying system behavior
- **Diagnostics**: Troubleshooting file issues
- **Integration**: Running FLAC Detective in automated environments

They are not required for normal FLAC Detective usage via the CLI (`flac-detective` command).
