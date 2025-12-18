# 🚀 Getting Started with FLAC Detective

## Installation

### Requirements
- Python 3.8+
- FFmpeg (for audio processing)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/GuillainM/FLAC_Detective.git
cd FLAC_Detective

# Install dependencies
pip install -r requirements.txt

# Optional: Install development dependencies
pip install -r requirements-dev.txt
```

## First Scan

### Basic Usage

```bash
# Analyze a single folder
python -m flac_detective /path/to/flac/files

# Or use the helper script
python scripts/run_detective.py
```

### Output

FLAC Detective generates:
- **Console report** - Real-time analysis with progress bar
- **Text report** - Detailed results saved as `flac_report_YYYYMMDD_HHMMSS.txt`
- **Scoring breakdown** - Individual rule scores for each file

### Understanding Results

```
Score ≥ 86  → FAKE_CERTAIN ❌
Score 61-85 → SUSPICIOUS ⚠️
Score 31-60 → WARNING ⚡
Score ≤ 30  → AUTHENTIC ✅
```

## Configuration

Edit `src/flac_detective/config.py` to customize:
- Scoring thresholds
- Analysis rules
- Output format
- Cache behavior

## Next Steps

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Understand how it works
- [EXAMPLES.md](../EXAMPLES.md) - See real usage examples
- [RULES.md](../RULES.md) - Learn about detection rules
