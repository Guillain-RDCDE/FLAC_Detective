# 📁 Project Structure Guide

## Quick Navigation

```
FLAC_Detective/
│
├── 📄 README.md ⭐ START HERE
│   └─ Main project overview & features
│
├── 📚 docs/ (DOCUMENTATION)
│   │
│   ├── INDEX.md ⭐ DOCS ROADMAP
│   │   └─ Navigation hub for all docs
│   │
│   ├── 👤 USER DOCUMENTATION
│   │   ├── GETTING_STARTED.md (Installation & first scan)
│   │   ├── ARCHITECTURE.md (How the system works)
│   │   ├── RULES.md (Complete rule reference)
│   │   ├── EXAMPLES.md (Real usage scenarios)
│   │   └── TROUBLESHOOTING.md (Common issues)
│   │
│   ├── 🔧 development/ (FOR DEVELOPERS)
│   │   ├── CONTRIBUTING.md (How to contribute)
│   │   ├── DEVELOPMENT_SETUP.md (Dev environment)
│   │   └── TESTING.md (Testing guidelines)
│   │
│   ├── 🔬 technical/ (DEEP DIVES)
│   │   ├── LOGIC_FLOW.md (Analysis pipeline)
│   │   ├── TECHNICAL_DETAILS.md (Implementation)
│   │   └── ERROR_HANDLING.md (Error recovery)
│   │
│   ├── 📋 RULE_SPECIFICATIONS.md (Reference)
│   ├── 📖 TECHNICAL_DOCUMENTATION.md (Complete tech docs)
│   └── 📰 pypi/ (PyPI publication guides)
│
├── 💻 src/flac_detective/ (SOURCE CODE)
│   ├── main.py (Entry point)
│   ├── config.py (Configuration)
│   ├── analyzer.py (Main analyzer)
│   ├── analysis/
│   │   ├── analyzer.py
│   │   ├── metadata.py (Audio metadata)
│   │   ├── spectrum.py (Spectral analysis)
│   │   └── new_scoring/ (Scoring engine)
│   │       ├── models.py (Data structures)
│   │       ├── strategies.py (Rule strategies)
│   │       └── rules/ (11 detection rules)
│   ├── repair/ (FLAC repair tools)
│   └── reporting/ (Report generation)
│
├── 🧪 tests/ (UNIT TESTS)
│   ├── test_rule1.py (Rule 1 tests)
│   ├── test_rule4.py (Rule 4 tests)
│   ├── test_scoring.py (Scoring engine)
│   └── test_new_scoring.py (Integration tests)
│
├── 📝 examples/ (EXAMPLE CODE)
│   └── retry_mechanism_examples.py
│
├── 🛠️ scripts/ (UTILITY SCRIPTS)
│   ├── run_detective.py (Main CLI)
│   ├── demo_text_report.py
│   └── analyze_single.py
│
├── 📦 Configuration Files
│   ├── pyproject.toml (Modern Python packaging)
│   ├── setup.py (Setup script)
│   ├── requirements.txt (Production dependencies)
│   ├── requirements-dev.txt (Dev dependencies)
│   ├── Makefile (Build tasks)
│   ├── .flake8 (Linting config)
│   └── .gitignore (Git ignore rules)
│
└── 📄 Root Files
    ├── CHANGELOG.md (Version history)
    ├── LICENSE (MIT)
    ├── README.md (Project overview)
    └── MANIFEST.in (Package manifest)
```

---

## For Different User Types

### 👤 **New Users**
Start here:
1. [README.md](README.md) - What is FLAC Detective?
2. [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) - How to install & use
3. [docs/EXAMPLES.md](docs/EXAMPLES.md) - See real examples
4. [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - If issues arise

### 🎯 **Regular Users**
Quick reference:
- [docs/RULES.md](docs/RULES.md) - Understand detection rules
- [docs/EXAMPLES.md](docs/EXAMPLES.md) - Usage scenarios
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues

### 🔬 **Researchers/Auditors**
Deep understanding:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [docs/technical/LOGIC_FLOW.md](docs/technical/LOGIC_FLOW.md) - Analysis pipeline
- [docs/technical/TECHNICAL_DETAILS.md](docs/technical/TECHNICAL_DETAILS.md) - Implementation
- [src/](src/) - Actual source code

### 🛠️ **Developers**
Contributing:
- [docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md) - How to contribute
- [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md) - Dev environment
- [docs/development/TESTING.md](docs/development/TESTING.md) - Testing & quality
- [src/](src/) + [tests/](tests/) - Code & tests

---

## Key Files

| File | Purpose | For |
|------|---------|-----|
| [README.md](README.md) | Project overview | Everyone |
| [docs/INDEX.md](docs/INDEX.md) | Documentation hub | Everyone |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Installation & quickstart | New users |
| [docs/RULES.md](docs/RULES.md) | Rule specifications | Users, researchers |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design | Developers, researchers |
| [docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md) | Contribution guide | Contributors |
| [src/flac_detective/main.py](src/flac_detective/main.py) | Entry point | Developers |
| [tests/](tests/) | Unit tests | Developers |
| [pyproject.toml](pyproject.toml) | Package config | Developers, maintainers |
| [CHANGELOG.md](CHANGELOG.md) | Version history | Everyone |

---

## Common Tasks

### "I want to use FLAC Detective"
→ [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

### "How do the detection rules work?"
→ [docs/RULES.md](docs/RULES.md)

### "I have a problem"
→ [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### "I want to understand the system"
→ [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) + [docs/technical/LOGIC_FLOW.md](docs/technical/LOGIC_FLOW.md)

### "I want to contribute code"
→ [docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md)

### "I want to run tests"
→ [docs/development/TESTING.md](docs/development/TESTING.md)

### "I want to see examples"
→ [docs/EXAMPLES.md](docs/EXAMPLES.md)

---

## Directory Descriptions

### `src/` - Source Code
Main application code. Entry point is `src/flac_detective/main.py`.

### `tests/` - Unit Tests
Test suite with 9+ test files. Run with `pytest tests/`.

### `docs/` - Documentation
Complete documentation organized by user type.

### `scripts/` - Utility Scripts
Helper scripts for running analysis, demos, etc.

### `examples/` - Example Code
Example Python code showing library usage.

### `tools/` - Tools & Resources
Additional tools and conversion guides.

---

## File Organization Best Practices

✅ This project follows:
- **Clear hierarchy**: Easy to find things
- **Self-documenting**: Files clearly named
- **Modular structure**: Each component in own directory
- **Documentation at top-level**: `docs/INDEX.md` as hub
- **Separate concerns**: Code, tests, docs, scripts separate
- **Development guide**: `docs/development/` for contributors
- **Technical depth**: `docs/technical/` for advanced topics

---

## Updated: December 18, 2025

Created comprehensive documentation structure for easy navigation and onboarding.
