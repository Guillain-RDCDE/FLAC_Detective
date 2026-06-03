# FLAC Detective Documentation

Welcome to the FLAC Detective documentation! This tool analyzes FLAC audio files to detect MP3-to-FLAC transcodes using advanced spectral analysis.

```{toctree}
:maxdepth: 2
:hidden:

getting-started
user-guide
api-reference
technical-details
roadmap-formats
```

## Quick Navigation

### For Users
- **[Getting Started](getting-started.md)** - Installation, basic usage, first analysis
- **[User Guide](user-guide.md)** - Complete usage guide, examples, understanding results

### For Developers
- **[API Reference](api-reference.md)** - Python API documentation and examples
- **[Technical Details](technical-details.md)** - Architecture, detection rules, algorithms
- **[Contributing](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md)** - Development setup, contributing guidelines

### Deep dives (for the curious & specialists)
- **[ML case study](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)** - How Rule 12's CNN was built: the false-positive audit, the dead-ends, the mono→stereo breakthrough
- **[Formats roadmap](roadmap-formats.md)** - Why supporting ALAC/APE is an *input* problem, and the bitrate-from-original gotcha

## What is FLAC Detective?

FLAC Detective is a command-line tool that detects fake lossless audio files (MP3s transcoded to FLAC, ALAC, APE or WAV). It uses an 11-rule scoring system — plus an optional 12th CNN rule — with advanced spectral analysis to achieve high accuracy while protecting legitimate files from vinyl, cassettes, and high-quality MP3 sources.

### Key Features

- **High Precision**: 11-rule scoring system (0-150 points), plus an optional 12th CNN rule
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

# Already installed? Use --upgrade to get the latest version
pip install --upgrade flac-detective

# Via Docker
docker pull ghcr.io/guillain-rdcde/flac_detective:latest
```

> Plain `pip install` does not upgrade an existing install — it prints
> "Requirement already satisfied" and exits. Use `--upgrade` (or `-U`).
> See [Getting Started → Upgrading](getting-started.md#upgrading-to-the-latest-version) for details.

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
| ✅ AUTHENTIC | ≤ 30 | No evidence of transcoding |
| ❓ WARNING | 31-54 | Borderline - manual review recommended |
| ⚠️ SUSPICIOUS | 55-85 | Likely transcode |
| ❌ FAKE_CERTAIN | ≥ 86 | Multiple strong indicators of transcoding |

## Documentation Structure

The documentation is organised into core guides plus two deep dives:

1. **[index.md](index.md)** (this file) - Overview and navigation
2. **[getting-started.md](getting-started.md)** - Installation and first steps
3. **[user-guide.md](user-guide.md)** - Complete usage guide with examples
4. **[api-reference.md](api-reference.md)** - Python API documentation
5. **[technical-details.md](technical-details.md)** - How it works under the hood (11 rules + optional ML Rule 12)
6. **[CONTRIBUTING.md](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md)** - Development and contribution guide
7. **[ml/README.md](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)** - The ML model R&D case study
8. **[roadmap-formats.md](roadmap-formats.md)** - Multi-format design note

## Common Tasks

### I want to analyze my music collection
→ Start with [Getting Started](getting-started.md), then read [User Guide](user-guide.md)

### I want to use FLAC Detective in my Python code
→ Read [API Reference](api-reference.md)

### I want to understand how detection works
→ Read [Technical Details](technical-details.md)

### I want to contribute code or report bugs
→ Read [Contributing](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md)

## External Resources

- **GitHub Repository**: https://github.com/Guillain-RDCDE/FLAC_Detective
- **PyPI Package**: https://pypi.org/project/flac-detective/
- **Issue Tracker**: https://github.com/Guillain-RDCDE/FLAC_Detective/issues
- **Discussions**: https://github.com/Guillain-RDCDE/FLAC_Detective/discussions

## Support

- **Report bugs**: [GitHub Issues](https://github.com/Guillain-RDCDE/FLAC_Detective/issues)
- **Ask questions**: [GitHub Discussions](https://github.com/Guillain-RDCDE/FLAC_Detective/discussions)
- **Security issues**: Email guillain@poulpe.us (see [SECURITY.md](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/SECURITY.md))

## License

FLAC Detective is released under the MIT License. See [LICENSE](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/LICENSE) for details.

---

**Version**: 1.1.0 | **Last Updated**: June 2026
