# Pre-commit Hooks Setup Guide

This guide explains how to install and use pre-commit hooks for FLAC Detective to ensure code quality.

## What are Pre-commit Hooks?

Pre-commit hooks are automated checks that run **before** each git commit. They help maintain code quality by automatically:
- Formatting code (Black, isort)
- Checking code style (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Validating file syntax (YAML, TOML, JSON)
- And more!

## Installation

### 1. Install pre-commit

The `pre-commit` tool is already included in the dev dependencies. Install it with:

```bash
# If you haven't installed dev dependencies yet
pip install -e ".[dev]"

# Or install pre-commit separately
pip install pre-commit
```

### 2. Install the Git Hooks

Run this command in the repository root to install the hooks:

```bash
pre-commit install
```

This creates a `.git/hooks/pre-commit` script that runs automatically before each commit.

### 3. (Optional) Install commit-msg hooks

To also check commit messages:

```bash
pre-commit install --hook-type commit-msg
```

## Usage

### Automatic Execution

Once installed, the hooks run **automatically** every time you commit:

```bash
git add .
git commit -m "feat: Add new feature"
# Hooks run automatically here!
```

If any hook fails, the commit is **blocked** and you'll see which checks failed.

### Manual Execution

Run hooks on all files manually:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run a specific hook
pre-commit run black --all-files
pre-commit run flake8 --all-files
pre-commit run mypy --all-files

# Run hooks on specific files
pre-commit run --files src/flac_detective/main.py
```

### Skip Hooks (Emergency Only)

If you need to commit without running hooks (not recommended):

```bash
git commit --no-verify -m "Emergency fix"
```

⚠️ **Warning**: Only use `--no-verify` in emergencies. Your code should always pass the hooks!

## Configured Hooks

Our `.pre-commit-config.yaml` includes the following checks:

### 1. **File Checks** (pre-commit-hooks)
- ✅ Case conflict detection
- ✅ Large files prevention (>1MB)
- ✅ Merge conflict detection
- ✅ YAML/TOML/JSON syntax validation
- ✅ End-of-file fixer
- ✅ Trailing whitespace removal
- ✅ Python syntax validation
- ✅ Debugger statement detection
- ✅ Private key detection

### 2. **Black** - Code Formatting
- Automatically formats Python code to match the project style
- Line length: 100 characters
- Config: `[tool.black]` in `pyproject.toml`

### 3. **isort** - Import Sorting
- Organizes imports alphabetically and by category
- Compatible with Black
- Config: `[tool.isort]` in `pyproject.toml`

### 4. **flake8** - Code Linting
- Checks code style (PEP 8)
- Max line length: 100
- Additional plugins:
  - `flake8-docstrings`: Docstring style checking
  - `flake8-bugbear`: Bug and design problem detection
  - `flake8-comprehensions`: Better list/dict comprehensions
  - `flake8-simplify`: Code simplification suggestions

### 5. **mypy** - Type Checking
- Static type checking for Python
- Config: `[tool.mypy]` in `pyproject.toml`
- Excludes tests

### 6. **bandit** - Security Scanning
- Scans for common security issues
- Skips false positives (B101: assert_used, B601: shell injection)

### 7. **interrogate** - Docstring Coverage
- Ensures adequate documentation
- Minimum coverage: 80%
- Ignores: private/magic methods, init methods

### 8. **safety** - Dependency Security
- Checks for known vulnerabilities in dependencies
- Scans `pyproject.toml`

### 9. **validate-pyproject** - Project Configuration
- Validates `pyproject.toml` syntax and structure

## Updating Hooks

Pre-commit hooks should be updated regularly to get the latest versions:

```bash
# Update all hooks to latest versions
pre-commit autoupdate

# Review the changes in .pre-commit-config.yaml
git diff .pre-commit-config.yaml
```

## Troubleshooting

### Hooks fail on first run

This is normal! Run the failing hook manually to see details:

```bash
pre-commit run <hook-name> --all-files
```

Example:
```bash
pre-commit run black --all-files
```

### Black and flake8 conflicts

Our configuration is already set up to avoid conflicts:
- Both use 100 character line length
- flake8 ignores E203, W503, E501 (Black-compatible)

### mypy type errors

If mypy fails:
1. Check the error message
2. Add type hints where needed
3. For third-party libraries without types, add to `ignore_missing_imports` in `pyproject.toml`

### Interrogate fails (low docstring coverage)

If docstring coverage is below 80%:
1. Add docstrings to public functions/classes
2. Or adjust `--fail-under` in `.pre-commit-config.yaml`

### Skip specific hooks temporarily

Edit `.pre-commit-config.yaml` and comment out the hook you want to skip:

```yaml
# - repo: https://github.com/pre-commit/mirrors-mypy
#   rev: v1.11.2
#   hooks:
#     - id: mypy
```

Then run:
```bash
pre-commit install --overwrite
```

## Best Practices

1. **Run hooks before committing large changes**:
   ```bash
   pre-commit run --all-files
   ```

2. **Fix issues incrementally**: Don't try to fix all files at once

3. **Read the error messages**: Hooks provide helpful suggestions

4. **Update regularly**: Keep hooks up-to-date with `pre-commit autoupdate`

5. **Never commit with `--no-verify`** unless it's a genuine emergency

## CI/CD Integration

Pre-commit hooks can also run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run pre-commit
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)

## Summary

With pre-commit hooks installed:
- ✅ Code is automatically formatted on commit
- ✅ Style issues are caught before they enter the codebase
- ✅ Type errors are detected early
- ✅ Security issues are flagged
- ✅ Documentation coverage is maintained
- ✅ Code quality remains consistently high

**Installation command**:
```bash
pip install pre-commit && pre-commit install
```

That's it! Your commits will now be automatically checked for quality issues.
