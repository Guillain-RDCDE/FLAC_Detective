# FLAC Detective Python API Guide

This guide shows how to use FLAC Detective as a Python library in your own projects.

## Installation

```bash
pip install flac-detective
```

## Quick Start

### Basic Analysis

Analyze a single FLAC file:

```python
from flac_detective import FLACAnalyzer
from pathlib import Path

# Create analyzer instance
analyzer = FLACAnalyzer(sample_duration=30.0)

# Analyze a file
result = analyzer.analyze_file(Path('song.flac'))

# Check the result
print(f"File: {result['filename']}")
print(f"Score: {result['score']}/100")
print(f"Verdict: {result['verdict']}")
print(f"Reason: {result['reason']}")
```

### Understanding Results

Each analysis returns a dictionary with comprehensive information:

```python
result = {
    'filepath': str,              # Full path to file
    'filename': str,              # File name only
    'score': int,                 # 0-100 (higher = more likely fake)
    'verdict': str,               # AUTHENTIC, WARNING, SUSPICIOUS, FAKE
    'confidence': str,            # Confidence level
    'reason': str,                # Human-readable explanation

    # Technical details
    'cutoff_freq': int,           # Frequency cutoff in Hz
    'sample_rate': int,           # Sample rate (44100, 48000, etc.)
    'bit_depth': int,             # Bit depth (16, 24, etc.)
    'encoder': str,               # Encoder information

    # Quality checks
    'has_clipping': bool,         # Audio clipping detected
    'clipping_severity': str,     # light, moderate, severe
    'has_dc_offset': bool,        # DC offset detected
    'dc_offset_severity': str,    # light, moderate, severe

    # File integrity
    'is_corrupted': bool,         # File corruption detected
    'corruption_error': str,      # Error message if corrupted

    # Detection details
    'is_fake_high_res': bool,     # Fake high-resolution
    'is_upsampled': bool,         # Upsampled audio
    'estimated_mp3_bitrate': int, # Estimated source bitrate
}
```

### Score Interpretation

```python
def interpret_score(score):
    """Interpret FLAC Detective score."""
    if score >= 80:
        return "FAKE - Almost certainly a transcode"
    elif score >= 50:
        return "SUSPICIOUS - Likely a transcode"
    elif score >= 30:
        return "WARNING - Doubtful, needs review"
    else:
        return "AUTHENTIC - Likely genuine lossless"

result = analyzer.analyze_file(Path('song.flac'))
print(interpret_score(result['score']))
```

## Batch Analysis

### Analyzing Multiple Files

```python
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

# Setup
analyzer = FLACAnalyzer()
music_dir = Path('/path/to/music')

# Find all FLAC files
flac_files = find_flac_files(music_dir)
print(f"Found {len(flac_files)} FLAC files")

# Analyze each file
results = []
for flac_file in flac_files:
    result = analyzer.analyze_file(flac_file)
    results.append(result)

    # Print progress
    print(f"[{len(results)}/{len(flac_files)}] {result['filename']}: {result['score']}/100")

# Filter suspicious files
suspicious = [r for r in results if r['score'] >= 50]
print(f"\nFound {len(suspicious)} suspicious files")
```

### Progress Tracking with Resume

```python
from flac_detective import FLACAnalyzer, ProgressTracker
from pathlib import Path

# Create tracker with progress file
output_dir = Path('results')
output_dir.mkdir(exist_ok=True)

tracker = ProgressTracker(progress_file=output_dir / 'progress.json')
analyzer = FLACAnalyzer()

# Find files
from flac_detective.utils import find_flac_files
flac_files = find_flac_files(Path('/path/to/music'))

# Set total for progress tracking
tracker.set_total(len(flac_files))

# Analyze with automatic resume
for flac_file in flac_files:
    # Skip if already processed
    if not tracker.is_processed(str(flac_file)):
        result = analyzer.analyze_file(flac_file)
        tracker.add_result(result)

        # Save progress every 10 files
        if len(tracker.get_results()) % 10 == 0:
            tracker.save()
            print(f"Progress saved: {tracker.get_progress()}")

# Final save
tracker.save()

# Get all results
all_results = tracker.get_results()
print(f"Analysis complete: {len(all_results)} files")

# Clean up progress file when done
tracker.cleanup()
```

