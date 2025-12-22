# 🎵 FLAC Detective

![FLAC Detective Banner](https://raw.githubusercontent.com/GuillainM/FLAC_Detective/main/assets/flac_detective_banner.png)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/flac-detective)](https://pypi.org/project/flac-detective/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/flac-detective)](https://pypi.org/project/flac-detective/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-yellow)](https://github.com/GuillainM/FLAC_Detective)
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

```bash
# Install via pip (Recommended)
pip install flac-detective

# OR run with Docker
docker pull ghcr.io/guillainm/flac-detective:latest
```

**📦 See [Getting Started](docs/getting-started.md) for complete installation instructions.**

### Basic Usage

```bash
# Analyze current directory
flac-detective .

# Analyze specific directory
flac-detective /path/to/music
```

**📖 See [User Guide](docs/user-guide.md) for detailed usage examples and command line options.**

---

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- [**Documentation Index**](docs/index.md) - Overview and navigation
- [**Getting Started**](docs/getting-started.md) - Installation and first analysis
- [**User Guide**](docs/user-guide.md) - Complete usage guide with examples
- [**Technical Details**](docs/technical-details.md) - Deep dive into detection rules and algorithms
- [**API Reference**](docs/api-reference.md) - Python API documentation
- [**Contributing**](.github/CONTRIBUTING.md) - Development guide

---

## 🎯 Use Cases

- **Library Maintenance**: Clean your music collection of fake lossless files
- **Quality Verification**: Validate FLAC authenticity before archiving
- **Batch Processing**: Analyze large music libraries efficiently
- **Format Validation**: Ensure genuine lossless quality for critical listening

---

## 🤝 Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](.github/CONTRIBUTING.md) for detailed guidelines and [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md) for community standards.

---

## 🔒 Security

For security policy and vulnerability reporting, please see [SECURITY.md](.github/SECURITY.md).

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Discussions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)

---

**FLAC Detective** - *Maintaining authentic lossless audio collections*
