# Pull Request Guidelines

This guide explains how to submit high-quality pull requests (PRs) to FLAC Detective.

## Table of Contents

- [Before You Start](#before-you-start)
- [PR Workflow](#pr-workflow)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [PR Review Process](#pr-review-process)
- [Common Issues and Solutions](#common-issues-and-solutions)

## Before You Start

### 1. Check Existing Work

Before creating a PR, ensure:

- [ ] Search [existing PRs](https://github.com/GuillainM/FLAC_Detective/pulls) to avoid duplicates
- [ ] Check [existing issues](https://github.com/GuillainM/FLAC_Detective/issues) for related discussions
- [ ] Read the [Contributing Guide](../CONTRIBUTING.md)
- [ ] Review the [Code of Conduct](../CODE_OF_CONDUCT.md)

### 2. Discuss Major Changes

For significant changes:

1. **Open an issue first** to discuss the approach
2. Wait for maintainer feedback before implementing
3. Reference the issue in your PR description

### 3. Set Up Your Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/FLAC_Detective.git
cd FLAC_Detective

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install --hook-type commit-msg
pre-commit install
```

## PR Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch with a descriptive name
git checkout -b feature/add-json-export
git checkout -b fix/vinyl-detection-false-positive
git checkout -b docs/improve-api-documentation
```

**Branch Naming Convention:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements
- `perf/` - Performance improvements

### 2. Make Your Changes

- Follow the [code quality standards](#code-quality-standards)
- Write tests for your changes
- Update documentation as needed
- Keep commits focused and atomic

### 3. Run Tests and Checks

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage
pytest --cov=flac_detective --cov-report=html

# Run pre-commit checks
pre-commit run --all-files

# Manual code quality checks
black src tests           # Format code
isort src tests          # Sort imports
flake8 src tests         # Lint code
mypy src                 # Type check
```

### 4. Commit Your Changes

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```bash
# Use commitizen for guided commits
cz commit

# Or write conventional commits manually
git commit -m "feat: add JSON export functionality"
git commit -m "fix: correct vinyl detection false positives"
git commit -m "docs: update API documentation for score calculation"
```

**Commit Types:**
- `feat:` - New feature (bumps MINOR version)
- `fix:` - Bug fix (bumps PATCH version)
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring (no functional changes)
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `build:` - Build system or dependency changes
- `ci:` - CI/CD configuration changes
- `chore:` - Other changes (maintenance tasks)

### 5. Push and Create PR

```bash
# Push your branch
git push origin feature/add-json-export

# Go to GitHub and create a Pull Request
# Fill out the PR template completely
```

## Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Examples

**Simple commit:**
```
feat: add JSON export option to CLI
```

**Detailed commit:**
```
fix: correct cutoff detection for vinyl rips

The energy-based cutoff detection was incorrectly flagging
vinyl rips as MP3 transcodes due to the 15 kHz threshold.

Added special handling for files with high noise floor
characteristic of analog sources.

Fixes #123
```

**Breaking change:**
```
feat!: change score calculation to 0-150 scale

BREAKING CHANGE: Score scale changed from 0-100 to 0-150.
Update any scripts that depend on the score range.

Migration guide available in docs/MIGRATION_0.9.md
```

## Code Quality Standards

### Python Code Style

FLAC Detective follows these standards:

- **PEP 8**: Python style guide
- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Static type checking

### Code Quality Checklist

- [ ] Code is formatted with `black`
- [ ] Imports are sorted with `isort`
- [ ] No linting errors from `flake8`
- [ ] Type hints added for public APIs
- [ ] No `mypy` errors
- [ ] Pre-commit hooks pass
- [ ] No hardcoded credentials or secrets
- [ ] No commented-out code blocks
- [ ] Clear variable and function names

### Type Hints

```python
# Good: Clear type hints
def analyze_file(file_path: Path, duration: float = 30.0) -> Dict[str, Any]:
    """Analyze a FLAC file for authenticity."""
    ...

# Bad: Missing type hints
def analyze_file(file_path, duration=30.0):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_score(rules: List[Rule], data: np.ndarray) -> int:
    """Calculate the authenticity score based on rules.

    Args:
        rules: List of scoring rules to apply
        data: Audio data as numpy array

    Returns:
        Total score from 0-150

    Raises:
        ValueError: If data is empty or invalid

    Example:
        >>> rules = [Rule1(), Rule2()]
        >>> score = calculate_score(rules, audio_data)
        >>> print(score)
        45
    """
    ...
```

## Testing Requirements

### Test Coverage

- All new code must have tests
- Aim for >80% code coverage
- Test both success and failure cases
- Include edge cases

### Test Types

**Unit Tests** (`tests/unit/`):
```python
def test_cutoff_detection():
    """Test cutoff frequency detection."""
    analyzer = FLACAnalyzer()
    cutoff = analyzer.detect_cutoff(test_data)
    assert 15000 < cutoff < 20000
```

**Integration Tests** (`tests/integration/`):
```python
def test_full_analysis_workflow():
    """Test complete analysis workflow."""
    result = analyze_file(test_flac_path)
    assert result["verdict"] == "AUTHENTIC"
    assert result["score"] < 30
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_scoring.py -v

# Run with coverage
pytest --cov=flac_detective --cov-report=html

# Run only fast tests
pytest -m "not slow"

# Run tests in parallel
pytest -n auto
```

## Documentation Requirements

### What to Document

- [ ] **Code changes**: Update docstrings
- [ ] **API changes**: Update API documentation
- [ ] **CLI changes**: Update README and CLI help
- [ ] **New features**: Add usage examples
- [ ] **Breaking changes**: Add migration guide
- [ ] **CHANGELOG.md**: Add entry (automatic with `cz bump`)

### Documentation Checklist

- [ ] Docstrings updated for modified functions/classes
- [ ] README.md updated if needed
- [ ] API documentation updated (`docs/api/`)
- [ ] Examples added or updated (`examples/`)
- [ ] CHANGELOG.md reflects changes (via Commitizen)

### Writing Good Documentation

**Clear and Concise:**
```python
# Good
def repair_file(path: Path) -> bool:
    """Repair a corrupted FLAC file.

    Returns:
        True if repair succeeded, False otherwise.
    """

# Bad
def repair_file(path: Path) -> bool:
    """This function takes a path and tries to repair it maybe."""
```

**Include Examples:**
```python
def analyze_directory(path: Path, recursive: bool = False) -> List[Dict]:
    """Analyze all FLAC files in a directory.

    Args:
        path: Directory path to analyze
        recursive: If True, analyze subdirectories

    Returns:
        List of analysis results

    Example:
        >>> results = analyze_directory(Path("/music"), recursive=True)
        >>> print(f"Analyzed {len(results)} files")
        Analyzed 150 files
    """
```

## PR Review Process

### What Reviewers Look For

1. **Code Quality**: Follows style guidelines, readable, maintainable
2. **Tests**: Comprehensive test coverage, tests pass
3. **Documentation**: Clear, complete, accurate
4. **Performance**: No obvious performance issues
5. **Security**: No vulnerabilities introduced
6. **Breaking Changes**: Properly documented and justified

### Review Checklist

When your PR is reviewed, expect checks for:

- [ ] PR template fully filled out
- [ ] Conventional commits used
- [ ] All CI checks passing
- [ ] Code coverage maintained or improved
- [ ] No merge conflicts
- [ ] Linked to related issues
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Documentation complete
- [ ] Tests comprehensive

### Addressing Review Comments

1. **Respond to all comments** - Even if just to acknowledge
2. **Make requested changes** in new commits (don't force-push during review)
3. **Mark conversations as resolved** after addressing
4. **Ask for clarification** if feedback is unclear
5. **Re-request review** after making changes

## Common Issues and Solutions

### Pre-commit Hooks Failing

```bash
# Fix formatting issues
black src tests
isort src tests

# Run hooks manually to see issues
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify -m "message"
```

### Tests Failing

```bash
# Run tests in verbose mode
pytest tests/ -v -s

# Run specific failing test
pytest tests/unit/test_scoring.py::test_rule_1 -v

# Check test coverage
pytest --cov=flac_detective --cov-report=term-missing
```

### Merge Conflicts

```bash
# Update your branch with latest main
git checkout main
git pull upstream main
git checkout your-branch
git rebase main

# Resolve conflicts, then
git add .
git rebase --continue
git push --force-with-lease
```

### CI/CD Failures

1. Check the CI logs in the GitHub Actions tab
2. Run the same checks locally:
   ```bash
   pytest tests/ -v
   pre-commit run --all-files
   ```
3. Fix issues and push again

### Type Check Errors

```bash
# Run mypy locally
mypy src

# Add type hints or use type: ignore comments sparingly
# Good:
def process(data: List[int]) -> int:
    ...

# Acceptable (with justification):
result = complex_function()  # type: ignore[no-untyped-call]
```

## Best Practices

### Do's ✅

- **Keep PRs focused** - One feature or fix per PR
- **Write clear descriptions** - Explain what, why, and how
- **Add tests** - Ensure your code is tested
- **Update docs** - Keep documentation in sync
- **Follow conventions** - Use established patterns
- **Be responsive** - Address review comments promptly
- **Ask questions** - Better to clarify than assume

### Don'ts ❌

- **Don't mix changes** - Separate refactoring from features
- **Don't skip tests** - Every change needs tests
- **Don't ignore feedback** - Engage with reviewers
- **Don't force-push** - During review (rebasing is OK before)
- **Don't leave TODOs** - Complete work before PR
- **Don't commit secrets** - No API keys, passwords, etc.
- **Don't assume** - Ask if requirements are unclear

## Getting Help

If you need help with your PR:

1. **Ask in the PR comments** - Tag maintainers with @username
2. **Open a discussion** - [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)
3. **Check documentation** - [Contributing Guide](../CONTRIBUTING.md)
4. **Review examples** - Look at merged PRs for reference

## Additional Resources

- [Contributing Guide](../CONTRIBUTING.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pre-commit Setup](PRE_COMMIT_SETUP.md)
- [Testing Guide](../tests/TESTING_STATUS.md)
- [Changelog Automation](CHANGELOG_AUTOMATION.md)

---

Thank you for contributing to FLAC Detective! 🎵
