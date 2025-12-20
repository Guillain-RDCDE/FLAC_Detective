# Code Coverage Setup Guide

This guide explains how to generate, view, and maintain code coverage reports for FLAC Detective.

## 📊 What is Code Coverage?

Code coverage measures what percentage of your code is executed during tests. It helps identify:
- ✅ Well-tested code paths
- ❌ Untested code that needs more tests
- 🔍 Dead code that can be removed
- 🎯 Critical paths that need better testing

## 🎯 Coverage Goals

FLAC Detective maintains **minimum 80% code coverage**:
- ✅ **Project-wide**: 80% minimum (enforced in CI/CD)
- ✅ **New code**: 80% minimum for new features
- ✅ **Critical paths**: 90%+ for core analysis logic

## 🚀 Quick Start

### Generate Coverage Report Locally

```bash
# Run tests with coverage
pytest --cov=flac_detective --cov-report=html --cov-report=term-missing

# Open HTML report in browser
# Windows:
start htmlcov/index.html
# Linux/macOS:
open htmlcov/index.html
```

### Using Makefile

```bash
# Run tests with coverage report
make test-cov

# View coverage report (automatically opens in browser)
```

## 📋 Coverage Configuration

### Location: `pyproject.toml`

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=flac_detective",      # Module to measure
    "--cov-report=term-missing",  # Show missing lines in terminal
    "--cov-report=html",          # Generate HTML report
    "--cov-report=xml",           # Generate XML for Codecov
]

