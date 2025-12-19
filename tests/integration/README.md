# Integration Tests

This directory contains integration tests for validating FLAC Detective's core functionality.

## Test Scripts

### `test_source_integrity.py`
Tests the integrity of source FLAC files on disk.

**Usage:**
```bash
python tests/integration/test_source_integrity.py "path/to/flac/directory"
```

**Purpose:**
- Validates FLAC files using the official `flac --test` command
- Identifies corrupted files at the source
- Generates detailed reports of file integrity

### `test_copy_integrity.py`
Tests whether file copy operations introduce corruption.

**Usage:**
```bash
python tests/integration/test_copy_integrity.py "path/to/flac/file.flac"
```

**Purpose:**
- Validates that `shutil.copy2()` preserves file integrity
- Compares SHA256 hashes before/after copy
- Tests FLAC integrity after copying

### `test_parallel_copy_stress.py`
Stress tests parallel file copying under load.

**Usage:**
```bash
python tests/integration/test_parallel_copy_stress.py "path/to/flac/directory"
```

**Purpose:**
- Simulates parallel file processing (like during actual scans)
- Tests for race conditions or I/O corruption
- Validates integrity under concurrent operations

## Running All Tests

```bash
# Test a single file
python tests/integration/test_copy_integrity.py "file.flac"

# Test entire directory integrity
python tests/integration/test_source_integrity.py "music/collection" --verbose

# Stress test with parallel operations
python tests/integration/test_parallel_copy_stress.py "music/collection"
```

## Test Results

All tests generate detailed output showing:
- ✅ Success indicators
- ❌ Failure indicators with error messages
- Summary statistics
- Detailed diagnostic information
