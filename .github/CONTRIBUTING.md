# Contributing to FLAC Detective

Thank you for your interest in contributing! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
- [Areas to Contribute](#areas-to-contribute)

## Code of Conduct

### Our Standards

- **Be respectful** - Treat others with respect and consideration
- **Be constructive** - Focus on the code and ideas, not the person
- **Be collaborative** - Help others learn and grow
- **Be patient** - Remember that everyone was a beginner once

### Expected Behavior

✅ Use welcoming and inclusive language
✅ Accept constructive criticism gracefully
✅ Focus on what's best for the project
✅ Show empathy towards other contributors

❌ Trolling, insulting, or derogatory comments
❌ Personal or political attacks
❌ Publishing others' private information
❌ Unprofessional conduct

## Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/FLAC_Detective.git
cd FLAC_Detective
```

### 2. Add Upstream Remote

```bash
# Add the original repository as upstream
git remote add upstream https://github.com/GuillainM/FLAC_Detective.git

# Verify remotes
git remote -v
```

### 3. Create a Branch

```bash
# Create and switch to a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- (Optional) FLAC command-line tool

### Install Development Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

This installs:
- FLAC Detective in editable mode
- Testing tools (pytest, pytest-cov)
- Code quality tools (black, isort, flake8, mypy)
- Pre-commit hooks

### Set Up Pre-Commit Hooks

Pre-commit hooks automatically check code quality on every commit:

```bash
# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

**What the hooks do**:
- Format code with Black
- Sort imports with isort
- Check style with flake8
- Type check with mypy
- Security scan with bandit

## Development Workflow

### Before You Start Coding

1. **Check existing issues** - Is someone already working on this?
2. **Open an issue** - Discuss your idea before major work
3. **Get feedback** - Wait for maintainer input on approach

### Making Changes

#### 1. Write Code

Follow these guidelines:

**Code Style**:
- Follow PEP 8 (enforced by flake8)
- Use meaningful variable names
- Keep functions small and focused
- Add docstrings to public functions

**Example**:
```python
def analyze_cutoff_frequency(fft_magnitude: np.ndarray,
                             frequencies: np.ndarray,
                             threshold: float = 0.01) -> float:
    """
    Detect frequency cutoff from FFT magnitude spectrum.

    Args:
        fft_magnitude: FFT magnitude array
        frequencies: Corresponding frequency bins
        threshold: Magnitude threshold (fraction of peak)

    Returns:
        Cutoff frequency in Hz
    """
    peak = np.max(fft_magnitude)
    threshold_value = threshold * peak

    # Find last frequency above threshold
    above_threshold = fft_magnitude > threshold_value
    cutoff_index = np.where(above_threshold)[0][-1]

    return frequencies[cutoff_index]
```

#### 2. Write Tests

**Coverage requirement**: ≥80% code coverage

```python
# tests/unit/test_spectrum.py
import pytest
import numpy as np
from flac_detective.analysis.spectrum import analyze_cutoff_frequency

def test_cutoff_detection_basic():
    """Test basic cutoff frequency detection."""
    # Create mock FFT with cutoff at 20 kHz
    frequencies = np.linspace(0, 22050, 1000)
    magnitude = np.ones(1000)
    magnitude[900:] = 0.001  # Sharp drop at ~20 kHz

    cutoff = analyze_cutoff_frequency(magnitude, frequencies)

    assert 19000 < cutoff < 21000  # Cutoff around 20 kHz

def test_cutoff_detection_authentic():
    """Test authentic file (full spectrum)."""
    frequencies = np.linspace(0, 22050, 1000)
    magnitude = np.ones(1000)  # No cutoff

    cutoff = analyze_cutoff_frequency(magnitude, frequencies)

    assert cutoff > 21000  # Near Nyquist
```

#### 3. Update Documentation

If you changed behavior or added features:

- Update relevant documentation files
- Add docstrings to new functions
- Update examples if needed

### Running Tests Locally

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=flac_detective --cov-report=html

# Run specific test file
pytest tests/unit/test_spectrum.py

# Run specific test
pytest tests/unit/test_spectrum.py::test_cutoff_detection_basic -v

# Run tests matching pattern
pytest -k "cutoff" -v
```

### Code Quality Checks

Pre-commit hooks run automatically, but you can run manually:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/

# Run all checks
pre-commit run --all-files
```

## Testing

### Test Structure

```
tests/
├── unit/                  # Unit tests (fast, isolated)
│   ├── test_analyzer.py
│   ├── test_spectrum.py
│   ├── test_rules.py
│   └── ...
├── integration/           # Integration tests (slower, full workflow)
│   ├── test_end_to_end.py
│   └── ...
├── benchmarks/           # Performance tests
│   └── test_performance.py
└── fixtures/             # Test data
    └── sample.flac
```

### Writing Good Tests

**Do**:
✅ Test one thing per test function
✅ Use descriptive test names
✅ Use fixtures for common setup
✅ Test edge cases and error conditions
✅ Keep tests fast (< 1 second each)

**Don't**:
❌ Test implementation details
❌ Rely on external resources (network, files)
❌ Write flaky tests (random failures)
❌ Skip writing tests

**Example - Good Test**:
```python
def test_mp3_signature_detection_192kbps():
    """Test MP3 192 kbps signature detection."""
    # Arrange
    cutoff_freq = 19200  # Typical 192 kbps cutoff
    sample_rate = 44100

    # Act
    score, reason = rule_01_mp3_spectral(cutoff_freq, sample_rate)

    # Assert
    assert score == 50  # Should add 50 points
    assert "192 kbps" in reason
```

### Test Coverage

Check coverage:

```bash
# Generate HTML coverage report
pytest --cov=flac_detective --cov-report=html

# Open in browser
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

**Coverage goals**:
- Overall: ≥80%
- New code: ≥90%
- Critical paths: 100%

## Code Quality

### Code Formatting

**Black** (code formatter):
```bash
black src/ tests/
```

**isort** (import sorter):
```bash
isort src/ tests/
```

### Linting

**flake8** (style checker):
```bash
flake8 src/ tests/
```

Common issues:
- Line too long (max 88 chars with Black)
- Unused imports
- Undefined names
- Missing docstrings

### Type Checking

**mypy** (type checker):
```bash
mypy src/
```

Add type hints to new code:
```python
def analyze_file(filepath: Path, duration: float = 30.0) -> dict:
    """Analyze FLAC file."""
    ...
```

### Security

**bandit** (security linter):
```bash
bandit -r src/
```

If false positive, add comment:
```python
result = subprocess.run(cmd, shell=True)  # nosec - Safe command
```

**Note on safety**: The `safety` tool is included in dev dependencies but only works with Poetry-based projects. Since FLAC Detective uses setuptools, `safety` cannot scan dependencies directly. For dependency vulnerability scanning, consider using:
- GitHub Dependabot (enabled by default)
- `pip-audit` as an alternative: `pip install pip-audit && pip-audit`

## Submitting Changes

### 1. Commit Your Changes

Use **conventional commits** format:

```bash
# Format: <type>: <description>
# Types: feat, fix, docs, refactor, test, perf, chore

git commit -m "feat: Add Rule 12 for streaming artifacts"
git commit -m "fix: Correct cutoff detection for bass-heavy music"
git commit -m "docs: Update API reference with new parameters"
git commit -m "test: Add tests for vinyl detection"
```

**Good commit messages**:
```
feat: Add support for 96 kHz sample rate analysis

- Extend FFT computation for higher sample rates
- Update Nyquist threshold calculations
- Add tests for 96 kHz files

Fixes #123
```

**Bad commit messages**:
```
update stuff
fix bug
wip
asdf
```

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Open a Pull Request

Go to GitHub and create a Pull Request.

**PR Template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests
- [ ] Coverage ≥80%

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Fixes #123
Closes #456
```

### 4. Code Review Process

1. **Automated checks run** - CI/CD pipeline
2. **Maintainer reviews** - May request changes
3. **You address feedback** - Push new commits
4. **Approval** - Maintainer approves PR
5. **Merge** - PR merged to main branch

**Handling feedback**:
- Be open to suggestions
- Ask questions if unclear
- Make requested changes
- Push updates to same branch

### 5. After Merge

```bash
# Update your local repository
git checkout main
git pull upstream main

# Delete feature branch (optional)
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Areas to Contribute

### 🐛 Bug Fixes

Check [open issues](https://github.com/GuillainM/FLAC_Detective/issues) labeled `bug`.

**Process**:
1. Reproduce the bug
2. Write a failing test
3. Fix the bug
4. Verify test passes

### ✨ New Features

**Ideas for features**:
- Support for other lossless formats (WAV, ALAC)
- Additional detection rules
- GUI interface
- Web service API
- Performance improvements

**Before starting**:
1. Open an issue to discuss
2. Wait for maintainer feedback
3. Get approval on approach
4. Start implementation

### 📚 Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples
- Improve API documentation
- Translate to other languages

### 🧪 Testing

Increase test coverage:

```bash
# Find untested code
pytest --cov=flac_detective --cov-report=term-missing

# Focus on files with low coverage
```

### ⚡ Performance

Profile and optimize:

```bash
# Run benchmarks
pytest tests/benchmarks/ -v

# Profile code
python -m cProfile -o profile.stats your_script.py
```

### 🎨 Code Quality

- Improve code organization
- Add type hints
- Refactor complex functions
- Reduce code duplication

## Getting Help

**Questions about contributing?**

- Read this guide thoroughly
- Check existing issues and PRs
- Ask in [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
- Contact maintainers

**Development questions?**

- Review [Technical Details](../docs/technical-details.md)
- Check [API Reference](../docs/api-reference.md)
- Look at existing code for examples

## Recognition

All contributors are recognized in:
- GitHub contributors page
- Release notes
- Project documentation

Thank you for contributing! 🙏

---

**Ready to contribute?** Fork the repo and start coding!