## Advanced Usage

### Custom Analysis Parameters

```python
from flac_detective import FLACAnalyzer

# Analyze longer sample (more accurate but slower)
analyzer = FLACAnalyzer(sample_duration=60.0)

# Analyze shorter sample (faster but less accurate)
analyzer = FLACAnalyzer(sample_duration=15.0)

# Default is 30.0 seconds (good balance)
analyzer = FLACAnalyzer()  # sample_duration=30.0
```

### Filtering Results

```python
# Find all fake files (score >= 80)
fake_files = [r for r in results if r['score'] >= 80]

# Find all suspicious files (score >= 50)
suspicious_files = [r for r in results if r['score'] >= 50]

# Find files with specific issues
upsampled = [r for r in results if r['is_upsampled']]
fake_hi_res = [r for r in results if r['is_fake_high_res']]
corrupted = [r for r in results if r['is_corrupted']]
clipping = [r for r in results if r['has_clipping']]

# Find authentic files
authentic = [r for r in results if r['score'] < 30]
```

### Generating Reports

```python
from flac_detective.reporting import TextReporter
from pathlib import Path

# Create reporter
reporter = TextReporter()

# Generate report
report_file = Path('analysis_report.txt')
reporter.generate_report(
    results=all_results,
    output_file=report_file,
    scan_paths=[Path('/path/to/music')]
)

print(f"Report saved to {report_file}")
```

### Working with Statistics

```python
from flac_detective.reporting.statistics import calculate_statistics

# Calculate statistics from results
stats = calculate_statistics(results)

print(f"Total files: {stats['total_files']}")
print(f"Fake files: {stats['fake_count']}")
print(f"Suspicious files: {stats['suspicious_count']}")
print(f"Authentic files: {stats['authentic_count']}")
print(f"Average score: {stats['average_score']:.1f}")
```

## Repairing FLAC Files

### Automatic Repair

```python
from flac_detective.repair import repair_flac
from pathlib import Path

# Repair a corrupted FLAC file
input_file = Path('corrupted.flac')
output_file = Path('repaired.flac')

success, message = repair_flac(input_file, output_file)

if success:
    print(f"✅ Repair successful: {message}")
    # Original file is backed up as .corrupted.bak
else:
    print(f"❌ Repair failed: {message}")
```

### Batch Repair

```python
from flac_detective.repair import repair_flac
from pathlib import Path

# Find corrupted files from analysis
corrupted_files = [r for r in results if r['is_corrupted']]

for result in corrupted_files:
    filepath = Path(result['filepath'])
    output_file = filepath.parent / f"{filepath.stem}_repaired.flac"

    print(f"Repairing {filepath.name}...")
    success, message = repair_flac(filepath, output_file)

    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
```

## Integration Examples

### With Pandas for Data Analysis

```python
import pandas as pd
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

# Analyze files
analyzer = FLACAnalyzer()
flac_files = find_flac_files(Path('/path/to/music'))
results = [analyzer.analyze_file(f) for f in flac_files]

# Create DataFrame
df = pd.DataFrame(results)

# Analysis
print(df['verdict'].value_counts())
print(df.groupby('verdict')['score'].mean())
print(df[df['score'] >= 50][['filename', 'score', 'reason']])

# Export to CSV
df.to_csv('analysis_results.csv', index=False)
```

### With tqdm for Progress Bar

```python
from tqdm import tqdm
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

analyzer = FLACAnalyzer()
flac_files = find_flac_files(Path('/path/to/music'))

results = []
for flac_file in tqdm(flac_files, desc="Analyzing FLAC files"):
    result = analyzer.analyze_file(flac_file)
    results.append(result)
```

### With concurrent.futures for Parallel Processing

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from flac_detective import FLACAnalyzer
from flac_detective.utils import find_flac_files
from pathlib import Path

