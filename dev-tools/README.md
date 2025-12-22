# Development Tools

This directory contains development and maintenance tools for FLAC Detective.

## Directory Structure

```
dev-tools/
├── build-scripts/        # Build and packaging scripts
│   ├── build_package.bat
│   └── test_coverage.bat
├── launch-docs/          # Launch preparation documentation
│   ├── FINAL_STATUS.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── PRE_LAUNCH_CHECKLIST.md
│   └── RELEASE_NOTES_v0.9.6.md
├── examples/             # Internal development examples
├── tools/                # Utility scripts
├── CODECOV_*.md          # Codecov integration documentation
└── check_codecov_status.py
```

## Purpose

These tools are for:
- **Development**: Internal development scripts and utilities
- **Build/Release**: Package building and release preparation
- **Documentation**: Launch preparation and status tracking
- **CI/CD**: Integration and deployment tools

## Not for End Users

This directory is excluded from PyPI distribution (see `MANIFEST.in` at project root).

End users should refer to the main project documentation and examples:
- [README.md](../README.md)
- [docs/](../docs/)
- [examples/](../examples/)
