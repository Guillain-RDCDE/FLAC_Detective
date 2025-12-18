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
pip install -r requirements-dev.txt

# Run tests to ensure everything works
pytest tests/
```

### Making Changes

1. **Write the code** - Follow PEP 8 style guide
2. **Write tests** - Add tests in `tests/` for new features
3. **Test locally** - `pytest tests/` + `make lint`
4. **Update docs** - Add/update relevant documentation

### Code Style

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

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

1. Tests must pass (CI/CD checks)
2. Code review by maintainers
3. Documentation updated if needed
4. Squash commits if requested
5. Merge when approved

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
