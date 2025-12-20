# 🛠️ Development Setup

## Prerequisites

- Python 3.8+
- Git
- FFmpeg
- Virtual environment tool (venv or conda)

## Step 1: Clone & Environment

```bash
# Clone the repository
git clone https://github.com/GuillainM/FLAC_Detective.git
cd FLAC_Detective

# Create virtual environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

## Step 2: Install Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# This includes:
# - pytest (testing)
# - black (formatting)
# - flake8 (linting)
# - mypy (type checking)
# - mutagen (audio metadata)
# - scipy (signal processing)
```

## Step 3: Verify Setup

```bash
# Run tests
pytest tests/ -v

# Check code style
make lint

# Both should pass without errors
```

## Project Structure

```
src/flac_detective/
├── __init__.py           # Package init
├── main.py              # Entry point
├── config.py            # Configuration
├── colors.py            # Console colors
├── analysis/
│   ├── analyzer.py      # Main analyzer
│   ├── metadata.py      # Metadata reading
│   ├── spectrum.py      # Spectral analysis
│   └── new_scoring/     # Scoring engine
│       ├── models.py    # Data models
│       ├── strategies.py # Rule strategies
│       └── rules/       # Individual rules
├── repair/              # FLAC repair tools
└── reporting/           # Report generation
```

## Common Tasks

### Run Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_rule1.py

# With coverage
pytest --cov=src tests/
```

### Format Code

```bash
# Auto-format
black src/ tests/

# Check only (no changes)
black --check src/ tests/
```

### Lint Code

```bash
# Check style
flake8 src/ tests/

# With line length
flake8 --max-line-length=100 src/
```

### Type Check

```bash
# Check types
mypy src/

# Strict mode
mypy --strict src/
```

### Run Locally

```bash
# Single file
python -m flac_detective /path/to/file.flac

# Entire folder
python -m flac_detective /path/to/folder

# Using script
python scripts/run_detective.py
```

## Debugging

### Enable Debug Output

```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug FFT Issues

```bash
python scripts/debug_spectrum.py /path/to/file.flac
```

### Inspect Analysis Result

```python
from flac_detective.analysis.analyzer import AudioAnalyzer

analyzer = AudioAnalyzer()
context = analyzer.analyze_file("/path/to/file.flac")
print(f"Score: {context.score}")
print(f"Verdict: {context.verdict}")
print(f"Reasons: {context.reasons}")
```

## Adding New Rules

1. **Create rule function** in `src/flac_detective/analysis/new_scoring/rules/`
2. **Create strategy class** in `src/flac_detective/analysis/new_scoring/strategies.py`
3. **Add tests** in `tests/test_rule_XX.py`
4. **Document** in `docs/RULES.md`
5. **Update** `src/flac_detective/config.py` if needed

## Common Issues

### "ModuleNotFoundError: No module named 'flac_detective'"

```bash
# Make sure you're in the project root
cd FLAC_Detective

# Reinstall in development mode
pip install -e .
```

### FFmpeg not found

```bash
# Install FFmpeg
# Windows (with choco): choco install ffmpeg
# macOS (with brew): brew install ffmpeg
# Linux (Ubuntu): sudo apt-get install ffmpeg
```

### Tests fail

```bash
# Check Python version
python --version  # Should be 3.8+

# Clean cache and reinstall
rm -rf .venv
python -m venv .venv
pip install -r requirements-dev.txt
pytest tests/
```

## Need Help?

- Check [TESTING.md](TESTING.md) for testing guidelines
- Read [../ARCHITECTURE.md](../ARCHITECTURE.md) for system design
- Open an issue: https://github.com/GuillainM/FLAC_Detective/issues
