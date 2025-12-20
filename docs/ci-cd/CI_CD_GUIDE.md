# Continuous Integration & Testing Guide

## Overview

FLAC Detective uses GitHub Actions for comprehensive CI/CD with:
- **Multi-platform testing**: Linux, Windows, macOS
- **Multi-version Python support**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Automated code quality checks**: linting, type checking, security scanning
- **Coverage reporting**: Integrated with Codecov
- **Pre-commit hooks**: Automatic code formatting and validation

## CI Workflow Structure

### Test Matrix

The CI runs tests across **14 different environments**:

| OS | Python Versions |
|---|---|
| Ubuntu (Linux) | 3.8, 3.9, 3.10, 3.11, 3.12 |
| Windows | 3.8, 3.9, 3.10, 3.11, 3.12 |
| macOS | 3.9, 3.10, 3.11, 3.12 (3.8 not supported) |

### Jobs

#### 1. Test Job (`test`)

Runs on every combination of OS and Python version.

**Steps:**
1. **Checkout code**: Get the latest code from the repository
2. **Setup Python**: Install specified Python version
3. **Install system dependencies**: Platform-specific audio libraries
   - Linux: `libsndfile1` via apt-get
   - macOS: `libsndfile` via Homebrew
   - Windows: Bundled with soundfile package
4. **Install Python dependencies**: Install package with dev dependencies
5. **Run pre-commit hooks**: Format checking, linting, etc.
6. **Lint with flake8**: Check code style and catch common errors
7. **Type check with mypy**: Verify type annotations
8. **Run tests**: Execute pytest suite
9. **Coverage reporting** (Linux + Python 3.11 only):
   - Generate coverage report
   - Upload to Codecov
   - Archive HTML report as artifact

#### 2. Code Quality Job (`code-quality`)

Runs additional quality checks on Python 3.11/Ubuntu.

**Checks:**
- **Black**: Code formatting verification
- **isort**: Import statement ordering
- **Bandit**: Security vulnerability scanning
- **Safety**: Known vulnerability detection in dependencies

## Running Tests Locally

### Prerequisites

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Run All Checks (Like CI)

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Lint with flake8
flake8 src tests --count --statistics --show-source

# Type check with mypy
mypy src --config-file=pyproject.toml

# Run tests with coverage
pytest tests/ --cov=flac_detective --cov-report=term-missing --cov-report=html
```

### Quick Test Run

```bash
# Just run tests without coverage
pytest tests/ -v

# Run specific test file
pytest tests/test_analyzer.py -v

# Run tests matching a pattern
pytest tests/ -k "test_repair" -v
```

### Coverage Analysis

```bash
# Generate coverage report
pytest tests/ --cov=flac_detective --cov-report=html

# Open HTML report
# Linux/Mac
open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## Coverage Requirements

- **Minimum coverage**: 80%
- **Branch coverage**: Enabled
- **Coverage report**: Generated for every test run
- **Excluded from coverage**:
  - Test files (`*/tests/*`)
  - `if __name__ == "__main__"` blocks
  - Abstract methods
  - Type checking blocks (`if TYPE_CHECKING:`)

### Coverage Configuration

Located in [pyproject.toml](../pyproject.toml:139-162):

```toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
fail_under = 80
```

## Pre-commit Hooks

Pre-commit hooks automatically run before each commit to maintain code quality.

### Installed Hooks

See [.pre-commit-config.yaml](../.pre-commit-config.yaml) for the full configuration.

**Standard Hooks:**
- `trailing-whitespace`: Remove trailing spaces
- `end-of-file-fixer`: Ensure files end with newline
- `check-yaml`: Validate YAML syntax
- `check-added-large-files`: Prevent committing large files

**Python Hooks:**
- `black`: Auto-format Python code
- `isort`: Sort and organize imports
- `flake8`: Lint Python code
- `mypy`: Type checking

### Manual Pre-commit Usage

```bash
# Run all hooks on staged files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Update hook versions
pre-commit autoupdate

# Skip hooks for a commit (use sparingly!)
git commit --no-verify
```

