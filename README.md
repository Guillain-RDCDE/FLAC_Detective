# 🎵 FLAC Detective

**Advanced FLAC Authenticity Analyzer & Repair Tool**

> "Every FLAC file tells a story... I find the truth."

FLAC Detective is a professional tool for analyzing the authenticity of your FLAC files. It detects "Fake FLAC" files (transcoded MP3s) by analyzing their frequency spectrum and verifies metadata integrity and duration.

## ✨ Features

- **🕵️ Advanced 6-Rule Detection System**: 
  - Bitrate constant MP3 detection (320, 256, 192 kbps, etc.)
  - Frequency cutoff analysis based on sample rate
  - Real vs apparent bitrate comparison
  - 24-bit file validation
  - Bitrate variance analysis to avoid false positives
  - Bitrate coherence verification
- **📊 4-Level Verdict System**: 
  - FAKE_CERTAIN (score ≥ 80/100): Delete immediately
  - FAKE_PROBABLE (score 50-79): Mark as suspicious
  - DOUTEUX (score 30-49): Manual verification needed
  - AUTHENTIQUE (score < 30): Keep file
- **🔧 Automatic Repair**: Fixes duration issues (metadata consistency) by re-encoding without metadata loss.
- **📑 Detailed Reports**: Generates detailed text reports with statistics and verdict breakdown.
- **🚀 Performance**: Multi-threaded analysis to quickly process large libraries.

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Python libraries (installed automatically via pip)

### Installation (Development)

```bash
# Clone the repo
git clone https://github.com/your-repo/flac-detective.git
cd flac-detective

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For tests and linting
```

## 🚀 Usage

### Analyzer (Scanner)

```bash
# Analyze the current folder
python -m flac_detective.main

# The text report will be generated in the same folder.
```

### Repair Tool (Fixer)

```bash
# Repair a specific file
python -m flac_detective.repair "path/to/file.flac"

# Repair an entire folder recursively
python -m flac_detective.repair "path/to/folder" --recursive

# Simulation (dry-run, no modification)
python -m flac_detective.repair "path/to/file.flac" --dry-run
```

## 🏗️ Code Architecture

The project follows a modern modular architecture:

- `src/flac_detective/analysis/`: Spectral analysis and scoring engine.
- `src/flac_detective/repair/`: Repair and re-encoding module.
- `src/flac_detective/reporting/`: Text report generation.
- `src/flac_detective/tracker.py`: Resume capability management.

## 🧪 Quality and Tests

The project respects Python quality standards:
- **Formatting**: Black & Isort
- **Linting**: Flake8 (0 errors)
- **Typing**: Mypy (Strict)
- **Tests**: Pytest (Full coverage)

To run tests:
```bash
pytest tests -v
```

## 📝 License

MIT License.
