# 🎵 FLAC Detective

![FLAC Detective Banner](https://raw.githubusercontent.com/GuillainM/FLAC_Detective/main/assets/flac_detective_banner.png)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/flac-detective)](https://pypi.org/project/flac-detective/)
[![Documentation Status](https://readthedocs.org/projects/flac-detective/badge/?version=latest)](https://flac-detective.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-yellow)](https://github.com/GuillainM/FLAC_Detective)
[![Coverage Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/GuillainM/FLAC_Detective/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/GuillainM/FLAC_Detective/blob/python-coverage-comment-action-data/htmlcov/index.html)
[![codecov](https://codecov.io/gh/GuillainM/FLAC_Detective/branch/main/graph/badge.svg)](https://codecov.io/gh/GuillainM/FLAC_Detective)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

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
- **🔧 Robust Error Handling**: Automatic retries, partial file reading, and comprehensive diagnostic tracking
- **🔨 Automatic Repair**: Corrupted FLAC files are automatically repaired with full metadata preservation

---

## 🚀 Quick Start

### Installation

#### Option 1: Install via pip (Recommended)

```bash
pip install flac-detective
```

#### Option 2: Run with Docker

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/guillainm/flac-detective:latest

# Analyze files
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data
```

**📦 See [Getting Started](docs/getting-started.md) for complete installation and usage documentation.**

### Basic Usage

#### Command Line

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

#### Docker

```bash
# Analyze a directory
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data

# With repair enabled
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data --repair

# Generate JSON report
docker run --rm -v /path/to/audio:/data ghcr.io/guillainm/flac-detective:latest /data --format json > report.json
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

## 🆕 What's New in v0.9.0

### Complete Project Restructuring and Documentation Overhaul
- **Professional Documentation Structure**: Reorganized all documentation into audience-specific directories (user-guide, technical, reference, development, automation, ci-cd)
- **Comprehensive Navigation**: Added PROJECT_OVERVIEW.md and DOCUMENTATION_GUIDE.md for easy navigation
- **Clean Root Directory**: Removed 9+ temporary implementation files and build artifacts
- **113 Total Changes**: 78 new files added, professional project structure, production-ready organization
- **Enhanced Discoverability**: Clear separation between user docs, technical docs, API reference, and developer guides

### Complete CI/CD Automation
- **GitHub Actions Workflows**: Automated testing, building, security scanning, and releases
- **Docker Support**: Pre-built images on GitHub Container Registry
- **Security Scanning**: CodeQL, Bandit, Safety, pip-audit
- **Automated Releases**: PyPI publishing via Trusted Publishers
- **Performance Benchmarking**: Automated performance regression detection
- **Code Quality**: Pre-commit hooks, coverage reporting, linting

### Community Standards
- **CODE_OF_CONDUCT.md**: Community guidelines and standards
- **CONTRIBUTING.md**: Comprehensive contribution guide
- **SECURITY.md**: Security policy and vulnerability reporting
- **Issue Templates**: Bug reports, feature requests, performance issues, documentation, questions
- **Pull Request Template**: Structured PR workflow

For previous releases, see [CHANGELOG.md](CHANGELOG.md)

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
from flac_detective import FLACAnalyzer
from pathlib import Path

# Create analyzer
analyzer = FLACAnalyzer(sample_duration=30.0)

# Analyze a file
result = analyzer.analyze_file(Path('song.flac'))

print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}/100")
print(f"Reason: {result['reason']}")
```

**📚 See [API Reference](docs/api-reference.md) for complete Python API documentation**

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

### Version Management & Releases

FLAC Detective uses [Commitizen](https://commitizen-tools.github.io/commitizen/) for automated changelog generation and version management.

```bash
# Install pre-commit hooks (includes commit message validation)
pre-commit install --hook-type commit-msg

# Create a conventional commit interactively
cz commit

# Bump version and update CHANGELOG automatically
cz bump --changelog

# Or use the helper script
python scripts/bump_version.py --dry-run  # Preview changes
python scripts/bump_version.py --push     # Bump and push to trigger release
```

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:
- `feat:` - New features (bumps MINOR version)
- `fix:` - Bug fixes (bumps PATCH version)
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements

See [Changelog Automation Guide](docs/ci-cd/CHANGELOG_AUTOMATION.md) for detailed documentation on version management.

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

Complete documentation is available in the [docs/](docs/) directory:

- [**Documentation Index**](docs/index.md) - Start here! Overview and navigation
- [**Getting Started**](docs/getting-started.md) - Installation and first analysis
- [**User Guide**](docs/user-guide.md) - Complete usage guide with examples
- [**API Reference**](docs/api-reference.md) - Python API documentation
- [**Technical Details**](docs/technical-details.md) - Architecture, rules, and algorithms
- [**Contributing**](docs/contributing.md) - Development and contribution guide
- [**Changelog**](CHANGELOG.md) - Version history and release notes

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

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

### 📋 Issue Templates

We provide templates for different types of contributions:

1. **🐛 [Bug Report](https://github.com/GuillainM/FLAC_Detective/issues/new?template=bug_report.yml)**: Report bugs or unexpected behavior
2. **✨ [Feature Request](https://github.com/GuillainM/FLAC_Detective/issues/new?template=feature_request.yml)**: Suggest new features or enhancements
3. **⚡ [Performance Issue](https://github.com/GuillainM/FLAC_Detective/issues/new?template=performance_issue.yml)**: Report slow performance or resource issues
4. **📝 [Documentation Issue](https://github.com/GuillainM/FLAC_Detective/issues/new?template=documentation.yml)**: Report documentation problems
5. **❓ [Question](https://github.com/GuillainM/FLAC_Detective/issues/new?template=question.yml)**: Ask questions about usage

**[View Issue Templates Guide](docs/ci-cd/ISSUE_TEMPLATES_GUIDE.md)** for detailed information.

### How to Contribute

1. **Report Issues**: Use the appropriate [issue template](https://github.com/GuillainM/FLAC_Detective/issues/new/choose)
2. **Suggest Features**: Submit a [feature request](https://github.com/GuillainM/FLAC_Detective/issues/new?template=feature_request.yml)
3. **Start Discussions**: Join [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
4. **Submit PRs**: Read [CONTRIBUTING.md](CONTRIBUTING.md) first, then fork the repo, create a feature branch, and submit a pull request
5. **Improve Docs**: Documentation improvements are always appreciated

### Community Guidelines

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) to maintain a welcoming and inclusive environment for all contributors.

### Development Workflow

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/FLAC_Detective.git
cd FLAC_Detective

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks for code quality
python scripts/setup_precommit.py
# Or manually: pre-commit install

# Create feature branch
git checkout -b feature/amazing-feature

# Make changes and run tests
pytest tests/unit/ -v                    # Unit tests
pytest tests/integration/ -v             # Integration tests
pytest --cov=flac_detective              # With coverage

# Code quality checks (runs automatically on commit via pre-commit hooks)
pre-commit run --all-files               # Run all checks manually
black src tests                          # Format code
isort src tests                          # Sort imports
flake8 src tests                         # Lint code
mypy src                                 # Type check

# Commit and push (pre-commit hooks run automatically)
git commit -m "Add amazing feature"
git push origin feature/amazing-feature

# Open Pull Request on GitHub
```

**Python Version Requirements:**
- **Supported:** Python 3.8 - 3.12
- **Testing:** Use Python 3.8-3.12 for running tests (scipy/numpy compatibility)

**Running Tests:**
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage report
pytest --cov=flac_detective --cov-report=html

# See tests/TESTING_STATUS.md for detailed testing guide
```

---

## 🔒 Security

Security is a priority for FLAC Detective. We use multiple automated tools to ensure code and dependency security.

### Security Features

- **🛡️ Dependabot**: Automated dependency updates for security patches
- **🔍 CodeQL**: Static code analysis for vulnerability detection
- **🚨 Bandit**: Python security linter
- **📦 Safety & Pip-audit**: Dependency vulnerability scanners
- **📋 Security Policy**: Responsible disclosure process

### Reporting Vulnerabilities

**Please do NOT report security vulnerabilities through public GitHub issues.**

Email security issues to: **guillain@poulpe.us**

See [SECURITY.md](SECURITY.md) for:
- Supported versions
- Reporting guidelines
- Security best practices
- Vulnerability disclosure process

### Security Documentation

- [**SECURITY.md**](SECURITY.md) - Official security policy
- [**Security Guide**](docs/ci-cd/SECURITY_GUIDE.md) - Comprehensive security documentation

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

**FLAC Detective v0.9.0** - *Maintaining authentic lossless audio collections*
