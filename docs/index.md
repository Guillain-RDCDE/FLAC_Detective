# FLAC Detective Documentation

Welcome to the FLAC Detective documentation! This tool analyzes FLAC audio files to detect MP3-to-FLAC transcodes using advanced spectral analysis.

## Quick Navigation

### For Users
- **[Getting Started](getting-started.md)** - Installation, basic usage, first analysis
- **[User Guide](user-guide.md)** - Complete usage guide, examples, understanding results

### For Developers
- **[API Reference](api-reference.md)** - Python API documentation and examples
- **[Technical Details](technical-details.md)** - Architecture, detection rules, algorithms
- **[Contributing](../.github/CONTRIBUTING.md)** - Development setup, contributing guidelines

## What is FLAC Detective?

FLAC Detective is a command-line tool that detects fake lossless audio files (MP3s transcoded to FLAC). It uses an 11-rule scoring system with advanced spectral analysis to achieve high accuracy while protecting legitimate files from vinyl, cassettes, and high-quality MP3 sources.

### Key Features

- **High Precision**: 11-rule scoring system (0-150 points)
- **4-Level Verdict**: AUTHENTIC, WARNING, SUSPICIOUS, FAKE_CERTAIN
- **Protection Layers**: Prevents false positives for analog sources
- **Fast Performance**: 80% faster than baseline through caching
- **Flexible Output**: Console, text reports, JSON export
- **Auto-Repair**: Corrupted FLAC files automatically fixed

## Quick Start

### Installation

```bash
# Via pip (recommended)
pip install flac-detective

# Via Docker
docker pull ghcr.io/guillainm/flac-detective:latest
```

### Basic Usage

```bash
# Analyze a directory
flac-detective /path/to/music

# Generate JSON report
flac-detective /path/to/music --format json

# Verbose output
flac-detective /path/to/music --verbose
```

### Understanding Verdicts

| Verdict | Score | Meaning |
|---------|-------|---------|
| ✅ AUTHENTIC | ≤ 30 | High confidence - genuine lossless |
| ⚡ WARNING | 31-60 | Manual review recommended |
| ⚠️ SUSPICIOUS | 61-85 | Likely transcode |
| ❌ FAKE_CERTAIN | ≥ 86 | Definite transcode |

## Documentation Structure

This documentation is organized into 6 focused documents:

1. **[index.md](index.md)** (this file) - Overview and navigation
2. **[getting-started.md](getting-started.md)** - Installation and first steps
3. **[user-guide.md](user-guide.md)** - Complete usage guide with examples
4. **[api-reference.md](api-reference.md)** - Python API documentation
5. **[technical-details.md](technical-details.md)** - How it works under the hood
6. **[CONTRIBUTING.md](../.github/CONTRIBUTING.md)** - Development and contribution guide

## Common Tasks

### I want to analyze my music collection
→ Start with [Getting Started](getting-started.md), then read [User Guide](user-guide.md)

### I want to use FLAC Detective in my Python code
→ Read [API Reference](api-reference.md)

### I want to understand how detection works
→ Read [Technical Details](technical-details.md)

### I want to contribute code or report bugs
→ Read [Contributing](../.github/CONTRIBUTING.md)

## External Resources

- **GitHub Repository**: https://github.com/GuillainM/FLAC_Detective
- **PyPI Package**: https://pypi.org/project/flac-detective/
- **Issue Tracker**: https://github.com/GuillainM/FLAC_Detective/issues
- **Discussions**: https://github.com/GuillainM/FLAC_Detective/discussions
- **ReadTheDocs**: https://flac-detective.readthedocs.io/

## Support

- **Report bugs**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Ask questions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
- **Security issues**: Email guillain@poulpe.us (see [SECURITY.md](../SECURITY.md))

## License

FLAC Detective is released under the MIT License. See [LICENSE](../LICENSE) for details.

---

**Version**: 0.9.6 | **Last Updated**: December 2024
