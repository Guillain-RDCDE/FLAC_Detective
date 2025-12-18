# 🎵 FLAC Detective

![FLAC Detective Banner](https://raw.githubusercontent.com/GuillainM/FLAC_Detective/main/assets/flac_detective_banner.png)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/flac-detective)](https://pypi.org/project/flac-detective/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-yellow)](https://github.com/GuillainM/FLAC_Detective)

**Advanced FLAC Authenticity Analyzer for Detecting MP3-to-FLAC Transcodes**

FLAC Detective is a professional-grade command-line tool that analyzes FLAC audio files to detect MP3-to-FLAC transcodes with high precision. Using advanced spectral analysis and an 11-rule scoring system, it helps you maintain an authentic lossless music collection.

---

## ✨ Key Features

- **🎯 High Precision Detection**: 11-rule scoring system with intelligent protection mechanisms
- **📊 4-Level Verdict System**: Clear confidence ratings from AUTHENTIC to FAKE_CERTAIN
- **⚡ Performance Optimized**: 80% faster than baseline through smart caching and parallel processing
- **🔍 Advanced Analysis**: Spectral analysis, compression artifact detection, and multi-segment validation
- **🛡️ Protection Layers**: Prevents false positives for vinyl rips, cassette transfers, and high-quality MP3s
- **📝 Flexible Output**: Console reports with Rich formatting, JSON export, and detailed logging
- **🔧 Graceful Error Handling**: Partial file reading for corrupted or problematic FLAC files

---

## 🚀 Quick Start

### Installation

```bash
pip install flac-detective
```

### Basic Usage

```bash
# Analyze current directory
flac-detective .

# Analyze specific directory
flac-detective /path/to/music

# Generate JSON report
flac-detective /path/to/music --format json

# Verbose output with detailed analysis
flac-detective /path/to/music --verbose
```

---

## 📖 How It Works

### Detection Rules

FLAC Detective uses **11 independent rules** with additive scoring (0-150 points):

| Rule | Description | Points |
|------|-------------|--------|
| **Rule 1** | MP3 Spectral Signature (CBR patterns) | +50 |
| **Rule 2** | Cutoff Frequency Analysis | +50 |
| **Rule 3** | Bitrate Inflation Detection | +50 |
| **Rule 4** | Suspicious 24-bit Detection | +30 |
| **Rule 5** | High Variance Protection (VBR) | -40 |
| **Rule 6** | High Quality Protection | -30 |
| **Rule 7** | Vinyl & Silence Analysis | -100 |
| **Rule 8** | Nyquist Exception | -50 |
| **Rule 9** | Compression Artifacts | +30 |
| **Rule 10** | Multi-Segment Consistency | Variable |
| **Rule 11** | Cassette Detection | -60 |

### Verdict System

Based on the total score, FLAC Detective assigns one of four verdicts:

```
Score ≤ 30   → ✅ AUTHENTIC      (High confidence - genuine lossless)
Score 31-60  → ⚡ WARNING        (Manual review recommended)
Score 61-85  → ⚠️  SUSPICIOUS    (Likely transcode)
Score ≥ 86   → ❌ FAKE_CERTAIN   (Definite transcode)
```

### Protection Mechanisms

The tool implements a multi-layer protection system to prevent false positives:

1. **Absolute Protection** (Rule 8): Protects files with cutoff near Nyquist frequency
2. **MP3 320k Protection** (Rule 1): Exception for high-quality MP3 320 kbps
3. **Analog Source Protection** (Rules 7, 11): Detects vinyl rips and cassette transfers
4. **Dynamic Protection** (Rule 10): Validates consistency across file segments

---

## 🆕 What's New in v0.7.0

### Partial File Reading
- Gracefully handles FLAC files with decoder errors
- Analyzes partial audio data when full decode fails
- Reduces false "CORRUPTED" verdicts

### Energy-Based Cutoff Detection
- **Critical Fix**: Bass-heavy music no longer misidentified as MP3
- Added 15 kHz minimum threshold to distinguish bass from MP3 artifacts
- **Impact**: 77% reduction in false positives

### Quality Improvements
- False positives: **198 → 46** (-77%)
- Authentic detection: **59 → 244** (+314%)
- Overall quality score: **20.2% → 83.6%**

---

## 💻 Usage Examples

### Command Line

```bash
# Basic analysis
flac-detective /path/to/music

# Save report to file
flac-detective /path/to/music --output report.txt

# JSON output for automation
flac-detective /path/to/music --format json > results.json

# Verbose mode with detailed rule execution
flac-detective /path/to/music --verbose
```

### Python API

```python
from flac_detective.analysis.new_scoring import new_calculate_score
from pathlib import Path

# Analyze a FLAC file
filepath = Path("/path/to/file.flac")
score, verdict, confidence, reasons = new_calculate_score(
    cutoff_freq=20500,
    metadata={"sample_rate": 44100, "bit_depth": 16, "channels": 2},
    duration_check={"duration": 180.5},
    filepath=filepath
)

print(f"Verdict: {verdict}")
print(f"Score: {score}/150")
print(f"Confidence: {confidence}")
print(f"Detection Reasons: {reasons}")
```

---

## 📦 Requirements

### Python Dependencies

- Python 3.8 or higher
- numpy >= 1.20.0
- scipy >= 1.7.0
- mutagen >= 1.45.0
- soundfile >= 0.10.0
- rich >= 13.0.0

### Optional System Dependencies

The `flac` command-line tool is recommended for advanced features:

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install flac
```

**macOS:**
```bash
brew install flac
```

**Windows:**
Download from [Xiph.org FLAC](https://xiph.org/flac/download.html)

---

## 🏗️ Development

### Installation from Source

```bash
# Clone the repository
git clone https://github.com/GuillainM/FLAC_Detective.git
cd FLAC_Detective

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=flac_detective --cov-report=html

# Run specific test file
pytest tests/test_new_scoring_rules.py -v
```

### Project Structure

```
src/flac_detective/
├── analysis/
│   ├── new_scoring/          # 11-rule scoring system
│   │   ├── rules/            # Individual rule implementations
│   │   ├── calculator.py     # Score orchestration
│   │   └── verdict.py        # Score interpretation
│   ├── spectrum.py           # Spectral analysis
│   └── audio_cache.py        # Optimized file reading
├── reporting/                # Report generation
└── main.py                   # CLI entry point
```

---

## 📚 Documentation

- [**Changelog**](CHANGELOG.md) - Version history and release notes
- [**Technical Documentation**](docs/TECHNICAL_DOCUMENTATION.md) - Architecture and algorithms
- [**Rule Specifications**](docs/RULE_SPECIFICATIONS.md) - Detailed rule documentation
- [**Performance Guide**](docs/PERFORMANCE_OPTIMIZATIONS.md) - Optimization strategies
- [**Project Structure**](PROJECT_STRUCTURE.md) - Codebase organization

---

## 🎯 Use Cases

### ✅ Ideal For

- **Library Maintenance**: Clean your music collection of fake lossless files
- **Quality Verification**: Validate FLAC authenticity before archiving
- **Batch Processing**: Analyze large music libraries efficiently
- **Format Validation**: Ensure genuine lossless quality for critical listening

### ⚠️ Limitations

- Only analyzes FLAC files (other lossless formats not supported)
- Designed for batch analysis, not real-time processing
- Detects transcodes, not subjective audio quality
- May require manual review for edge cases (WARNING verdicts)

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report Issues**: Found a bug? [Open an issue](https://github.com/GuillainM/FLAC_Detective/issues)
2. **Suggest Features**: Have an idea? Start a [discussion](https://github.com/GuillainM/FLAC_Detective/discussions)
3. **Submit PRs**: Fork the repo, create a feature branch, and submit a pull request
4. **Improve Docs**: Documentation improvements are always appreciated

### Development Workflow

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/FLAC_Detective.git
cd FLAC_Detective

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and test
pytest

# Format code
black src tests
isort src tests

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open Pull Request on GitHub
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Audio analysis community for MP3 compression research
- Contributors to NumPy, SciPy, and Soundfile libraries
- Beta testers and community feedback

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Discussions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
- **Documentation**: [Project Wiki](https://github.com/GuillainM/FLAC_Detective/wiki)

---

**FLAC Detective v0.7.0** - *Maintaining authentic lossless audio collections*
