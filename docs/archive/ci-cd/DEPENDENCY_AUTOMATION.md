# Dependency Automation Guide

This guide explains how FLAC Detective automates dependency updates using Dependabot and auto-merge workflows.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Auto-Merge Policy](#auto-merge-policy)
- [Dependency Groups](#dependency-groups)
- [Manual Review Process](#manual-review-process)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Overview

FLAC Detective uses GitHub's Dependabot to automatically:
- Check for dependency updates weekly (every Monday at 9:00 AM Paris time)
- Create pull requests for updates
- Group related dependencies together
- Auto-merge safe updates (patches and minor dev dependencies)
- Request manual review for major updates

**Benefits**:
- ✅ Always up-to-date dependencies
- ✅ Automatic security patches
- ✅ Reduced maintenance burden
- ✅ Safe, tested updates
- ✅ Minimal manual intervention

## How It Works

### 1. Dependabot Checks for Updates

Every Monday, Dependabot scans `pyproject.toml` and GitHub Actions for updates:

```yaml
schedule:
  interval: "weekly"
  day: "monday"
  time: "09:00"
  timezone: "Europe/Paris"
```

### 2. Pull Requests Created

When updates are found, Dependabot creates PRs with:
- Clear commit messages (`deps:` or `deps(dev):` prefix)
- Grouped related dependencies
- Automatic labels
- Assigned reviewers

### 3. Auto-Merge Workflow Triggered

The [dependabot-auto-merge.yml](.github/workflows/dependabot-auto-merge.yml) workflow:

1. **Extracts metadata** - Analyzes update type (major/minor/patch)
2. **Auto-labels PR** - Adds semantic labels (`semver-patch`, `semver-minor`, etc.)
3. **Auto-approves safe updates** - Approves patches and minor dev updates
4. **Waits for CI** - Ensures all tests pass
5. **Enables auto-merge** - Merges automatically if conditions met
6. **Notifies manual review** - Flags major updates for human review

## Auto-Merge Policy

### Automatically Merged

The following updates are **automatically merged** once CI passes:

#### ✅ All Patch Updates (0.0.X)
- **Production dependencies**: ✅ Auto-merged
- **Development dependencies**: ✅ Auto-merged
- **Reason**: Bug fixes and security patches are safe

**Example**: `numpy 1.24.3 → 1.24.4`

#### ✅ Minor Development Dependencies (0.X.0)
- **Development dependencies only**: ✅ Auto-merged
- **Reason**: Dev tools don't affect production code

**Example**: `pytest 7.4.0 → 7.5.0`

### Require Manual Review

The following updates require **manual review**:

#### 🔍 Minor Production Dependencies (0.X.0)
- **Production dependencies**: ⚠️ Manual review
- **Reason**: May introduce new features that need testing

**Example**: `numpy 1.24.0 → 1.25.0`

#### 🔍 Major Updates (X.0.0)
- **All dependencies**: ⚠️ Manual review
- **Reason**: Breaking changes possible

**Example**: `numpy 1.26.0 → 2.0.0`

## Dependency Groups

Dependencies are organized into logical groups for easier management:

### Python Dependencies

#### Production Core
```yaml
production-core:
  - numpy
  - scipy
  - mutagen
  - soundfile
  - rich
```
**Auto-merge**: Patch updates only

#### Development - Testing
```yaml
dev-testing:
  - pytest*
  - coverage
```
**Auto-merge**: Patch + minor updates

#### Development - Code Quality
```yaml
dev-code-quality:
  - black
  - isort
  - flake8*
  - mypy
  - pylint
  - bandit
  - safety
  - interrogate
```
**Auto-merge**: Patch + minor updates

#### Development - Pre-commit
```yaml
dev-pre-commit:
  - pre-commit
```
**Auto-merge**: Patch + minor updates

#### Documentation
```yaml
documentation:
  - sphinx*
  - myst-parser
```
**Auto-merge**: Patch + minor updates

### GitHub Actions

All GitHub Actions updates are grouped together:
```yaml
github-actions:
  - All actions (*)
```
**Auto-merge**: Patch updates only

## Manual Review Process

### When Manual Review is Required

You'll receive a PR with a comment like:

```
🔍 Manual review required

This is a major version update and requires careful review:

📦 Dependency: numpy
📈 Version: 1.26.0 → 2.0.0
⚠️ Update type: Major (breaking changes possible)

Review checklist:
- [ ] Check CHANGELOG/release notes for breaking changes
- [ ] Review CI test results
- [ ] Test locally if needed
- [ ] Update code if API changes required

Once reviewed and approved, merge manually or use:
@dependabot merge
```

### Review Steps

1. **Check the changelog**:
   - Visit the dependency's GitHub/website
   - Review release notes for breaking changes
   - Check migration guides

2. **Review CI results**:
   - Ensure all tests pass
   - Check for new warnings
   - Review test coverage

3. **Test locally** (if needed):
   ```bash
   git fetch origin
   git checkout dependabot/pip/numpy-2.0.0
   pytest tests/
   ```

4. **Merge or request changes**:
   - If all OK: Approve and merge
   - If issues: Request changes or close PR

### Dependabot Commands

You can control Dependabot via PR comments:

```bash
@dependabot merge          # Merge this PR
@dependabot cancel merge   # Cancel auto-merge
@dependabot rebase         # Rebase this PR
@dependabot recreate       # Recreate this PR
@dependabot close          # Close this PR
@dependabot ignore         # Ignore this dependency
```

## Configuration

### Dependabot Config

Location: [`.github/dependabot.yml`](.github/dependabot.yml)

**Key settings**:
```yaml
schedule:
  interval: "weekly"              # Check weekly
  day: "monday"                   # Every Monday
  time: "09:00"                   # 9:00 AM
  timezone: "Europe/Paris"        # Paris timezone

open-pull-requests-limit: 10      # Max 10 PRs at once
versioning-strategy: increase     # Compatible updates only
rebase-strategy: auto             # Auto-rebase on conflicts
```

### Auto-Merge Workflow

Location: [`.github/workflows/dependabot-auto-merge.yml`](.github/workflows/dependabot-auto-merge.yml)

**Key features**:
- Metadata extraction from Dependabot
- Automatic PR labeling
- Auto-approval for safe updates
- CI check waiting
- Auto-merge enablement
- Manual review notifications

### Customizing Auto-Merge Rules

To change what gets auto-merged, edit the workflow conditions:

```yaml
# Current rules
auto-merge:
  if: |
    update-type == 'semver-patch' ||
    (update-type == 'semver-minor' && dependency-type == 'development')
```

**Examples**:

**Auto-merge all minor updates**:
```yaml
if: |
  update-type == 'semver-patch' ||
  update-type == 'semver-minor'
```

**Only auto-merge patches**:
```yaml
if: update-type == 'semver-patch'
```

**Disable auto-merge** (approve only):
```yaml
if: false  # Never auto-merge, only auto-approve
```

## Labels

PRs are automatically labeled for easy filtering:

### Update Type Labels
- `semver-patch` - Patch update (0.0.X)
- `semver-minor` - Minor update (0.X.0)
- `semver-major` - Major update (X.0.0)

### Review Status Labels
- `auto-merge-candidate` - Eligible for auto-merge
- `needs-review` - Requires manual review

### Dependency Type Labels
- `production-dependency` - Production dependency
- `dev-dependency` - Development dependency

### Ecosystem Labels
- `python` - Python dependency (pip)
- `github-actions` - GitHub Actions

### Standard Labels
- `dependencies` - All Dependabot PRs
- `automated` - Automated update

## Troubleshooting

### Auto-Merge Not Working

**Problem**: PR not auto-merging despite passing checks

**Solutions**:
1. **Check PR labels**: Should have `auto-merge-candidate`
2. **Check update type**: Only patches and minor dev deps auto-merge
3. **Check CI status**: All checks must pass
4. **Check branch protection**: Auto-merge requires protected branch settings
5. **Manual trigger**: Comment `@dependabot merge`

### Too Many PRs

**Problem**: Dependabot creating too many PRs

**Solution**: Reduce `open-pull-requests-limit` in config:
```yaml
open-pull-requests-limit: 5  # Reduce from 10
```

### Ignoring Specific Dependencies

**Problem**: Don't want to update a specific dependency

**Solution**: Add to `ignore` list in config:
```yaml
ignore:
  - dependency-name: "numpy"
    versions: ["2.x"]  # Ignore v2.x
```

### Grouping Not Working

**Problem**: Dependencies not grouped as expected

**Solution**: Check group patterns match exactly:
```yaml
groups:
  testing:
    patterns:
      - "pytest*"      # Matches pytest, pytest-cov, etc.
      - "coverage"     # Exact match
```

### CI Failing on Dependabot PRs

**Problem**: Tests fail on dependency updates

**Solutions**:
1. **Check breaking changes**: Review dependency changelog
2. **Update code**: Fix compatibility issues
3. **Update tests**: Adjust tests for new behavior
4. **Pin version**: Add to `ignore` list if needed

## Security Updates

Dependabot automatically creates PRs for security vulnerabilities:

- **Priority**: Security updates are prioritized
- **Auto-merge**: Security patches may auto-merge if safe
- **Notifications**: GitHub sends security alerts
- **Action**: Review and merge ASAP

## Best Practices

### DO ✅

- Review major updates carefully
- Check changelogs before merging
- Test locally for complex updates
- Keep auto-merge enabled for patches
- Monitor dependency health regularly

### DON'T ❌

- Ignore security updates
- Auto-merge major updates without review
- Disable Dependabot without good reason
- Ignore broken CI on dependency updates
- Merge without checking breaking changes

## Monitoring

### Check Dependency Health

**GitHub Insights**:
- Navigate to: Insights → Dependency graph → Dependabot
- View: Active PRs, merged updates, security alerts

**Review Merged Updates**:
```bash
git log --grep="deps:" --oneline
```

**Check Auto-Merge Activity**:
- Navigate to: Actions → Dependabot Auto-Merge
- Review: Recent runs, success rate, errors

## Related Documentation

- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [Release Guide](RELEASE_GUIDE.md) - Creating releases
- [Contributing Guide](development/CONTRIBUTING.md) - Development workflow
- [Security Guide](SECURITY_GUIDE.md) - Security policies

## Support

For issues with dependency automation:

1. **Check workflow runs**: https://github.com/GuillainM/FLAC_Detective/actions
2. **Review Dependabot PRs**: https://github.com/GuillainM/FLAC_Detective/pulls
3. **Open an issue**: https://github.com/GuillainM/FLAC_Detective/issues

---

**Last updated**: 2025-12-20
**Workflow version**: v1.0