## Codecov Integration

Coverage reports are automatically uploaded to [Codecov](https://codecov.io) for tracking coverage trends.

### Setup (First Time)

1. **Get Codecov Token**:
   - Go to https://codecov.io
   - Sign in with GitHub
   - Add your repository
   - Copy the upload token

2. **Add Token to GitHub Secrets**:
   - Go to repository Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: Paste your Codecov token
   - Click "Add secret"

3. **Verify Setup**:
   - Push a commit or create a PR
   - Check GitHub Actions for successful upload
   - Visit Codecov dashboard to see reports

### Coverage Badges

Add coverage badge to README:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/flac-detective/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/flac-detective)
```

## Linting Configuration

### Flake8

Configuration in [.flake8](../.flake8):

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,build,dist,.venv
max-complexity = 10
```

**Key Settings:**
- Line length: 100 characters (matches Black)
- Ignores: E203 (whitespace before ':'), W503 (line break before operator)
- Complexity: Max McCabe complexity of 10

### MyPy

Configuration in [pyproject.toml](../pyproject.toml:98-119):

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
strict_equality = true
ignore_missing_imports = true
```

**Type Checking Level:**
- Partial type checking enabled
- Not enforcing full type coverage (`disallow_untyped_defs = false`)
- Gradual migration to stricter typing

## Troubleshooting CI Failures

### Common Issues

#### 1. Flake8 Errors

```bash
# Fix automatically with black and isort
black src tests
isort src tests

# Check what would be fixed
black --check src tests
isort --check-only src tests
```

#### 2. MyPy Type Errors

```bash
# Run mypy locally to see detailed errors
mypy src --config-file=pyproject.toml

# Add type ignore for unavoidable issues
variable: Any = some_function()  # type: ignore[assignment]
```

#### 3. Test Failures

```bash
# Run with verbose output
pytest tests/ -vv

# Run with full traceback
pytest tests/ --tb=long

# Run specific failing test
pytest tests/test_file.py::test_function -vv
```

#### 4. Coverage Below Threshold

```bash
# See which files need more coverage
pytest tests/ --cov=flac_detective --cov-report=term-missing

# Focus on files with low coverage
# Add tests for uncovered code paths
```

#### 5. Pre-commit Hook Failures

```bash
# See which hook failed
pre-commit run --all-files

# Fix issues manually, then
git add .
git commit
```

## Platform-Specific Notes

### Windows

- Uses backslashes in paths: Ensure path handling is cross-platform
- Line endings: CRLF vs LF (handled by `.gitattributes`)
- Case-insensitive filesystem: Be careful with file naming

### macOS

- Python 3.8 not available on latest runners
- Uses Homebrew for system dependencies
- Case-sensitive filesystem by default (but not always)

### Linux (Ubuntu)

- Primary development/testing platform
- apt-get for system dependencies
- Most reliable for CI/CD

## Best Practices

### 1. Run Tests Before Pushing

```bash
# Quick check
pytest tests/ -v

# Full CI-like check
pre-commit run --all-files && pytest tests/ --cov=flac_detective
```

### 2. Keep Dependencies Updated

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package-name
```

### 3. Write Platform-Agnostic Code

```python
# ✅ Good - cross-platform
from pathlib import Path
path = Path("data") / "file.txt"

# ❌ Bad - platform-specific
path = "data\\file.txt"  # Windows only
path = "data/file.txt"   # Unix only
```

### 4. Add Tests for Bug Fixes

```python
# When fixing a bug, add a test that would have caught it
def test_regression_issue_123():
    """Ensure issue #123 doesn't happen again."""
    result = function_that_had_bug()
    assert result == expected_value
```

### 5. Monitor CI Performance

- Check GitHub Actions tab regularly
- Review failed runs to spot patterns
- Optimize slow tests if CI takes too long

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Codecov Documentation](https://docs.codecov.com/)
- [Pre-commit Framework](https://pre-commit.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Flake8 Rules](https://flake8.pycqa.org/en/latest/user/error-codes.html)
- [MyPy Documentation](https://mypy.readthedocs.io/)