def analyze_file(filepath):
    """Analyze a single file."""
    analyzer = FLACAnalyzer()
    return analyzer.analyze_file(filepath)

# Find files
flac_files = find_flac_files(Path('/path/to/music'))

# Parallel analysis (4 workers)
results = []
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(analyze_file, f): f for f in flac_files}

    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        print(f"Processed: {result['filename']}")

print(f"Complete: {len(results)} files analyzed")
```

## Error Handling

### Handling Analysis Errors

```python
from flac_detective import FLACAnalyzer
from pathlib import Path

analyzer = FLACAnalyzer()

try:
    result = analyzer.analyze_file(Path('song.flac'))

    # Check for corruption
    if result['is_corrupted']:
        print(f"File is corrupted: {result['corruption_error']}")
        # Attempt repair...
    else:
        print(f"Analysis successful: {result['verdict']}")

except FileNotFoundError:
    print("File not found")
except Exception as e:
    print(f"Analysis failed: {e}")
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
results = [safe_analyze(f, analyzer) for f in flac_files]
errors = [r for r in results if r['verdict'] == 'ERROR']
print(f"Errors: {len(errors)}")
```

## Best Practices

### 1. Memory Management for Large Batches

```python
# Process in chunks to avoid memory issues
chunk_size = 100
for i in range(0, len(flac_files), chunk_size):
    chunk = flac_files[i:i+chunk_size]
    chunk_results = [analyzer.analyze_file(f) for f in chunk]
    # Process chunk_results...
    # Save to disk, append to database, etc.
```

### 2. Always Save Progress

```python
# Use ProgressTracker for long-running analyses
tracker = ProgressTracker(progress_file=Path('progress.json'))

try:
    for flac_file in flac_files:
        if not tracker.is_processed(str(flac_file)):
            result = analyzer.analyze_file(flac_file)
            tracker.add_result(result)
            tracker.save()  # Save after each file
finally:
    tracker.save()  # Ensure final save
```

### 3. Validate File Paths

```python
from pathlib import Path

def get_valid_files(path):
    """Get valid FLAC files from path."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() != '.flac':
            raise ValueError(f"Not a FLAC file: {path}")
        return [path]

    flac_files = list(path.rglob('*.flac'))
    if not flac_files:
        raise ValueError(f"No FLAC files found in: {path}")

    return flac_files
```

## Full Example: Complete Analysis Pipeline

```python
#!/usr/bin/env python3
"""Complete FLAC analysis pipeline."""

from flac_detective import FLACAnalyzer, ProgressTracker
from flac_detective.utils import find_flac_files
from flac_detective.reporting import TextReporter
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
    print(f"Found {len(flac_files)} FLAC files")

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

                # Periodic save
                if processed % 10 == 0:
                    tracker.save()

            except Exception as e:
                print(f"Error analyzing {flac_file}: {e}")

    # Save final results
    tracker.save()
    results = tracker.get_results()

    # Generate report
    report_file = output_dir / 'analysis_report.txt'
    reporter = TextReporter()
    reporter.generate_report(results, report_file, scan_paths=[music_dir])

    # Summary
    suspicious = [r for r in results if r['score'] >= 50]
    fake = [r for r in results if r['score'] >= 80]

    print(f"\n{'='*60}")
    print(f"Analysis Complete")
    print(f"{'='*60}")
    print(f"Total files: {len(results)}")
    print(f"Suspicious files: {len(suspicious)}")
    print(f"Fake files (certain): {len(fake)}")
    print(f"Report saved to: {report_file}")
    print(f"{'='*60}")

    # Cleanup
    tracker.cleanup()

if __name__ == '__main__':
    main()
```

## Additional Resources

- **Full API Reference**: https://flac-detective.readthedocs.io/en/latest/api/
- **Examples**: https://flac-detective.readthedocs.io/en/latest/EXAMPLES.html
- **Troubleshooting**: https://flac-detective.readthedocs.io/en/latest/TROUBLESHOOTING.html

---

**Happy analyzing! 🎵**