[tool.coverage.run]
source = ["src"]                  # Source directories
branch = true                     # Measure branch coverage
omit = [
    "*/tests/*",                  # Exclude test files
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
precision = 2                     # 2 decimal places
show_missing = true               # Show line numbers
fail_under = 80                   # Fail if below 80%
exclude_lines = [
    "pragma: no cover",           # Manual exclusions
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

## 🌐 Codecov Integration

### What is Codecov?

[Codecov](https://codecov.io/) provides:
- 📊 Visual coverage reports
- 📈 Coverage trends over time
- 💬 Automatic PR comments
- 🎯 Coverage diff on pull requests
- 🏆 Team coverage insights

### Setup Codecov (for maintainers)

1. **Sign up**: Go to [codecov.io](https://codecov.io/) and sign in with GitHub

2. **Add repository**: Enable FLAC_Detective repository

3. **Get token**: Copy the Codecov token from repository settings

4. **Add to GitHub Secrets**:
   - Go to GitHub repository settings
   - Navigate to Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: Paste your Codecov token
   - Click "Add secret"

5. **Verify**: Push a commit and check that the CI workflow uploads coverage

### Codecov Configuration

Location: `codecov.yml`

```yaml
coverage:
  status:
    project:
      default:
        target: 80%           # Minimum coverage
        threshold: 2%         # Allow 2% drop

    patch:
      default:
        target: 80%           # New code coverage
```

## 📈 Reading Coverage Reports

### Terminal Output

After running tests, you'll see:

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src/flac_detective/main.py                45      5    89%   67-71
src/flac_detective/analysis/rules.py      120     12   90%   45, 78-82
---------------------------------------------------------------------
TOTAL                                     850     68    92%
```

**Columns**:
- **Stmts**: Total statements
- **Miss**: Statements not executed
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

### HTML Report

The HTML report (`htmlcov/index.html`) provides:
- ✅ File-by-file coverage breakdown
- 🔍 Interactive source code viewer
- 🎨 Color-coded coverage (green = covered, red = not covered)
- 📊 Visual coverage bars

**Navigation**:
1. Open `htmlcov/index.html`
2. Click on a file name to see detailed coverage
3. Red-highlighted lines are not covered by tests
4. Green-highlighted lines are covered

### XML Report

The XML report (`coverage.xml`) is used by:
- Codecov for online reporting
- CI/CD pipelines
- IDE integrations (e.g., VSCode coverage extensions)

## 🎯 Improving Coverage

### 1. Find Uncovered Code

```bash
# Run coverage with missing lines
pytest --cov=flac_detective --cov-report=term-missing

# Look for "Missing" column
```

### 2. Write Tests for Uncovered Lines

Example: If `audio_loader.py:45-50` is uncovered:

```python
# tests/test_audio_loader.py
def test_error_handling():
    """Test that covers lines 45-50."""
    with pytest.raises(ValueError):
        load_audio_with_retry("nonexistent.flac")
```

### 3. Verify Improvement

```bash
# Run tests again
pytest --cov=flac_detective --cov-report=term-missing

# Check that lines 45-50 are now covered
```

### 4. Exclude Untestable Code (if necessary)

If code is genuinely untestable (e.g., defensive programming):

```python
def process_file(path: str) -> None:
    try:
        # Normal processing
        pass
    except Exception as e:  # pragma: no cover
        # This exception should never happen in practice
        logger.critical(f"Unexpected error: {e}")
        raise
```

## 🔧 Coverage Tools & Commands

### Basic Commands

```bash
# Run tests with coverage
pytest --cov=flac_detective

# Generate HTML report
pytest --cov=flac_detective --cov-report=html

# Generate terminal report with missing lines
pytest --cov=flac_detective --cov-report=term-missing

# Generate XML for Codecov
pytest --cov=flac_detective --cov-report=xml

# Fail if coverage below 80%
pytest --cov=flac_detective --cov-fail-under=80
```

### Advanced Commands

```bash
# Coverage for specific module
pytest tests/test_rules.py --cov=flac_detective.analysis.rules

# Skip coverage for faster testing
pytest --no-cov

# Coverage with branch coverage
pytest --cov=flac_detective --cov-branch

# Combine multiple coverage runs
coverage combine
coverage report
```

### Makefile Shortcuts

```bash
make test           # Run tests (with coverage)
make test-cov       # Run tests with HTML coverage report
make test-unit      # Run unit tests with coverage
```

## 🎭 Coverage vs. Quality

### Coverage is NOT a Quality Metric

⚠️ **Important**: 100% coverage doesn't mean bug-free code!

**Good coverage**:
```python
def add(a: int, b: int) -> int:
    return a + b

# Test
def test_add():
    assert add(2, 3) == 5      # ✅ Tests the happy path
    assert add(-1, 1) == 0     # ✅ Tests edge case
    assert add(0, 0) == 0      # ✅ Tests zero
```

**Bad coverage** (high coverage, low quality):
```python
def divide(a: int, b: int) -> float:
    return a / b

# Test
def test_divide():
    divide(10, 2)  # ❌ No assertions! Test passes but validates nothing
```

### Focus on Meaningful Tests

- ✅ Test business logic thoroughly
- ✅ Test edge cases and error conditions
- ✅ Test integration points
- ❌ Don't write tests just to increase coverage
- ❌ Don't test trivial code (getters/setters)

## 📊 Coverage Badges

### README Badges

Our README includes coverage badges:

```markdown
[![codecov](https://codecov.io/gh/GuillainM/FLAC_Detective/branch/main/graph/badge.svg)](https://codecov.io/gh/GuillainM/FLAC_Detective)
```

### Badge Meanings

- 🟢 **Green (>80%)**: Good coverage
- 🟡 **Yellow (70-80%)**: Acceptable, needs improvement
- 🔴 **Red (<70%)**: Poor coverage, action required

## 🔄 CI/CD Integration

### GitHub Actions Workflow

Location: `.github/workflows/ci.yml`

```yaml
- name: Test with pytest and coverage
  run: |
    pytest tests/ --cov=flac_detective --cov-report=xml --cov-fail-under=80

- name: Upload coverage reports to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

### Coverage in Pull Requests

When you open a PR, Codecov will:
1. ✅ Comment with coverage diff
2. 📊 Show which files changed coverage
3. 🎯 Highlight uncovered lines in new code
4. ❌ Fail if coverage drops below threshold

## 🛠️ Troubleshooting

### Coverage Not Generated

**Problem**: No `coverage.xml` or `htmlcov/` folder

**Solution**:
```bash
# Ensure coverage is installed
pip install pytest-cov

# Run with explicit coverage flags
pytest --cov=flac_detective --cov-report=html
```

### Coverage Too Low

**Problem**: Tests pass but coverage is below 80%

**Solution**:
1. Check `htmlcov/index.html` to see which files are uncovered
2. Write tests for uncovered code
3. Or add `# pragma: no cover` for untestable code

### Codecov Upload Fails

**Problem**: CI fails at "Upload coverage to Codecov" step

**Solution**:
1. Verify `CODECOV_TOKEN` is set in GitHub secrets
2. Check that `coverage.xml` was generated
3. Review Codecov documentation for API changes

### Inaccurate Coverage

**Problem**: Coverage shows 100% but code isn't tested

**Solution**:
- Ensure you're using `--cov-branch` for branch coverage
- Check that test assertions actually validate behavior
- Review test quality, not just line coverage

## 📚 Best Practices

### 1. Write Tests First (TDD)

```bash
# Write test
# tests/test_new_feature.py
def test_new_feature():
    assert new_feature() == expected

# Run test (fails)
pytest tests/test_new_feature.py

# Implement feature
# src/flac_detective/new_feature.py
def new_feature():
    return expected

# Run test (passes with coverage)
pytest tests/test_new_feature.py --cov
```

### 2. Aim for Meaningful Coverage

- Focus on testing **behavior**, not just **lines**
- Test edge cases and error conditions
- Test integration between components

### 3. Review Coverage Regularly

```bash
# Weekly coverage check
make test-cov

# Review uncovered files
open htmlcov/index.html
```

### 4. Maintain Coverage in PRs

- Don't merge PRs that reduce coverage
- Add tests for new features
- Update tests when modifying existing code

### 5. Use Coverage to Find Dead Code

- Code with 0% coverage might be unused
- Consider removing or documenting why it's not tested

## 📈 Coverage Metrics

### Current Status

- **Target**: 80% minimum
- **Branch Coverage**: Enabled
- **CI Enforcement**: Yes (fails below 80%)

### Coverage by Module (Example)

| Module | Coverage | Status |
|--------|----------|--------|
| analysis/rules/ | 92% | ✅ Excellent |
| analysis/spectrum/ | 88% | ✅ Good |
| reporting/ | 85% | ✅ Good |
| main.py | 78% | ⚠️ Needs work |

## 🎓 Additional Resources

- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Martin Fowler on Test Coverage](https://martinfowler.com/bliki/TestCoverage.html)

## ✅ Summary

FLAC Detective uses comprehensive code coverage tracking to ensure quality:

1. ✅ **80% minimum coverage** enforced in CI/CD
2. ✅ **Codecov integration** for visual reports and PR comments
3. ✅ **HTML reports** for local development
4. ✅ **Badge in README** showing current coverage
5. ✅ **Automatic checks** on every pull request

**Quick command**: `make test-cov` to generate coverage report!
