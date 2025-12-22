# FLAC Detective Examples

This directory contains practical examples demonstrating how to use FLAC Detective in various scenarios.

## Quick Start

All examples are self-contained Python scripts that you can run directly:

```bash
# Make sure FLAC Detective is installed
pip install flac-detective

# Run any example
python basic_usage.py
```

## Available Examples

### 1. [basic_usage.py](basic_usage.py)
**Start here!** Simple examples for beginners.

- Analyze a single FLAC file
- Analyze a directory of files
- Interpret verdicts (AUTHENTIC, WARNING, SUSPICIOUS, FAKE_CERTAIN)

**Use when**: You're new to FLAC Detective and want to get started quickly.

```bash
python basic_usage.py
```

---

### 2. [batch_processing.py](batch_processing.py)
Analyze multiple directories and generate statistics.

- Process multiple directories in one run
- Generate comprehensive statistics (authentic %, fake %, etc.)
- Identify problematic files across entire collection
- Export results to JSON

**Use when**: You have a large music collection organized in multiple folders.

```bash
python batch_processing.py
```

**Example output**:
```
Statistics for Artist_Name
======================================================================
Total files analyzed: 245
  ✅ Authentic:      215 (87.8%)
  ⚡ Warning:         18 ( 7.3%)
  ⚠️  Suspicious:      9 ( 3.7%)
  ❌ Fake Certain:     3 ( 1.2%)
```

---

### 3. [json_export.py](json_export.py)
Export results to JSON and parse for custom reporting.

- Export analysis results to JSON format
- Parse JSON for custom reports
- Filter files by verdict or score
- Generate lists of files to delete or review
- Integration-ready format

**Use when**: You need to integrate FLAC Detective with other tools or scripts.

```bash
python json_export.py
```

**JSON format**:
```json
{
  "scan_info": {
    "timestamp": "2025-12-22T10:30:00",
    "directory": "/path/to/music",
    "total_files": 245
  },
  "files": [
    {
      "filepath": "/path/to/file.flac",
      "verdict": "AUTHENTIC",
      "score": 12,
      "reason": "Full spectrum preserved"
    }
  ]
}
```

---

### 4. [api_integration.py](api_integration.py)
Advanced API usage and integration patterns.

- Custom analyzer configuration (sample duration, etc.)
- Error handling best practices
- Filtering and sorting results
- External system integration (webhooks, notifications)
- Parallel processing concepts

**Use when**: You're building applications or workflows that integrate FLAC Detective.

```bash
python api_integration.py
```

**Features demonstrated**:
- ✅ Custom configuration
- ✅ Robust error handling
- ✅ Result filtering/sorting
- ✅ Webhook simulation
- ✅ Parallel processing hints

---

## Before Running Examples

### Update File Paths

All examples use placeholder paths. Before running, edit the scripts and update:

```python
# Change this:
directory = Path("path/to/your/music")

# To your actual path:
directory = Path("/Users/yourname/Music/FLAC")  # macOS/Linux
directory = Path("C:/Users/yourname/Music/FLAC")  # Windows
```

### Verify Installation

```bash
# Check that FLAC Detective is installed
python -c "import flac_detective; print(flac_detective.__version__)"

# Should output version number (e.g., 0.9.6)
```

## Common Use Cases

### Scenario 1: "I just want to check if my files are authentic"
→ Use **[basic_usage.py](basic_usage.py)**

### Scenario 2: "I need to clean my entire music library"
→ Use **[batch_processing.py](batch_processing.py)**

### Scenario 3: "I want to export results for further analysis"
→ Use **[json_export.py](json_export.py)**

### Scenario 4: "I'm building an app that uses FLAC Detective"
→ Use **[api_integration.py](api_integration.py)**

## Tips

### Performance Optimization

```python
# Faster analysis (15 seconds per file)
analyzer = FLACAnalyzer(sample_duration=15.0)

# More accurate analysis (60 seconds per file)
analyzer = FLACAnalyzer(sample_duration=60.0)

# Default: 30 seconds (balanced)
analyzer = FLACAnalyzer()
```

### Error Handling

Always wrap analysis in try-except blocks for production code:

```python
try:
    result = analyzer.analyze_file(file_path)
    if result.get('error'):
        print(f"Analysis error: {result['error']}")
    else:
        print(f"Success: {result['verdict']}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Filtering Results

```python
# Get only fake files
fake_files = [r for r in results if r['verdict'] == 'FAKE_CERTAIN']

# Get files with score above threshold
suspicious = [r for r in results if r['score'] >= 70]

# Get authentic files
authentic = [r for r in results if r['verdict'] == 'AUTHENTIC']
```

## Need More Help?

- **Documentation**: See [docs/](../docs/) directory
- **User Guide**: [docs/user-guide.md](../docs/user-guide.md)
- **API Reference**: [docs/api-reference.md](../docs/api-reference.md)
- **Issues**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Discussions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)

## Contributing

Found a bug in an example or have an idea for a new one?

1. Open an issue describing the problem or suggestion
2. Submit a pull request with your improvements
3. See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for guidelines

---

**Happy analyzing!** 🎵
