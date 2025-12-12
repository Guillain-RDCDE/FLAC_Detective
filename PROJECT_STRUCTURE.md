# 📁 Project Structure

This document describes the organization of the FLAC Detective project.

## 🗂️ Directory Structure

```
FLAC_Detective/
├── .github/                    # GitHub Actions workflows and templates
│   └── workflows/
│       ├── ci.yml             # Continuous Integration
│       └── publish-pypi.yml   # Automatic PyPI publication
│
├── docs/                       # Documentation
│   ├── pypi/                  # PyPI publication guides
│   ├── CHANGELOG.md           # Version history (symlink)
│   ├── DOCUMENTATION_UPDATES_v0.6.1.md
│   ├── FLAC_DECODER_ERROR_HANDLING.md
│   ├── GUIDE_RETRY_MECHANISM.md
│   ├── LOGIC_FLOW.md
│   ├── PYPI_PUBLICATION_GUIDE.md
│   ├── README.md              # Documentation index
│   ├── RESUME_MODIFICATIONS.md
│   ├── RULE_SPECIFICATIONS.md
│   ├── TECHNICAL_DOCUMENTATION.md
│   └── VERSION_MANAGEMENT.md
│
├── examples/                   # Usage examples
│   └── retry_mechanism_examples.py
│
├── scripts/                    # Utility scripts
│   └── update_version.py      # Automatic version updater
│
├── src/                        # Source code
│   └── flac_detective/
│       ├── __version__.py     # Version information (single source of truth)
│       ├── analysis/          # Analysis modules
│       │   ├── new_scoring/   # Scoring system
│       │   │   ├── audio_loader.py  # Retry mechanism
│       │   │   ├── rules/     # Individual rules
│       │   │   └── ...
│       │   ├── analyzer.py
│       │   ├── quality.py
│       │   └── spectrum.py
│       ├── reporting/         # Report generation
│       └── main.py            # CLI entry point
│
├── tests/                      # Unit tests
│   ├── test_audio_loader_retry.py
│   └── ...
│
├── tools/                      # Development tools
│
├── .flake8                     # Flake8 configuration
├── .gitignore                  # Git ignore patterns
├── CHANGELOG.md                # Version history
├── LICENSE                     # MIT License
├── MANIFEST.in                 # Package manifest
├── Makefile                    # Make commands
├── PROJECT_STRUCTURE.md        # This file
├── README.md                   # Main documentation
├── pyproject.toml              # Project configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
└── setup.py                    # Setup script (compatibility)
```

## 📝 Key Files

### Configuration Files

- **`pyproject.toml`** - Main project configuration (PEP 518)
  - Package metadata
  - Dependencies
  - Build system
  - Tool configurations (black, isort, pytest, etc.)

- **`.gitignore`** - Git ignore patterns
  - Python artifacts
  - Virtual environments
  - IDE files
  - Temporary files

- **`.flake8`** - Linting configuration
  - Code style rules
  - Complexity limits

### Documentation

- **`README.md`** - Main project documentation
  - Features
  - Installation
  - Usage
  - Examples

- **`CHANGELOG.md`** - Version history
  - Release notes
  - Breaking changes
  - New features

- **`docs/`** - Detailed documentation
  - Technical documentation
  - Rule specifications
  - Guides and tutorials

### Source Code

- **`src/flac_detective/__version__.py`** - **Single source of truth for version**
  - Version number
  - Release date
  - Release name

- **`src/flac_detective/`** - Main package
  - Analysis modules
  - Reporting
  - CLI

### Scripts

- **`scripts/update_version.py`** - Automatic version updater
  - Updates all files with new version
  - Ensures consistency

### Tests

- **`tests/`** - Unit tests
  - Test coverage
  - Integration tests

## 🔄 Workflow

### Development

1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Install dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Make changes
6. Run linting: `make lint`
7. Commit and push

### Release

1. Update version in `src/flac_detective/__version__.py`
2. Run `python scripts/update_version.py`
3. Update `CHANGELOG.md`
4. Commit: `git commit -am "chore: Release vX.X.X"`
5. Tag: `git tag -a vX.X.X -m "Release vX.X.X"`
6. Push: `git push && git push --tags`
7. GitHub Actions automatically publishes to PyPI

## 📦 Package Distribution

### What's Included

The package includes:
- Source code (`src/flac_detective/`)
- Documentation (`docs/`)
- Examples (`examples/`)
- License (`LICENSE`)
- README (`README.md`)

### What's Excluded

The following are excluded from the package:
- Tests (`tests/`)
- Development tools (`tools/`)
- Scripts (`scripts/`)
- GitHub workflows (`.github/`)
- IDE files (`.vscode/`, `.idea/`)
- Temporary files (`*.tmp`, `*.bak`)

See `MANIFEST.in` for details.

## 🎯 Best Practices

### File Organization

- ✅ Source code in `src/`
- ✅ Tests in `tests/`
- ✅ Documentation in `docs/`
- ✅ Examples in `examples/`
- ✅ Scripts in `scripts/`
- ✅ Configuration files at root

### Version Management

- ✅ Single source of truth: `src/flac_detective/__version__.py`
- ✅ Automatic propagation via `scripts/update_version.py`
- ✅ Manual CHANGELOG updates

### Documentation

- ✅ README at root for quick overview
- ✅ Detailed docs in `docs/`
- ✅ Inline code documentation
- ✅ Examples for common use cases

### Testing

- ✅ Unit tests in `tests/`
- ✅ Test coverage tracking
- ✅ CI/CD via GitHub Actions

## 🔗 Related Documentation

- [README.md](README.md) - Main documentation
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md) - Version management guide
- [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) - Technical details

---

**Last Updated**: December 12, 2025  
**Version**: 0.6.6
