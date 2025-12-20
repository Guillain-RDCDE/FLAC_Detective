# 🤝 Contributing to FLAC Detective

Thank you for your interest in contributing! This guide will help you get started.

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Help others learn and grow

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/FLAC_Detective.git`
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Follow** [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)

## Development Workflow

### Before You Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks (IMPORTANT!)
python scripts/setup_precommit.py
# Or manually: pre-commit install

# Run tests to ensure everything works
pytest tests/
```

**✨ Pre-commit hooks will now run automatically on every commit!** See [PRE_COMMIT_SETUP.md](../PRE_COMMIT_SETUP.md) for details.

### Making Changes

1. **Write the code** - Follow PEP 8 style guide
2. **Write tests** - Add tests in `tests/` for new features
   - **Coverage requirement**: Maintain ≥80% code coverage
   - Run `make test-cov` to check coverage locally
3. **Test locally** - `pytest tests/` + `make lint`
4. **Update docs** - Add/update relevant documentation

### Code Style

**Pre-commit hooks handle this automatically**, but you can also run manually:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Or use Makefile shortcuts
make format       # Format code with black + isort
make lint         # Check style with flake8
make type-check   # Type checking with mypy
make check        # Run all quality checks (lint + type + test)

# Or run tools individually
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

**Note**: Code formatting is enforced automatically on commit, so you don't need to run these manually unless debugging.

## Submitting Changes

1. **Commit** with clear messages:
   ```
   feat: Add Rule 12 for streaming artifacts
   
   - Detects streaming compression patterns
   - Analyzes bitrate discontinuities
   - Fixes #123
   ```

2. **Push** to your fork
3. **Create a Pull Request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshot/output if relevant
   - Tests included

## Pull Request Process

1. **Pre-commit hooks pass** - All code quality checks must succeed
2. **Tests must pass** - All unit and integration tests pass
3. **Code review by maintainers** - At least one approval required
4. **Documentation updated** - If adding features or changing behavior
5. **Squash commits if requested** - Keep git history clean
6. **Merge when approved** - Maintainer will merge

### Pre-commit Hook Failures?

If pre-commit hooks fail:
- **Formatting issues** (Black, isort): Usually auto-fixed, just `git add` and commit again
- **Linting issues** (flake8): Fix manually and commit
- **Type errors** (mypy): Add type hints and commit
- **Security issues** (bandit): Review and fix, or add `# nosec` comment if false positive

See [PRE_COMMIT_SETUP.md](../PRE_COMMIT_SETUP.md) for troubleshooting.

## Report Bugs

Found an issue? [Open an issue](https://github.com/GuillainM/FLAC_Detective/issues) with:
- Clear title
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- FLAC files (if possible)

## Suggest Enhancements

Have an idea? Open an issue with:
- Clear title: "Enhancement: ..."
- Motivation: why this would be useful
- Implementation approach (optional)
- Examples or mockups

## Areas to Contribute

- 🐛 **Bug fixes** - Check open issues
- ✨ **New rules** - Propose new detection methods
- 📚 **Documentation** - Improve guides and examples
- 🧪 **Tests** - Increase coverage
- ⚡ **Performance** - Optimize algorithms
- 🎨 **UI/UX** - Improve console output

## Need Help?

- Check [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for setup issues
- Review [TESTING.md](TESTING.md) for testing guidelines
- Read [ARCHITECTURE.md](../ARCHITECTURE.md) for system design
- Ask questions in issues or discussions

Thank you for contributing! 🙏
