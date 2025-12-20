# API Reference

Complete guide to using FLAC Detective as a Python library.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core API](#core-api)
- [Batch Analysis](#batch-analysis)
- [Result Objects](#result-objects)
- [Advanced Usage](#advanced-usage)
- [Integration Examples](#integration-examples)
- [Error Handling](#error-handling)

## Installation

```bash
pip install flac-detective
```

## Quick Start

### Analyze a Single File

```python
from flac_detective import FLACAnalyzer
from pathlib import Path

# Create analyzer
analyzer = FLACAnalyzer()

# Analyze a file
result = analyzer.analyze_file(Path('song.flac'))

# Check verdict
print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}/100")
print(f"Reason: {result['reason']}")
```

### Analyze Multiple Files

```python
from flac_detective import FLACAnalyzer
from pathlib import Path

analyzer = FLACAnalyzer()
music_dir = Path('/path/to/music')

# Find all FLAC files
flac_files = list(music_dir.rglob('*.flac'))

# Analyze each
results = []
for flac_file in flac_files:
    result = analyzer.analyze_file(flac_file)
    results.append(result)
    print(f"{result['filename']}: {result['verdict']}")

# Filter suspicious files
suspicious = [r for r in results if r['score'] >= 61]
print(f"Found {len(suspicious)} suspicious files")
```

## Core API

### FLACAnalyzer

Main analysis class.

#### Constructor

```python
FLACAnalyzer(sample_duration: float = 30.0)
```

**Parameters**:
- `sample_duration` (float): Seconds of audio to analyze (default: 30.0)
  - Lower values = faster but less accurate
  - Higher values = slower but more accurate
  - Recommended: 15-60 seconds

**Example**:
```python
# Fast analysis (15 seconds)
analyzer = FLACAnalyzer(sample_duration=15.0)

# Standard analysis (30 seconds) - default
analyzer = FLACAnalyzer()

# Thorough analysis (60 seconds)
analyzer = FLACAnalyzer(sample_duration=60.0)
```

#### Methods

##### analyze_file()

```python
analyze_file(filepath: Path) -> dict
```

Analyzes a single FLAC file.

**Parameters**:
- `filepath` (Path): Path to FLAC file

**Returns**: Dictionary with analysis results (see [Result Objects](#result-objects))

**Example**:
```python
from pathlib import Path

result = analyzer.analyze_file(Path('song.flac'))
```

**Raises**:
- `FileNotFoundError`: File doesn't exist
- `ValueError`: Not a valid FLAC file
- `RuntimeError`: Analysis failed

## Batch Analysis

### Using find_flac_files()

```python
from flac_detective.utils import find_flac_files
from pathlib import Path

# Find all FLAC files recursively
flac_files = find_flac_files(Path('/music'))

# Returns list of Path objects
print(f"Found {len(flac_files)} files")
```

### Progress Tracking with ProgressTracker

```python
from flac_detective import FLACAnalyzer, ProgressTracker
from flac_detective.utils import find_flac_files
from pathlib import Path

# Setup
analyzer = FLACAnalyzer()
tracker = ProgressTracker(progress_file=Path('progress.json'))

# Find files
flac_files = find_flac_files(Path('/music'))
tracker.set_total(len(flac_files))

# Analyze with resume capability
for flac_file in flac_files:
    if not tracker.is_processed(str(flac_file)):
        result = analyzer.analyze_file(flac_file)
        tracker.add_result(result)

        # Save every 10 files
        if len(tracker.get_results()) % 10 == 0:
            tracker.save()

# Final save
tracker.save()

# Get results
results = tracker.get_results()
processed, total = tracker.get_progress()
print(f"Processed {processed}/{total} files")

# Cleanup when done
tracker.cleanup()
```

### Parallel Processing

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

def analyze_file(filepath):
    """Worker function for parallel processing."""
    analyzer = FLACAnalyzer()
    return analyzer.analyze_file(filepath)

# Find files
flac_files = find_flac_files(Path('/music'))

# Parallel analysis with 4 workers
results = []
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(analyze_file, f): f for f in flac_files}

    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        print(f"Processed: {result['filename']}")

print(f"Complete: {len(results)} files analyzed")
```

## Result Objects

### Analysis Result Dictionary

Each `analyze_file()` call returns a dictionary:

```python
{
    # File information
    'filepath': str,              # Full path: "/music/song.flac"
    'filename': str,              # Name only: "song.flac"

    # Verdict
    'score': int,                 # 0-150 (higher = more likely fake)
    'verdict': str,               # "AUTHENTIC" | "WARNING" | "SUSPICIOUS" | "FAKE_CERTAIN"
    'confidence': str,            # Confidence level description
    'reason': str,                # Human-readable explanation

    # Audio metadata
    'cutoff_freq': int,           # Frequency cutoff in Hz (e.g., 22050)
    'sample_rate': int,           # Sample rate (e.g., 44100, 48000)
    'bit_depth': int,             # Bit depth (16, 24, etc.)
    'channels': int,              # Number of channels (1, 2)
    'duration': float,            # Duration in seconds
    'encoder': str,               # Encoder info from metadata

    # Quality indicators
    'has_clipping': bool,         # Audio clipping detected
    'clipping_severity': str,     # "light" | "moderate" | "severe"
    'has_dc_offset': bool,        # DC offset detected
    'dc_offset_severity': str,    # "light" | "moderate" | "severe"

    # Corruption detection
    'is_corrupted': bool,         # File integrity issues
    'corruption_error': str,      # Error message if corrupted

    # Transcode detection
    'is_fake_high_res': bool,     # Fake high-resolution file
    'is_upsampled': bool,         # Upsampled from lower quality
    'estimated_mp3_bitrate': int, # Estimated source bitrate (0 if unknown)

    # Rule details (verbose mode)
    'rule_scores': dict,          # Individual rule contributions
}
```

### Verdict Values

```python
# Possible verdict values
VERDICTS = [
    "AUTHENTIC",      # Score ≤ 30
    "WARNING",        # Score 31-60
    "SUSPICIOUS",     # Score 61-85
    "FAKE_CERTAIN",   # Score ≥ 86
]
```

### Working with Results

```python
result = analyzer.analyze_file(Path('song.flac'))

# Check verdict
if result['verdict'] == 'AUTHENTIC':
    print("File is genuine!")
elif result['verdict'] in ['SUSPICIOUS', 'FAKE_CERTAIN']:
    print(f"Likely fake: {result['reason']}")

# Check score threshold
if result['score'] >= 80:
    print("High confidence fake")

# Check specific indicators
if result['is_upsampled']:
    print(f"Upsampled from {result['estimated_mp3_bitrate']} kbps")

# Access metadata
print(f"Sample rate: {result['sample_rate']} Hz")
print(f"Bit depth: {result['bit_depth']} bit")
```

## Advanced Usage

### Custom Filtering

```python
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

analyzer = FLACAnalyzer()
results = [analyzer.analyze_file(f) for f in find_flac_files(Path('/music'))]

# Find all fake files (score >= 80)
fakes = [r for r in results if r['score'] >= 80]

# Find upsampled files
upsampled = [r for r in results if r['is_upsampled']]

# Find 24-bit suspicious files
suspicious_24bit = [
    r for r in results
    if r['bit_depth'] == 24 and r['score'] >= 50
]

# Find corrupted files
corrupted = [r for r in results if r['is_corrupted']]

# Find authentic high-quality files
authentic_hq = [
    r for r in results
    if r['verdict'] == 'AUTHENTIC' and r['sample_rate'] >= 48000
]
```

### Statistics Calculation

```python
from flac_detective.reporting.statistics import calculate_statistics

# Analyze files
results = [analyzer.analyze_file(f) for f in flac_files]

# Calculate statistics
stats = calculate_statistics(results)

print(f"Total files: {stats['total_files']}")
print(f"Authentic: {stats['authentic_count']} ({stats['authentic_percentage']:.1f}%)")
print(f"Suspicious: {stats['suspicious_count']} ({stats['suspicious_percentage']:.1f}%)")
print(f"Fake: {stats['fake_count']} ({stats['fake_percentage']:.1f}%)")
print(f"Average score: {stats['average_score']:.1f}")
```

### Report Generation

```python
from flac_detective.reporting import TextReporter
from pathlib import Path

# Analyze files
analyzer = FLACAnalyzer()
results = [analyzer.analyze_file(f) for f in flac_files]

# Generate report
reporter = TextReporter()
report_file = Path('analysis_report.txt')

reporter.generate_report(
    results=results,
    output_file=report_file,
    scan_paths=[Path('/music')]
)

print(f"Report saved to {report_file}")
```

### FLAC Repair

```python
from flac_detective.repair import repair_flac
from pathlib import Path

# Repair a corrupted file
input_file = Path('corrupted.flac')
output_file = Path('repaired.flac')

success, message = repair_flac(input_file, output_file)

if success:
    print(f"✅ Repair successful: {message}")
else:
    print(f"❌ Repair failed: {message}")

# Batch repair
corrupted_files = [r for r in results if r['is_corrupted']]

for result in corrupted_files:
    filepath = Path(result['filepath'])
    output = filepath.parent / f"{filepath.stem}_repaired.flac"

    success, msg = repair_flac(filepath, output)
    print(f"{filepath.name}: {msg}")
```

## Integration Examples

### With Pandas

```python
import pandas as pd
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

# Analyze
analyzer = FLACAnalyzer()
flac_files = find_flac_files(Path('/music'))
results = [analyzer.analyze_file(f) for f in flac_files]

# Create DataFrame
df = pd.DataFrame(results)

# Analysis
print(df['verdict'].value_counts())
print(df.groupby('verdict')['score'].mean())

# Filter and sort
suspicious = df[df['score'] >= 61].sort_values('score', ascending=False)
print(suspicious[['filename', 'score', 'verdict', 'reason']])

# Export
df.to_csv('analysis.csv', index=False)
suspicious.to_csv('suspicious.csv', index=False)
```

### With tqdm Progress Bar

```python
from tqdm import tqdm
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

analyzer = FLACAnalyzer()
flac_files = find_flac_files(Path('/music'))

results = []
for flac_file in tqdm(flac_files, desc="Analyzing FLAC files"):
    result = analyzer.analyze_file(flac_file)
    results.append(result)
```

### Database Integration (SQLite)

```python
import sqlite3
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

# Create database
conn = sqlite3.connect('flac_analysis.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis (
        filepath TEXT PRIMARY KEY,
        filename TEXT,
        score INTEGER,
        verdict TEXT,
        sample_rate INTEGER,
        bit_depth INTEGER,
        is_upsampled BOOLEAN,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Analyze and store
analyzer = FLACAnalyzer()
flac_files = find_flac_files(Path('/music'))

for flac_file in flac_files:
    result = analyzer.analyze_file(flac_file)

    cursor.execute('''
        INSERT OR REPLACE INTO analysis
        (filepath, filename, score, verdict, sample_rate, bit_depth, is_upsampled)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        result['filepath'],
        result['filename'],
        result['score'],
        result['verdict'],
        result['sample_rate'],
        result['bit_depth'],
        result['is_upsampled']
    ))

conn.commit()
conn.close()

# Query later
conn = sqlite3.connect('flac_analysis.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM analysis WHERE verdict = 'FAKE_CERTAIN'")
fakes = cursor.fetchall()
print(f"Found {len(fakes)} certain fakes")
```

### Web API (Flask Example)

```python
from flask import Flask, request, jsonify
from flac_detective import FLACAnalyzer
from pathlib import Path
import tempfile

app = Flask(__name__)
analyzer = FLACAnalyzer()

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze uploaded FLAC file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Save temporarily
    with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        # Analyze
        result = analyzer.analyze_file(tmp_path)
        return jsonify(result)
    finally:
        # Cleanup
        tmp_path.unlink()

if __name__ == '__main__':
    app.run(debug=True)
```

## Error Handling

### Basic Error Handling

```python
from flac_detective import FLACAnalyzer
from pathlib import Path

analyzer = FLACAnalyzer()

try:
    result = analyzer.analyze_file(Path('song.flac'))
    print(f"Score: {result['score']}")

except FileNotFoundError:
    print("File not found")

except ValueError as e:
    print(f"Invalid file: {e}")

except RuntimeError as e:
    print(f"Analysis failed: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

### Graceful Degradation

```python
def safe_analyze(filepath, analyzer):
    """Analyze with error handling."""
    try:
        return analyzer.analyze_file(filepath)
    except Exception as e:
        return {
            'filepath': str(filepath),
            'filename': filepath.name,
            'score': 0,
            'verdict': 'ERROR',
            'reason': f'Analysis failed: {str(e)}',
            'error': str(e)
        }

# Use in batch processing
analyzer = FLACAnalyzer()
results = [safe_analyze(f, analyzer) for f in flac_files]

# Check for errors
errors = [r for r in results if r['verdict'] == 'ERROR']
print(f"Errors: {len(errors)}")
```

### Corrupted File Handling

```python
result = analyzer.analyze_file(Path('song.flac'))

if result['is_corrupted']:
    print(f"File is corrupted: {result['corruption_error']}")

    # Attempt repair
    from flac_detective.repair import repair_flac

    success, message = repair_flac(
        Path(result['filepath']),
        Path('repaired.flac')
    )

    if success:
        # Re-analyze repaired file
        new_result = analyzer.analyze_file(Path('repaired.flac'))
        print(f"Repaired file score: {new_result['score']}")
```

## Complete Example

Full pipeline with all features:

```python
#!/usr/bin/env python3
"""Complete FLAC analysis pipeline with all features."""

from flac_detective import FLACAnalyzer, ProgressTracker
from flac_detective.utils import find_flac_files
from flac_detective.reporting import TextReporter
from flac_detective.reporting.statistics import calculate_statistics
from pathlib import Path
import sys

def main():
    # Configuration
    music_dir = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    output_dir = Path('flac_analysis')
    output_dir.mkdir(exist_ok=True)

    # Initialize
    analyzer = FLACAnalyzer(sample_duration=30.0)
    tracker = ProgressTracker(progress_file=output_dir / 'progress.json')

    # Find files
    print(f"Scanning {music_dir}...")
    flac_files = find_flac_files(music_dir)
    print(f"Found {len(flac_files)} FLAC files\n")

    # Analyze
    tracker.set_total(len(flac_files))

    for flac_file in flac_files:
        if not tracker.is_processed(str(flac_file)):
            try:
                result = analyzer.analyze_file(flac_file)
                tracker.add_result(result)

                # Progress
                processed, total = tracker.get_progress()
                print(f"[{processed}/{total}] {result['filename']}: "
                      f"{result['score']}/100 ({result['verdict']})")

                # Save periodically
                if processed % 10 == 0:
                    tracker.save()

            except Exception as e:
                print(f"Error analyzing {flac_file}: {e}")

    # Save results
    tracker.save()
    results = tracker.get_results()

    # Generate report
    report_file = output_dir / 'analysis_report.txt'
    reporter = TextReporter()
    reporter.generate_report(results, report_file, scan_paths=[music_dir])

    # Statistics
    stats = calculate_statistics(results)

    # Summary
    print(f"\n{'='*60}")
    print("Analysis Complete")
    print(f"{'='*60}")
    print(f"Total files: {stats['total_files']}")
    print(f"Authentic: {stats['authentic_count']} ({stats['authentic_percentage']:.1f}%)")
    print(f"Suspicious: {stats['suspicious_count']} ({stats['suspicious_percentage']:.1f}%)")
    print(f"Fake (certain): {stats['fake_count']} ({stats['fake_percentage']:.1f}%)")
    print(f"Average score: {stats['average_score']:.1f}")
    print(f"\nReport saved to: {report_file}")
    print(f"{'='*60}\n")

    # Cleanup
    tracker.cleanup()

if __name__ == '__main__':
    main()
```

## Next Steps

- **User guide**: [User Guide](user-guide.md)
- **Technical details**: [Technical Details](technical-details.md)
- **Contributing**: [Contributing](contributing.md)

---

For questions or issues, visit [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions).
