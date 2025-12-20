# Release Guide

This guide explains how to create and publish new releases of FLAC Detective to PyPI.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Release Process Overview](#release-process-overview)
- [Step-by-Step Guide](#step-by-step-guide)
- [Automated Release Workflow](#automated-release-workflow)
- [Troubleshooting](#troubleshooting)
- [Release Checklist](#release-checklist)

## Prerequisites

Before creating a release, ensure you have:

1. **Write access** to the GitHub repository
2. **PyPI API Token** configured as GitHub secret `PYPI_API_TOKEN`
3. **All tests passing** on the main branch
4. **CHANGELOG.md updated** with release notes

### Setting Up PyPI API Token

The PyPI API token must be configured as a GitHub secret:

1. Generate a PyPI API token at https://pypi.org/manage/account/token/
2. Add it to GitHub repository secrets as `PYPI_API_TOKEN`
3. The token should have upload permissions for the `flac-detective` package

See [docs/pypi/PYPI_SECRET_CONFIGURATION_GUIDE.md](pypi/PYPI_SECRET_CONFIGURATION_GUIDE.md) for detailed instructions.

## Release Process Overview

The release process is **fully automated** using GitHub Actions. When you push a version tag:

1. **Validation** - Version consistency and changelog checks
2. **Build** - Package built and validated with `twine check`
3. **Test** - Package installed and tested on multiple platforms
4. **Publish** - Published to PyPI using trusted publishing
5. **Release** - GitHub release created with changelog and artifacts

## Step-by-Step Guide

### 1. Prepare the Release

Use the automated preparation script:

```bash
# Update version to 0.9.0
python scripts/prepare_release.py 0.9.0 --release-name "Enhanced Spectral Analysis"
```

This script will:
- Update `src/flac_detective/__version__.py`
- Update `pyproject.toml`
- Validate CHANGELOG.md has an entry for the new version
- Provide next steps

### 2. Update CHANGELOG.md

Ensure CHANGELOG.md has a properly formatted entry:

```markdown
## [0.9.0] - 2025-12-20

### Added
- New feature 1
- New feature 2

### Changed
- Change 1

### Fixed
- Bug fix 1
```

**Important**: The version must exactly match the version in `__version__.py` and `pyproject.toml`.

### 3. Validate the Release

Run validation checks before committing:

```bash
python scripts/validate_release.py --version 0.9.0
```

This will check:
- Version consistency across all files
- CHANGELOG.md format and content
- pyproject.toml required fields
- Package structure

Fix any errors before proceeding.

### 4. Commit and Tag

Commit the version bump:

```bash
git add -A
git commit -m "chore: Bump version to 0.9.0"
```

Create and push the tag:

```bash
# Create annotated tag
git tag -a v0.9.0 -m "Release v0.9.0"

# Push commit and tag
git push origin main
git push origin v0.9.0
```

**Important**: The tag must start with `v` (e.g., `v0.9.0`).

### 5. Monitor the Release

The GitHub Actions workflow will automatically:

1. **Validate** (1-2 min)
   - Check version consistency
   - Extract changelog
   - Validate CHANGELOG entry

2. **Build** (1-2 min)
   - Build wheel and source distribution
   - Run `twine check`
   - Upload artifacts

3. **Test Package** (3-5 min)
   - Test installation on Ubuntu, Windows, macOS
   - Test Python 3.8 and 3.11
   - Verify CLI and imports work

4. **Publish to PyPI** (1-2 min)
   - Publish to https://pypi.org/project/flac-detective/

5. **Create GitHub Release** (1 min)
   - Create release with changelog
   - Attach distribution files
   - Add checksums

Monitor the workflow at:
```
https://github.com/GuillainM/FLAC_Detective/actions
```

### 6. Verify the Release

After successful deployment:

1. **Check PyPI**: https://pypi.org/project/flac-detective/
2. **Check GitHub Release**: https://github.com/GuillainM/FLAC_Detective/releases
3. **Test installation**:
   ```bash
   pip install --upgrade flac-detective
   flac-detective --version
   ```

## Automated Release Workflow

The release workflow ([.github/workflows/release.yml](.github/workflows/release.yml)) includes:

### Jobs

1. **validate** - Pre-flight checks
   - Version consistency validation
   - CHANGELOG extraction
   - Date validation

2. **build** - Package building
   - Build wheel and sdist
   - Run `twine check`
   - Upload artifacts

3. **test-package** - Installation testing
   - Matrix: Ubuntu/Windows/macOS × Python 3.8/3.11
   - Test CLI entry point
   - Test Python imports

4. **publish-pypi** - PyPI publication
   - Uses trusted publishing (OIDC)
   - Requires `PYPI_API_TOKEN` secret
   - Prints checksums

5. **create-github-release** - GitHub release
   - Extracts changelog for version
   - Adds installation instructions
   - Attaches distribution files
   - Includes SHA256 checksums

6. **notify** - Post-release summary
   - Creates workflow summary
   - Lists all links

### Security Features

- **Trusted Publishing**: Uses PyPI's OIDC provider (no long-lived tokens in repos)
- **Multi-platform Testing**: Validates on all major platforms before release
- **Checksum Verification**: SHA256 checksums in release notes
- **Version Validation**: Prevents mismatched versions

## Troubleshooting

### Version Mismatch Error

**Error**: "Tag version doesn't match pyproject.toml"

**Solution**: Ensure all version files are updated:
```bash
# Use the prepare script
python scripts/prepare_release.py 0.9.0

# Or manually update:
# - src/flac_detective/__version__.py
# - pyproject.toml
```

### Missing CHANGELOG Entry

**Error**: "No CHANGELOG.md entry found for version X"

**Solution**: Add a properly formatted entry:
```markdown
## [0.9.0] - 2025-12-20

### Added
- Feature description
```

### PyPI Upload Failure

**Error**: "403 Forbidden" or authentication error

**Solution**:
1. Verify `PYPI_API_TOKEN` secret is set correctly
2. Check token has upload permissions
3. See [PYPI_SECRET_CONFIGURATION_GUIDE.md](pypi/PYPI_SECRET_CONFIGURATION_GUIDE.md)

### Package Test Failure

**Error**: Installation or import tests fail

**Solution**:
1. Test locally first:
   ```bash
   python -m build
   pip install dist/*.whl
   flac-detective --version
   ```
2. Check dependencies in `pyproject.toml`
3. Verify `__init__.py` exports

### Workflow Permission Error

**Error**: "Resource not accessible by integration"

**Solution**: Check GitHub repository settings:
- Settings → Actions → General
- Workflow permissions: "Read and write permissions"
- Allow GitHub Actions to create releases

## Release Checklist

Use this checklist for each release:

### Pre-Release
- [ ] All tests passing on main branch
- [ ] Code review completed for all changes
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with version entry
- [ ] Version bumped in all files (`prepare_release.py`)
- [ ] Validation passed (`validate_release.py`)

### Release
- [ ] Changes committed to main
- [ ] Git tag created (`git tag -a vX.Y.Z`)
- [ ] Tag pushed (`git push origin vX.Y.Z`)
- [ ] GitHub Actions workflow started

### Post-Release
- [ ] Workflow completed successfully
- [ ] PyPI package visible and installable
- [ ] GitHub release created with changelog
- [ ] Installation tested: `pip install --upgrade flac-detective`
- [ ] CLI tested: `flac-detective --version`
- [ ] Release announced (if applicable)

## Version Numbering

FLAC Detective follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (0.x.0): Breaking changes
- **MINOR** (x.1.0): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

Examples:
- `0.8.0` → `0.8.1`: Bug fix
- `0.8.0` → `0.9.0`: New feature
- `0.9.0` → `1.0.0`: Major milestone, breaking changes

## Emergency Hotfix

For critical bugs requiring immediate release:

1. **Create hotfix branch**:
   ```bash
   git checkout -b hotfix/0.8.1 v0.8.0
   ```

2. **Fix the bug** and commit

3. **Prepare release**:
   ```bash
   python scripts/prepare_release.py 0.8.1
   ```

4. **Merge to main** and tag:
   ```bash
   git checkout main
   git merge hotfix/0.8.1
   git tag -a v0.8.1 -m "Hotfix: Critical bug fix"
   git push origin main v0.8.1
   ```

## Additional Resources

- [PyPI Secret Setup Guide](pypi/PYPI_SECRET_SETUP.md)
- [PyPI Error Troubleshooting](pypi/PYPI_ERROR_403_FIX.md)
- [Version Management](VERSION_MANAGEMENT.md)
- [Contributing Guide](development/CONTRIBUTING.md)

## Support

For release issues:
1. Check [GitHub Actions logs](https://github.com/GuillainM/FLAC_Detective/actions)
2. Review [PyPI project page](https://pypi.org/project/flac-detective/)
3. Open an issue: https://github.com/GuillainM/FLAC_Detective/issues
