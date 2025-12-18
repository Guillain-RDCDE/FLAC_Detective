# 👋 Welcome to FLAC Detective

**You landed in the right place!** This guide will help you navigate the project.

## 🎯 What are you here to do?

### 👤 I want to **USE** FLAC Detective to analyze FLAC files

**Start here:**
1. Read: [README.md](README.md) - Features and overview
2. Install: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
3. Learn: [docs/RULES.md](docs/RULES.md) - How detection works
4. Try: [docs/EXAMPLES.md](docs/EXAMPLES.md) - Usage examples

**Questions?** Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

### 👨‍💻 I want to **DEVELOP** or **CONTRIBUTE**

**Start here:**
1. Setup: [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md)
2. Understand: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. Read: [docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md)
4. Code: [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)

**Tests?** See [docs/development/TESTING.md](docs/development/TESTING.md)

---

### 📚 I want to **UNDERSTAND** the technical details

**Read:**
- [docs/LOGIC_FLOW.md](docs/LOGIC_FLOW.md) - Analysis process
- [docs/RULE_SPECIFICATIONS.md](docs/RULE_SPECIFICATIONS.md) - All 11 rules explained
- [docs/FLAC_DECODER_ERROR_HANDLING.md](docs/FLAC_DECODER_ERROR_HANDLING.md) - Error handling

---

### 📦 I want to **PUBLISH** to PyPI

**See:** [docs/pypi/](docs/pypi/) for publication documentation

---

## 📁 Project Structure

```
FLAC_Detective/
├── README.md                    ← Start here (feature overview)
├── docs/
│   ├── README.md                ← Documentation index
│   ├── GETTING_STARTED.md       ← Installation guide
│   ├── RULES.md                 ← Detection rules overview
│   ├── RULE_SPECIFICATIONS.md   ← Detailed rule specs
│   ├── EXAMPLES.md              ← Usage examples
│   ├── TROUBLESHOOTING.md       ← Common issues
│   ├── ARCHITECTURE.md          ← System design
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── development/             ← Contributor docs
│   ├── pypi/                    ← PyPI publication
│   └── CLEANUP_LOG.md           ← What was cleaned up
├── src/
│   └── flac_detective/          ← Main package code
├── scripts/
│   └── README.md                ← Available scripts
├── examples/
│   └── retry_mechanism_examples.py
├── tests/
│   └── Unit tests
└── CHANGELOG.md                 ← Version history
```

---

## ⚡ Quick Start Commands

```bash
# Installation
pip install -r requirements.txt

# Run analysis
python scripts/run_detective.py /path/to/flac/files

# Run tests
pytest

# Single file analysis
python scripts/analyze_single.py track.flac
```

---

## 🎯 What is FLAC Detective?

FLAC Detective detects MP3-to-FLAC transcodes using:
- Advanced spectral analysis (FFT)
- 11-rule detection system
- Multi-phase validation
- <0.5% false positive rate

**Why?** To help music enthusiasts verify that FLAC files are truly lossless, not just MP3s in FLAC containers.

---

## 📞 Need Help?

1. **Getting started?** → [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
2. **Troubleshooting?** → [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
3. **Understanding rules?** → [docs/RULES.md](docs/RULES.md)
4. **Full docs** → [docs/README.md](docs/README.md)

---

**Happy analyzing! 🎵**
