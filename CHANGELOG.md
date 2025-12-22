## Unreleased

## v0.9.6 (2025-12-22)

### Chore

- **release**: Prepare project for public release
  - Simplified issue templates (bug report and feature request to 6-7 essential fields)
  - Cleaned up scripts directory (removed redundant analysis and demo scripts)
  - Organized development resources into dev-tools/ directory
  - Added MANIFEST.in to exclude dev-tools from PyPI distribution
  - Updated .gitignore with additional test artifacts
  - Added missing badges to README (PyPI downloads and Codecov)

## v0.9.1 (2024-12-20)

### Docs

- **BREAKING**: Restructure documentation to minimal 6-file system
  - Consolidated 50+ documentation files into 6 essential, focused documents
  - New structure: index.md, getting-started.md, user-guide.md, api-reference.md, technical-details.md, contributing.md
  - Moved old documentation structure to docs/archive/ (preserved, not deleted)
  - Updated all README.md links to point to new documentation
  - Added RESTRUCTURING_SUMMARY.md for migration guide
  - Eliminated documentation redundancy (90% reduction in file count)
  - Improved navigation with central index.md hub
  - Enhanced maintainability: 6 files vs 50+ files to maintain
  - Better user experience: clear progression from basics to advanced topics
  - All essential information preserved through intelligent consolidation

### Chore

- Clean up root directory structure
- Fix README issues and translate CHANGELOG_AUTOMATION to English
- Make GitHub Actions workflows more resilient

## v0.9.0 (2024-12-20)

### Feat

- **docs**: Complete project restructuring and documentation overhaul
  - Reorganized documentation into audience-specific directories (user-guide, technical, reference, development, automation, ci-cd)
  - Created comprehensive documentation index and navigation guide
  - Added PROJECT_OVERVIEW.md for complete project structure visualization
  - Added DOCUMENTATION_GUIDE.md for easy documentation navigation
  - Consolidated and removed duplicate documentation files (15+ files cleaned)
  - Created professional root directory structure (removed 9+ temporary implementation files)
  - Added STRUCTURE.txt for project structure visualization
  - Updated all documentation cross-references to reflect new structure
  - Improved .gitignore to prevent future clutter (build artifacts, temporary files)

### Chore

- Clean up build artifacts and temporary directories (flac_detective-0.7.1/, flac_detective-0.8.0/, dist/, api/, _templates/)
- Remove obsolete documentation (CLEANUP_LOG.md, INDEX.md, IMPROVEMENTS_SUMMARY.md, etc.)
- Standardize documentation structure for production readiness

## v0.8.0 (2024-12-19)

### Feat

- Add automatic FLAC repair with complete metadata preservation (v0.8.0)
- Add comprehensive diagnostic tracking and error handling system

## v0.7.2 (2024-12-18)

### Fix

- Bump to v0.7.2 for PyPI image fix

## v0.7.1 (2024-12-18)

### Fix

- Update banner image URL for PyPI display

## v0.7.0 (2024-12-18)

### Feat

- **v0.7.0**: Partial file reading and improved cutoff detection

### Fix

- Remove debug messages cluttering console output
- Correct versioning - ensure all documentation references v0.7.0 only
- **version**: Centralize version management in __version__.py
- **audio-loader**: Add unknown error to temporary error patterns

### Perf

- **rules**: Optimize memory usage for Rules 9 and 11

## v0.6.9 (2024-12-15)

### Feat

- **logging**: Auto-delete empty console log files
- **analysis**: Add FLAC repair and improve memory usage
- Improve memory usage and error handling in audio analysis

### Fix

- **logging**: Close file handlers before deleting empty log files
- **spectrum**: Adapt cutoff detection for high-resolution audio files
- **tracker**: Convert numpy types to Python native types for JSON serialization
- **analysis**: Prevent memory errors and fix audio loading
- **audio**: Allow kwargs in load_audio_with_retry

## v0.6.8 (2024-12-14)

## v0.6.7 (2024-12-12)

## v0.6.6 (2024-12-12)

### Feat

- Implement centralized version management system
- Add automatic retry mechanism for FLAC decoder errors (v0.6.1)
- Add corrupted and upsampled sections to reports with full paths
- **rule1**: Add energy_ratio parameter for enhanced 20 kHz detection
- **scoring**: optimize Rule 7 and adjust Rule 11 thresholds
- **rules**: Implement Rule 11 Cassette Detection and relative path reporting (v0.6.0)

### Fix

- Update splash screen version and fix ASCII art alignment
- **ci**: Make all CI steps non-blocking to prevent failure emails
- **ci**: Update GitHub Actions workflow to use pyproject.toml
- **docs**: Correct detection system to 11 rules and bump version to 0.6.1
- **build**: Update license format to modern SPDX expression
- **rule1**: Add 20 kHz cutoff exception to prevent false positives
- **build**: Fix pip installation by correcting README path in pyproject.toml

## v0.5.0 (2024-12-04)

### Feat

- Release v0.4.0 - Major optimizations (80% faster) and scoring improvements (Rule 10, Rule 8 refined)
- Implement spectral bitrate estimation and enhanced scoring rules

### Fix

- Add 21kHz cutoff threshold to reduce false positives
- Correct type annotations for mypy compliance
