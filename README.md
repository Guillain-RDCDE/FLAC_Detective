# 🎵 FLAC Detective

**Advanced FLAC Authenticity Analyzer & Repair Tool**

> "Every FLAC file tells a story... I find the truth."

FLAC Detective is a professional tool for analyzing the authenticity of your FLAC files. It detects "Fake FLAC" files (transcoded MP3s) by analyzing their frequency spectrum and verifies metadata integrity and duration.

## ✨ Features

- **🕵️ Advanced Spectral Analysis**: Detects frequency cutoffs typical of MP3 encoders (16kHz, 18kHz, 20kHz).
- **📊 Intelligent Scoring**: Confidence score (0-100%) based on multiple criteria (spectrum, high-frequency energy, metadata).
- **🔧 Automatic Repair**: Fixes duration issues ("Fakin' The Funk" criterion) by re-encoding without metadata loss.
- **📑 Detailed Reports**: Generates detailed text reports with statistics.
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
