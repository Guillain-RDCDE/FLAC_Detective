# CHANGELOG Automation with Commitizen

This document explains how to use Commitizen to automate CHANGELOG generation and version management.

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Conventional Commits](#conventional-commits)
- [Usage](#usage)
- [Release Workflow](#release-workflow)
- [Configuration](#configuration)

## Introduction

FLAC Detective uses [Commitizen](https://commitizen-tools.github.io/commitizen/) to:
- Automatically generate CHANGELOG from commits
- Manage versions following Semantic Versioning
- Enforce Conventional Commits via pre-commit hooks

## Installation

```bash
# Install development dependencies (includes Commitizen)
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install --hook-type commit-msg
```

## Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

- **feat**: New feature (bumps MINOR version)
- **fix**: Bug fix (bumps PATCH version)
- **docs**: Documentation only
- **style**: Formatting, whitespace, etc. (no code changes)
- **refactor**: Code refactoring (bumps PATCH version)
- **perf**: Performance improvement (bumps PATCH version)
- **test**: Adding or updating tests
- **chore**: Build process, dependencies, tooling
- **ci**: CI/CD changes
- **build**: Build system or dependencies

### Breaking Changes

For breaking changes that bump MAJOR version:

```
feat(api): redesign authentication system

BREAKING CHANGE: The authentication API has been completely redesigned.
Old token format is no longer supported.
```

### Examples

```bash
# Feature (bumps MINOR: 0.8.0 → 0.9.0)
feat(analysis): add support for 24-bit FLAC files

# Bug fix (bumps PATCH: 0.8.0 → 0.8.1)
fix(repair): preserve album art during FLAC repair

# Documentation (no version bump)
docs(readme): update installation instructions

# Breaking change (bumps MAJOR: 0.8.0 → 1.0.0)
feat(api)!: redesign analyzer interface

BREAKING CHANGE: FLACAnalyzer now requires explicit configuration
```

## Usage

### Interactive Commit

Use Commitizen to create properly formatted commits:

```bash
cz commit
```

This will guide you through:
1. Select commit type
2. Specify scope (optional)
3. Write short description
4. Write detailed body (optional)
5. Add breaking change note (if applicable)
6. Add issues closed (if applicable)

### Manual Commit

You can also commit manually following the format:

```bash
git commit -m "feat(scoring): implement Rule 12 for DSD detection"
```

### Version Bump

Automatically bump version and update CHANGELOG:

```bash
# Dry run to preview changes
cz bump --dry-run

# Bump version and update CHANGELOG
cz bump --changelog

# Create git tag
cz bump --changelog --tag
```

### Generate CHANGELOG

Generate/update CHANGELOG from existing commits:

```bash
# Generate full CHANGELOG
cz changelog

# Generate changelog for specific version
cz changelog --incremental
```

## Release Workflow

### Standard Release Process

1. **Make changes** with conventional commits
   ```bash
   git add .
   cz commit
   ```

2. **Bump version** and generate changelog
   ```bash
   cz bump --changelog
   ```

3. **Review changes**
   - Check `CHANGELOG.md`
   - Verify version in `pyproject.toml`
   - Verify version in `src/flac_detective/__version__.py`

4. **Create and push tag**
   ```bash
   git push
   git push --tags
   ```

5. **GitHub Actions** will automatically:
   - Run tests
   - Build package
   - Publish to PyPI
   - Create GitHub Release

### Using Helper Script

The project includes a helper script for releases:

```bash
# Preview what will change
python scripts/bump_version.py --dry-run

# Bump version, create tag, and push
python scripts/bump_version.py --push
```

## Configuration

Commitizen is configured in `.cz.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.9.0"
version_files = [
    "pyproject.toml:version",
    "src/flac_detective/__version__.py:__version__"
]
tag_format = "v$version"
update_changelog_on_bump = true
bump_message = "bump: version $current_version → $new_version"
```

### Version Files

The version number is automatically synchronized in:
- `pyproject.toml`
- `src/flac_detective/__version__.py`

### Pre-commit Hook

The pre-commit hook validates commit messages:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/commitizen-tools/commitizen
  rev: v3.13.0
  hooks:
    - id: commitizen
      stages: [commit-msg]
```

## Troubleshooting

### Commit Message Rejected

If your commit message is rejected:

```bash
# Check the format
git log --oneline -1

# Amend if needed
git commit --amend
```

### Version Mismatch

If version numbers are out of sync:

```bash
# Let Commitizen fix it
cz bump --changelog
```

### Skipping Hooks

**NOT RECOMMENDED** - Only for emergencies:

```bash
git commit --no-verify -m "emergency fix"
```

## Best Practices

1. **Write Clear Commit Messages**: Describe the "why", not just the "what"
2. **One Commit Per Logical Change**: Keep commits focused
3. **Use Scopes**: Help categorize changes (e.g., `feat(repair):`, `fix(analysis):`)
4. **Reference Issues**: Include `Closes #123` in footer when applicable
5. **Breaking Changes**: Always document with `BREAKING CHANGE:`

## Examples

### Good Commits

```bash
# Feature with scope
feat(scoring): add energy-based cutoff detection

Implements a new method to detect MP3 cutoff frequencies based on
energy analysis rather than simple frequency thresholds. This reduces
false positives for bass-heavy music.

Closes #45

# Bug fix
fix(repair): preserve all metadata tags during FLAC repair

Previously, some custom tags were lost during the repair process.
This fix ensures all VORBIS_COMMENT tags are preserved.

# Documentation
docs(api): add examples for Python API usage

Added code examples showing how to use FLACAnalyzer programmatically
with different configuration options.
```

### Bad Commits (Don't Do This)

```bash
# Too vague
fix: stuff

# Not following format
Fixed the analyzer bug

# Multiple changes in one commit
feat: add new features, fix bugs, update docs
```

## Additional Resources

- [Commitizen Documentation](https://commitizen-tools.github.io/commitizen/)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)

## Support

If you have questions about the commit workflow:
- Check [CONTRIBUTING.md](../development/CONTRIBUTING.md)
- Open a [GitHub Discussion](https://github.com/GuillainM/FLAC_Detective/discussions)
- Create an [issue](https://github.com/GuillainM/FLAC_Detective/issues/new/choose)
