## 📝 Description

<!-- Provide a clear and concise description of your changes -->

## 🔄 Type of Change

<!-- Check all that apply -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update (no code changes)
- [ ] ♻️ Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test improvement
- [ ] 🔧 CI/CD or tooling changes

## 🔗 Related Issues

<!-- Link related issues. Use "Fixes #123" or "Closes #123" to auto-close issues when PR is merged -->

- Fixes #
- Related to #

## 📋 Checklist

### Code Quality

- [ ] My code follows the project's style guidelines (black, isort, flake8)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)

### Testing

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes (`pytest tests/unit/`)
- [ ] New and existing integration tests pass locally (`pytest tests/integration/`)
- [ ] I have verified the test coverage is maintained or improved

### Documentation

- [ ] I have updated the documentation accordingly
- [ ] I have updated the CHANGELOG.md file (following [Keep a Changelog](https://keepachangelog.com/))
- [ ] I have added/updated docstrings for public functions/classes
- [ ] I have updated the README.md if needed

### Commits

- [ ] My commits follow the [Conventional Commits](https://www.conventionalcommits.org/) specification
- [ ] My commit messages are clear and descriptive

## 🧪 Testing

<!-- Describe the tests you ran to verify your changes -->

### Test Configuration

- **Python Version**: <!-- e.g., 3.11 -->
- **OS**: <!-- e.g., Ubuntu 22.04, macOS 13, Windows 11 -->
- **Test Files Used**: <!-- e.g., sample FLAC files, test fixtures -->

### Test Results

```bash
# Paste your test output here
pytest tests/ -v
```

### Manual Testing

<!-- Describe any manual testing performed -->

1.
2.
3.

## 📸 Screenshots / Examples

<!-- If applicable, add screenshots or command-line examples to help explain your changes -->

### Before

```
<!-- Example output or behavior before your changes -->
```

### After

```
<!-- Example output or behavior after your changes -->
```

## ⚡ Performance Impact

<!-- If applicable, describe the performance impact of your changes -->

- [ ] No performance impact
- [ ] Performance improved (provide benchmarks if possible)
- [ ] Performance degraded (explain why this trade-off is acceptable)

### Benchmarks

<!-- If you ran performance tests, include the results here -->

```
# Paste benchmark results here
```

## 🔄 Breaking Changes

<!-- If this is a breaking change, describe the migration path for users -->

### What breaks

<!-- Describe what will break -->

### Migration Guide

<!-- Provide step-by-step instructions for users to migrate -->

1.
2.
3.

## 📝 Additional Notes

<!-- Add any other context about the pull request here -->

## 📚 References

<!-- Add links to relevant resources, documentation, or discussions -->

- Related Documentation:
- External References:
- Discussion:

---

## 🔍 Reviewer Checklist

<!-- For reviewers - do not fill this out if you are the PR author -->

- [ ] Code quality is acceptable
- [ ] Tests are comprehensive and passing
- [ ] Documentation is clear and complete
- [ ] No security vulnerabilities introduced
- [ ] Performance impact is acceptable
- [ ] Breaking changes are properly documented
- [ ] CHANGELOG.md is updated appropriately
