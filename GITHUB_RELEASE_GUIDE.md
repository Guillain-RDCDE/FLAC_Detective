# GitHub Release Guide - v0.5.0

## Pre-Release Checklist

### 1. Verify All Changes

```bash
# Check git status
git status

# Review changes
git diff
```

### 2. Run All Tests

```bash
# Run test suite
pytest tests/ -v

# Check coverage
pytest --cov=flac_detective --cov-report=html

# Verify all tests pass
```

### 3. Code Quality Checks

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint check
flake8 src/ tests/

# Type check
mypy src/
```

## Release Steps

### Step 1: Commit All Changes

```bash
# Add all files
git add .

# Commit with descriptive message
git commit -m "Release v0.5.0 - Nyquist Guardian

Major improvements:
- Added Nyquist exception system (R8) with 95% and 90% thresholds
- Enhanced vinyl detection with 3-phase analysis (R7)
- Added compression artifacts detection (R9)
- Added multi-segment consistency check (R10)
- Fixed critical short-circuit bug
- 80% performance improvement
- Eliminated 37 false positives
- Achieved 79.2% authentic detection rate

See CHANGELOG.md and RELEASE_NOTES_v0.5.0.md for details."
```

### Step 2: Create Git Tag

```bash
# Create annotated tag
git tag -a v0.5.0 -m "Release v0.5.0 - Nyquist Guardian

Production-ready release with:
- 79.2% authentic detection rate
- < 0.5% false positive rate
- 80% performance improvement
- 12-rule detection system
- Comprehensive documentation"

# Verify tag
git tag -l -n9 v0.5.0
```

### Step 3: Push to GitHub

```bash
# Push commits
git push origin main

# Push tags
git push origin v0.5.0
```

### Step 4: Create GitHub Release

1. Go to: https://github.com/GuillainM/FLAC_Detective/releases/new

2. **Tag**: Select `v0.5.0`

3. **Release Title**: `v0.5.0 - Nyquist Guardian (Production Ready)`

4. **Description**: Copy from `RELEASE_NOTES_v0.5.0.md` or use this template:

```markdown
# 🎯 FLAC Detective v0.5.0 - Production Ready

## Major Achievement
- **79.2% authentic detection rate** (target: > 75%)
- **2.2% fake detection rate** with near-zero false positives (< 0.5%)
- **80% performance improvement** (10 hours → 1h45 for 759 files)

## 🚀 What's New

### Nyquist Exception System (Rule 8)
- 95% Nyquist threshold for global protection
- 90% Nyquist threshold for MP3 320 kbps specific protection
- **Impact**: Eliminated 37 false positives

### Enhanced Vinyl Detection (Rule 7)
- 3-phase analysis: Dither → Vinyl noise → Clicks & pops
- Accurate identification of authentic vinyl sources

### Compression Artifacts Detection (Rule 9)
- Pre-echo detection (MDCT ghosting)
- High-frequency aliasing detection
- MP3 quantization noise patterns

### Multi-Segment Consistency (Rule 10)
- Validates anomalies across 5 file segments
- Distinguishes dynamic mastering from transcoding

### Performance Optimizations
- Smart short-circuits (~70% reduction)
- Progressive analysis (~17% reduction)
- Parallel execution (~6% reduction)
- File read cache (~3% reduction)

## 🐛 Critical Fixes
- **Short-circuit bug**: R8 now calculated FIRST
- **21 kHz false positives**: 95% Nyquist exception
- **20.2-20.8 kHz zone**: 90% Nyquist exception for 320k
- **320 kbps range**: Widened to (700, 1050) kbps

## 📚 Documentation
- Complete changelog
- Technical documentation
- Rule specifications
- Performance guide

## 📦 Installation

```bash
pip install flac-detective
```

## 🔗 Links
- [Changelog](CHANGELOG.md)
- [Release Notes](RELEASE_NOTES_v0.5.0.md)
- [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md)
- [README](README.md)

---

**Full Changelog**: https://github.com/GuillainM/FLAC_Detective/compare/v0.2.0...v0.5.0
```

5. **Assets**: Attach any additional files if needed

6. **Pre-release**: ☐ (uncheck - this is a production release)

7. **Set as latest release**: ☑ (check)

8. Click **Publish release**

## Post-Release

### Step 1: Verify Release

- Check release page: https://github.com/GuillainM/FLAC_Detective/releases/tag/v0.5.0
- Verify all links work
- Check that tag is visible

### Step 2: Update Documentation

- Ensure README badges are up to date
- Update any external documentation links

### Step 3: Announce Release (Optional)

- Create discussion post on GitHub
- Share on relevant communities
- Update project website if applicable

## PyPI Release (Optional)

### Build Package

```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# Check distribution
twine check dist/*
```

### Upload to PyPI

```bash
# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ flac-detective

# Upload to production PyPI
twine upload dist/*
```

## Troubleshooting

### Tag Already Exists

```bash
# Delete local tag
git tag -d v0.5.0

# Delete remote tag
git push origin :refs/tags/v0.5.0

# Recreate tag
git tag -a v0.5.0 -m "..."
git push origin v0.5.0
```

### Failed Push

```bash
# Pull latest changes
git pull origin main --rebase

# Push again
git push origin main
git push origin v0.5.0
```

### Release Notes Too Long

- Use summary in GitHub release
- Link to full RELEASE_NOTES_v0.5.0.md
- Keep critical information visible

## Checklist

- [ ] All tests passing
- [ ] Code quality checks passed
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG.md updated
- [ ] RELEASE_NOTES created
- [ ] README.md updated
- [ ] Documentation complete
- [ ] Changes committed
- [ ] Tag created (v0.5.0)
- [ ] Pushed to GitHub
- [ ] GitHub release created
- [ ] Release verified
- [ ] Documentation links checked
- [ ] (Optional) PyPI package published
- [ ] (Optional) Announcement made

---

**FLAC Detective v0.5.0 Release Guide**  
**Last Updated: December 4, 2025**
