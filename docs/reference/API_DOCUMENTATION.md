# API Documentation

## Overview

FLAC Detective provides a comprehensive Python API for analyzing FLAC files and detecting transcoding issues. This document explains how to use the API documentation and how to build it locally.

## Online Documentation

The full API documentation is available on Read the Docs:

**[https://flac-detective.readthedocs.io](https://flac-detective.readthedocs.io)**

## Building Documentation Locally

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e .[docs]
```

This will install:
- Sphinx (documentation generator)
- sphinx-rtd-theme (Read the Docs theme)
- sphinx-autodoc-typehints (type hints in documentation)
- myst-parser (Markdown support)

### Build HTML Documentation

Navigate to the `docs` directory and build:

```bash
cd docs
make html
```

On Windows, you can use:

```bash
cd docs
.\make.bat html
```

The generated documentation will be in `docs/_build/html/`. Open `index.html` in your browser.

### Other Output Formats

Sphinx supports multiple output formats:

```bash
make html      # HTML documentation (default)
make latex     # LaTeX files for PDF generation
make epub      # EPUB e-book format
make text      # Plain text format
make man       # Unix manual pages
```

### Clean Build

To clean previous builds:

```bash
make clean
```

## API Reference Structure

The API documentation is organized into the following sections:

### Core Module (`flac_detective`)

Main entry point with:
- `FLACAnalyzer`: Main analyzer class
- `ProgressTracker`: Progress tracking and result management
- Utility functions for file discovery

### Analysis Module (`flac_detective.analysis`)

Contains:
- `FLACAnalyzer.analyze_file()`: Main analysis method
- Spectral analysis functions
- Quality analysis (clipping, DC offset detection)
- Metadata validation
- Scoring system with 6 detection rules

### Repair Module (`flac_detective.repair`)

FLAC file repair functionality:
- `repair_flac()`: Automatic FLAC repair
- Metadata preservation
- Encoding utilities

### Reporting Module (`flac_detective.reporting`)

Report generation:
- `TextReporter`: Detailed text reports
- Statistics aggregation
- Summary generation

## Using the API in Code

### Basic Analysis

```python
from pathlib import Path
from flac_detective import FLACAnalyzer

# Create analyzer
analyzer = FLACAnalyzer(sample_duration=30.0)

# Analyze a file
result = analyzer.analyze_file(Path('song.flac'))

# Check result
print(f"Score: {result['score']}/100")
print(f"Verdict: {result['verdict']}")
print(f"Reason: {result['reason']}")

# Scores >= 80: FAKE (certain)
# Scores >= 50: SUSPICIOUS (probable fake)
# Scores >= 30: WARNING (doubtful)
# Scores < 30: AUTHENTIC (likely genuine)
```

### Batch Analysis with Progress Tracking

```python
from pathlib import Path
from flac_detective import FLACAnalyzer, ProgressTracker
from flac_detective.utils import find_flac_files

# Setup
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

analyzer = FLACAnalyzer()
tracker = ProgressTracker(progress_file=output_dir / 'progress.json')

# Find all FLAC files
music_dir = Path('/path/to/music')
flac_files = find_flac_files(music_dir)

# Analyze with resume capability
for flac_file in flac_files:
    if not tracker.is_processed(str(flac_file)):
        result = analyzer.analyze_file(flac_file)
        tracker.add_result(result)

        # Periodic save (every 10 files)
        if len(tracker.get_results()) % 10 == 0:
            tracker.save()

# Final save
tracker.save()

# Get all results
results = tracker.get_results()
suspicious = [r for r in results if r['score'] >= 50]
print(f"Found {len(suspicious)} suspicious files")
```

### Repairing FLAC Files

```python
from pathlib import Path
from flac_detective.repair import repair_flac

# Repair a corrupted FLAC file
input_file = Path('corrupted.flac')
output_file = Path('repaired.flac')

success, message = repair_flac(input_file, output_file)

if success:
    print(f"Successfully repaired: {message}")
else:
    print(f"Repair failed: {message}")
```

### Generating Reports

```python
from pathlib import Path
from flac_detective.reporting import TextReporter

# After analysis
results = tracker.get_results()

# Generate report
reporter = TextReporter()
report_file = Path('analysis_report.txt')
reporter.generate_report(
    results=results,
    output_file=report_file,
    scan_paths=[Path('/path/to/music')]
)

print(f"Report saved to {report_file}")
```

## Result Dictionary Structure

Each analysis returns a dictionary with the following keys:

```python
{
    'filepath': str,              # Absolute path to file
    'filename': str,              # File name only
    'score': int,                 # 0-100 (higher = more likely fake)
    'verdict': str,               # AUTHENTIC, WARNING, SUSPICIOUS, FAKE
    'confidence': str,            # CERTAIN, PROBABLE, etc.
    'reason': str,                # Human-readable explanation
    'cutoff_freq': int,           # Detected frequency cutoff (Hz)
    'sample_rate': int,           # Sample rate (Hz)
    'bit_depth': int,             # Bit depth (bits)
    'encoder': str,               # Encoder information
    'duration_metadata': float,   # Duration from metadata (s)
    'duration_real': float,       # Actual audio duration (s)
    'duration_mismatch': bool,    # Duration consistency check
    'has_clipping': bool,         # Clipping detected
    'clipping_severity': str,     # light, moderate, severe
    'has_dc_offset': bool,        # DC offset detected
    'dc_offset_severity': str,    # light, moderate, severe
    'is_corrupted': bool,         # File corruption detected
    'is_fake_high_res': bool,    # Fake high-resolution audio
    'is_upsampled': bool,         # Upsampled from lower sample rate
    'estimated_mp3_bitrate': int, # Estimated source MP3 bitrate
}
```

## Documentation Standards

All public functions and classes in FLAC Detective follow these docstring conventions:

1. **NumPy/Google Style**: Using Napoleon extension for parsing
2. **Type Hints**: All parameters and return types are annotated
3. **Examples**: Code examples in docstrings where appropriate
4. **Cross-References**: Links to related functions and modules

### Example Docstring Format

```python
def analyze_file(filepath: Path) -> Dict:
    """Analyzes a FLAC file for transcoding detection.

    Performs comprehensive spectral analysis, metadata validation,
    and quality checks to determine if a FLAC file is an authentic
    recording or a transcode from a lossy format (typically MP3).

    Parameters
    ----------
    filepath : Path
        Path to the FLAC file to analyze.

    Returns
    -------
    dict
        Analysis result dictionary containing score, verdict,
        and detailed findings.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If the file is not a valid FLAC file.

    Examples
    --------
    >>> from pathlib import Path
    >>> analyzer = FLACAnalyzer()
    >>> result = analyzer.analyze_file(Path('song.flac'))
    >>> print(result['score'])
    15

    See Also
    --------
    analyze_spectrum : Performs spectral analysis
    new_calculate_score : Calculates final score
    """
    # Implementation...
```

## Contributing to Documentation

When adding new features or modifying existing ones:

1. **Update docstrings** in the source code
2. **Add examples** where helpful
3. **Test the documentation build** locally
4. **Check for broken links** in generated docs

### Testing Documentation

```bash
# Build and check for warnings
cd docs
make clean
make html

# Check for broken links (requires sphinx-linkcheck)
make linkcheck
```

## Read the Docs Configuration

The project is configured for automatic documentation building on Read the Docs through `.readthedocs.yml`:

```yaml
version: 2

sphinx:
  configuration: docs/conf.py

build:
  os: ubuntu-22.04
  tools:
    python: "3.11"

python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - docs
```

Documentation is automatically rebuilt when changes are pushed to the repository.

## Additional Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Guide](https://docs.readthedocs.io/)
- [NumPy Docstring Guide](https://numpydoc.readthedocs.io/en/latest/format.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
