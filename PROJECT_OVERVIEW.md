# FLAC Detective - Project Overview

**Professional audio quality analysis tool for detecting MP3-to-FLAC transcodes.**

## Project Structure

```
FLAC_Detective/
├── src/flac_detective/          # Main source code
│   ├── analysis/                # Audio analysis engine
│   │   ├── new_scoring/         # 11-rule scoring system
│   │   │   ├── rules/           # Individual rule implementations
│   │   │   ├── calculator.py    # Score orchestration
│   │   │   └── verdict.py       # Verdict determination
│   │   ├── spectrum.py          # Spectral analysis
│   │   └── audio_cache.py       # Audio loading optimization
│   ├── reporting/               # Report generation
│   ├── repair/                  # FLAC repair functionality
│   └── main.py                  # CLI entry point
│
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── benchmarks/              # Performance benchmarks
│
├── docs/                        # Complete documentation
│   ├── user-guide/              # User documentation
│   │   ├── GETTING_STARTED.md
│   │   ├── EXAMPLES.md
│   │   ├── REPORT_FORMAT.md
│   │   └── TROUBLESHOOTING.md
│   ├── technical/               # Technical documentation
│   │   ├── ARCHITECTURE.md
│   │   ├── RULES.md
│   │   ├── RULE_SPECIFICATIONS.md
│   │   ├── LOGIC_FLOW.md
│   │   ├── TECHNICAL_DOCUMENTATION.md
│   │   ├── FLAC_DECODER_ERROR_HANDLING.md
│   │   ├── GUIDE_RETRY_MECHANISM.md
│   │   └── TYPE_HINTS.md
│   ├── reference/               # API reference
│   │   ├── API_DOCUMENTATION.md
│   │   └── PYTHON_API_GUIDE.md
│   ├── development/             # Developer guide
│   │   ├── CONTRIBUTING.md
│   │   ├── DEVELOPMENT_SETUP.md
│   │   └── TESTING.md
│   ├── automation/              # Automation docs
│   │   ├── DOCKER_GUIDE.md
│   │   ├── LOGGING_GUIDE.md
│   │   └── VERSION_MANAGEMENT.md
│   ├── ci-cd/                   # CI/CD documentation
│   │   ├── CI_CD_GUIDE.md
│   │   ├── PRE_COMMIT_SETUP.md
│   │   ├── CODE_QUALITY_SETUP.md
│   │   ├── COVERAGE_SETUP.md
│   │   ├── CHANGELOG_AUTOMATION.md
│   │   ├── DEPENDENCY_AUTOMATION.md
│   │   ├── PERFORMANCE_BENCHMARKING.md
│   │   ├── RELEASE_GUIDE.md
│   │   ├── SECURITY_GUIDE.md
│   │   ├── PULL_REQUEST_GUIDE.md
│   │   ├── ISSUE_TEMPLATES_GUIDE.md
│   │   └── STALE_BOT_GUIDE.md
│   ├── pypi/                    # PyPI publication docs
│   └── README.md                # Documentation index
│
├── .github/                     # GitHub configuration
│   ├── workflows/               # CI/CD pipelines
│   │   ├── ci.yml              # Main CI pipeline
│   │   ├── release.yml         # Automated releases
│   │   ├── docker.yml          # Docker builds
│   │   ├── security-scan.yml   # Security scanning
│   │   ├── codeql.yml          # CodeQL analysis
│   │   └── benchmark.yml       # Performance benchmarks
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── dependabot.yml          # Dependency automation
│
├── scripts/                     # Utility scripts
│   ├── bump_version.py         # Version management
│   ├── prepare_release.py      # Release preparation
│   ├── validate_ci.py          # CI validation
│   └── coverage_report.py      # Coverage reporting
│
├── examples/                    # Usage examples
│   ├── repair/                 # Repair examples
│   └── logging_example.py      # Logging configuration
│
├── tools/                       # Development tools
│
├── README.md                    # Main project README
├── CHANGELOG.md                 # Version history
├── CONTRIBUTING.md              # Contribution guidelines
├── CODE_OF_CONDUCT.md          # Community guidelines
├── SECURITY.md                 # Security policy
├── LICENSE                     # MIT License
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Docker compose setup
└── .pre-commit-config.yaml     # Pre-commit hooks
```

## Quick Links

### Getting Started
- [README.md](README.md) - Project overview and quick start
- [User Guide](docs/user-guide/GETTING_STARTED.md) - Installation and usage
- [Examples](docs/user-guide/EXAMPLES.md) - Usage examples

### Documentation
- [Documentation Index](docs/README.md) - Complete documentation structure
- [Technical Docs](docs/technical/TECHNICAL_DOCUMENTATION.md) - Architecture and algorithms
- [API Reference](docs/reference/API_DOCUMENTATION.md) - Python API

### Development
- [Contributing Guide](docs/development/CONTRIBUTING.md) - How to contribute
- [Development Setup](docs/development/DEVELOPMENT_SETUP.md) - Setup dev environment
- [Testing Guide](docs/development/TESTING.md) - Running tests

### CI/CD & Quality
- [CI/CD Guide](docs/ci-cd/CI_CD_GUIDE.md) - Continuous integration
- [Code Quality](docs/ci-cd/CODE_QUALITY_SETUP.md) - Code quality tools
- [Release Process](docs/ci-cd/RELEASE_GUIDE.md) - How to release

## Key Features

- **11-Rule Scoring System**: Advanced detection with intelligent protection
- **4-Level Verdict System**: AUTHENTIC, WARNING, SUSPICIOUS, FAKE_CERTAIN
- **Automatic Repair**: Fixes corrupted FLAC files with metadata preservation
- **High Performance**: 80% faster through caching and optimization
- **Comprehensive Testing**: 95%+ code coverage
- **Professional CI/CD**: Automated testing, security scanning, releases
- **Docker Support**: Pre-built images for easy deployment

## Technology Stack

- **Language**: Python 3.8+
- **Audio Processing**: NumPy, SciPy, soundfile
- **Metadata**: mutagen
- **CLI**: Rich (terminal formatting)
- **Testing**: pytest, pytest-cov
- **Code Quality**: black, isort, flake8, mypy, pre-commit
- **Documentation**: Sphinx, Read the Docs
- **CI/CD**: GitHub Actions
- **Security**: CodeQL, Bandit, Safety
- **Versioning**: Commitizen (Conventional Commits)

## Contribution Workflow

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Fork and clone the repository
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Set up pre-commit: `pre-commit install`
5. Create feature branch: `git checkout -b feature/name`
6. Make changes and run tests: `pytest`
7. Commit using conventional commits: `cz commit`
8. Push and open Pull Request

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
- **Discussions**: [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
- **Documentation**: [Read the Docs](https://flac-detective.readthedocs.io)
- **Security**: Email [guillain@poulpe.us](mailto:guillain@poulpe.us)

---

**Version**: 0.9.0
**License**: MIT
**Status**: Beta
**Python**: 3.8+
