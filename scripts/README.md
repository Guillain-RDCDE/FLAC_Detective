# 🛠️ Scripts

Utility scripts for testing, running, and releasing FLAC Detective.

## Release Management Scripts

### prepare_release.py
Automates the release preparation process.

**Usage**:
```bash
python scripts/prepare_release.py 0.9.0
python scripts/prepare_release.py 0.9.0 --release-name "Feature Name"
```

**What it does**:
- Updates version in `__version__.py` and `pyproject.toml`
- Updates release date automatically
- Validates CHANGELOG entry exists
- Provides step-by-step release instructions
- Shows changelog preview

**Example output**:
```
📦 Preparing release
   Current version: 0.8.0
   New version:     0.9.0

✅ Updated src/flac_detective/__version__.py
✅ Updated pyproject.toml
✅ CHANGELOG.md has entry for version 0.9.0

📋 Next steps:
1. Review changes: git diff
2. Commit: git commit -m "chore: Bump version to 0.9.0"
3. Tag: git tag -a v0.9.0 -m "Release v0.9.0"
4. Push: git push origin main v0.9.0
```

### validate_release.py
Validates release configuration before publishing.

**Usage**:
```bash
python scripts/validate_release.py
python scripts/validate_release.py --version 0.9.0
```

**What it checks**:
- ✅ Version consistency across all files
- ✅ CHANGELOG.md format and completeness
- ✅ pyproject.toml required fields
- ✅ README.md existence and content
- ✅ Package structure

**Exit codes**:
- `0`: All validations passed
- `1`: Errors found (blocks release)

### validate_workflows.py
Validates GitHub Actions workflow YAML files.

**Usage**:
```bash
python scripts/validate_workflows.py
```

**What it checks**:
- ✅ YAML syntax correctness
- ✅ Required workflow fields (name, on, jobs)
- ✅ Job configuration (runs-on, steps)
- ✅ Reports job and step counts

**Example output**:
```
📋 Validating release.yml...
  ✅ Name: Release to PyPI
  ✅ Triggers: ['push']
  ✅ Jobs: 6 (validate, build, test-package, ...)
  ✅ release.yml is valid

Result: 5/5 workflows valid
✅ All workflows are valid!
```

## Coverage & Quality Scripts

### coverage_report.py
Generates comprehensive test coverage reports.

**Usage**:
```bash
python scripts/coverage_report.py
```

### validate_ci.py
Validates CI/CD configuration.

**Usage**:
```bash
python scripts/validate_ci.py
```

### setup_precommit.py
Sets up pre-commit hooks for code quality.

**Usage**:
```bash
python scripts/setup_precommit.py
```

## Usage Scripts

### run_detective.py
Main entry point for analyzing FLAC files.

**Usage**:
```bash
python scripts/run_detective.py <directory_or_file>
```

### run_windows.bat
Windows batch wrapper for easy execution.

## Testing & Demo Scripts

### analyze_single.py
Analyze a single FLAC file with detailed debug output.

**Usage**:
```bash
python scripts/analyze_single.py <flac_file>
```

### demo_text_report.py
Demonstrate text report generation.

### interactive_helper.py
Interactive helper for exploring analysis results.

### repair_flac.py
Utility for repairing FLAC files (for specific use cases).

### update_version.py
Update version numbers across the project.

---

## Release Process

For creating a new release, follow this workflow:

1. **Prepare**: `python scripts/prepare_release.py 0.9.0`
2. **Validate**: `python scripts/validate_release.py --version 0.9.0`
3. **Commit & Tag**:
   ```bash
   git add -A
   git commit -m "chore: Bump version to 0.9.0"
   git tag -a v0.9.0 -m "Release v0.9.0"
   git push origin main v0.9.0
   ```
4. **Monitor**: GitHub Actions will automatically build, test, and publish to PyPI

See [docs/RELEASE_GUIDE.md](../docs/RELEASE_GUIDE.md) for complete documentation.

---

**Note**: For production use, refer to the main README.md in the project root for installation and usage instructions.
