# 📦 PyPI Publication Guides

This directory contains all documentation related to publishing FLAC Detective on PyPI.

## 📚 Available Guides

### For Users

- **[PYPI_SECRET_SETUP.md](PYPI_SECRET_SETUP.md)** - Quick guide to configure GitHub secret (5 min)
- **[PYPI_SECRET_CONFIGURATION_GUIDE.md](PYPI_SECRET_CONFIGURATION_GUIDE.md)** - Detailed step-by-step guide

### For Maintainers

- **[PYPI_PUBLICATION_GUIDE.md](../PYPI_PUBLICATION_GUIDE.md)** - Complete publication workflow
- **[PYPI_PREPARATION_SUMMARY.md](PYPI_PREPARATION_SUMMARY.md)** - Preparation checklist
- **[PYPI_ERROR_403_FIX.md](PYPI_ERROR_403_FIX.md)** - Troubleshooting authentication errors

## 🚀 Quick Start

### First Time Setup

1. Read [PYPI_SECRET_CONFIGURATION_GUIDE.md](PYPI_SECRET_CONFIGURATION_GUIDE.md)
2. Configure your PyPI API token as GitHub secret
3. Done! Future releases will be automatic

### Publishing a New Version

1. Update version in `src/flac_detective/__version__.py`
2. Run `python scripts/update_version.py`
3. Update `CHANGELOG.md`
4. Create and push tag: `git tag -a v0.X.X -m "Release v0.X.X"`
5. GitHub Actions will automatically publish to PyPI

## 🔗 Related Documentation

- [Version Management](../VERSION_MANAGEMENT.md) - How to update versions
- [Main README](../../README.md) - Project overview
- [CHANGELOG](../../CHANGELOG.md) - Version history

---

**Last Updated**: December 12, 2025
