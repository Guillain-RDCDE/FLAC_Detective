# Unit Tests

This directory contains unit tests for FLAC Detective functionality.

## Test Files

### `test_repair_functions.py`
Comprehensive unit tests for the FLAC repair functionality introduced in v0.8.0.

**Tests coverage:**
- `_extract_metadata()` - Metadata extraction from FLAC files
- `_restore_metadata()` - Metadata restoration to FLAC files
- `repair_flac_file()` - Complete 6-step repair process

**Test scenarios:**
- ✅ Successful metadata extraction with tags and pictures
- ✅ Files without tags
- ✅ Multi-value tags (multiple artists, genres)
- ✅ Multiple album art pictures
- ✅ Successful metadata restoration
- ✅ Empty metadata handling
- ✅ Complete FLAC file repair process
- ✅ Decode/encode/verify failure handling
- ✅ Source file replacement with backup
- ✅ Timeout handling
- ✅ WAV cleanup after repair
- ✅ Exception handling throughout
- ✅ Mutagen not available scenarios

## Running Tests

### Requirements

**Python Version:** 3.8 - 3.12

**Important:** Python 3.13+ may have compatibility issues with scipy/numpy. If you encounter errors like:

```
ValueError: _CopyMode.IF_NEEDED is neither True nor False
```

This indicates a numpy/scipy compatibility issue with Python 3.14+. Please use Python 3.8-3.12.

### Installation

```bash
# Install test dependencies
pip install -e ".[dev]"
```

This installs:
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- Other development tools

### Running All Unit Tests

```bash
# From project root
pytest tests/unit/ -v

# With coverage report
pytest tests/unit/ -v --cov=flac_detective --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_repair_functions.py -v

# Run specific test class
pytest tests/unit/test_repair_functions.py::TestExtractMetadata -v

# Run specific test method
pytest tests/unit/test_repair_functions.py::TestRepairFlacFile::test_repair_flac_file_success -v
```

### Coverage Goals

Target coverage for new repair functions:
- `_extract_metadata()`: ≥ 90%
- `_restore_metadata()`: ≥ 90%
- `repair_flac_file()`: ≥ 85%

## Test Structure

### Test Classes

1. **TestExtractMetadata** (6 tests)
   - Successful extraction scenarios
   - Edge cases (no tags, multi-value tags)
   - Error handling

2. **TestRestoreMetadata** (6 tests)
   - Successful restoration scenarios
   - Edge cases (empty metadata, None metadata)
   - Error handling

3. **TestRepairFlacFile** (9 tests)
   - Full repair workflow
   - Each step failure scenario
   - Cleanup and backup operations

### Mocking Strategy

Tests use `unittest.mock` to:
- Mock FLAC file operations (Mutagen)
- Mock subprocess calls (flac command-line tool)
- Mock file system operations (shutil, os)
- Create temporary test files with `pytest.tmp_path` fixture

## Expected Test Output

```
============================= test session starts =============================
tests/unit/test_repair_functions.py::TestExtractMetadata::test_extract_metadata_success PASSED
tests/unit/test_repair_functions.py::TestExtractMetadata::test_extract_metadata_no_tags PASSED
tests/unit/test_repair_functions.py::TestExtractMetadata::test_extract_metadata_multi_value_tags PASSED
...
tests/unit/test_repair_functions.py::TestRepairFlacFile::test_repair_flac_file_success PASSED
tests/unit/test_repair_functions.py::TestRepairFlacFile::test_repair_flac_file_cleanup_wav PASSED

======================= 21 passed in 2.34s ========================
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running from the project root and have installed the package:

```bash
pip install -e .
```

### Scipy/Numpy Compatibility

If you encounter scipy import errors with Python 3.14+:

1. **Option 1** (Recommended): Use Python 3.8-3.12
   ```bash
   pyenv install 3.12
   pyenv local 3.12
   ```

2. **Option 2**: Wait for scipy to add Python 3.14+ support

### Missing Dependencies

```bash
# Install all dependencies including dev
pip install -e ".[dev]"

# Or install test requirements only
pip install pytest pytest-cov
```

## Adding New Tests

When adding new repair-related functionality:

1. Add test methods to appropriate test class
2. Use descriptive test names: `test_<function>_<scenario>`
3. Follow AAA pattern:
   - **Arrange**: Set up mocks and test data
   - **Act**: Call the function being tested
   - **Assert**: Verify expected behavior
4. Add docstrings explaining what's being tested
5. Update coverage goals if needed

## Integration Tests

For integration tests that use real FLAC files, see `tests/integration/`.

Unit tests here use mocking to avoid dependency on:
- Actual FLAC files
- flac command-line tool
- Mutagen library internals
- File system state

## Continuous Integration

These tests are designed to run in CI environments. Ensure:
- Python version matches 3.8-3.12
- All dependencies installed
- Sufficient permissions for tmp file creation
