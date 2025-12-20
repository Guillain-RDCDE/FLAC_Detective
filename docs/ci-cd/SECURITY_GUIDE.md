# Security Guide for FLAC Detective

## Overview

This guide provides comprehensive information about security practices, tools, and policies for FLAC Detective.

## Table of Contents

1. [Security Policy](#security-policy)
2. [Automated Security Tools](#automated-security-tools)
3. [Dependency Management](#dependency-management)
4. [Vulnerability Scanning](#vulnerability-scanning)
5. [Security Best Practices](#security-best-practices)
6. [Reporting Vulnerabilities](#reporting-vulnerabilities)
7. [Security Checklist](#security-checklist)

---

## Security Policy

FLAC Detective follows a comprehensive security policy outlined in [SECURITY.md](../SECURITY.md).

### Key Points

- **Supported Versions**: Security patches for 0.7.x and 0.8.x
- **Reporting**: Private disclosure to guillain@poulpe.us
- **Response Time**: Acknowledgment within 48 hours
- **Disclosure**: Coordinated disclosure after patches are available

---

## Automated Security Tools

### 1. Dependabot

**Purpose**: Automated dependency updates and security patches

**Configuration**: [`.github/dependabot.yml`](../.github/dependabot.yml)

**Features**:
- Weekly scans of Python dependencies
- Weekly scans of GitHub Actions
- Automatic PR creation for updates
- Grouped updates for related packages
- Security-only updates prioritized

**Groups**:
- `scientific`: NumPy, SciPy
- `audio`: Mutagen, soundfile
- `development`: pytest, black, flake8, etc.
- `documentation`: Sphinx and related tools

**How it works**:
```yaml
# Dependabot checks weekly on Mondays at 9:00 AM
schedule:
  interval: "weekly"
  day: "monday"
  time: "09:00"
```

**Responding to Dependabot PRs**:
1. Review the changelog and security advisory
2. Check for breaking changes
3. Run tests locally if needed
4. Approve and merge if safe
5. Monitor for issues after merge

---

### 2. CodeQL

**Purpose**: Static code analysis for security vulnerabilities

**Configuration**: [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml)

**Features**:
- Scans Python code for common vulnerabilities
- Runs on every push and PR
- Weekly scheduled scans
- Security-and-quality query pack
- Results uploaded to GitHub Security tab

**Detected Issues**:
- SQL injection
- Command injection
- Path traversal
- Cross-site scripting (XSS)
- Insecure deserialization
- Hard-coded credentials
- And many more...

**Viewing Results**:
1. Go to repository **Security** tab
2. Click **Code scanning alerts**
3. Review findings by severity
4. Dismiss false positives with justification

**Example Alert**:
```
Severity: High
Rule: py/command-injection
File: src/flac_detective/repair.py
Line: 45
Message: Unsanitized user input in command execution
```

---

### 3. Bandit

**Purpose**: Python security linter

**Configuration**: Part of pre-commit hooks and CI pipeline

**Features**:
- Scans for common Python security issues
- Checks for hard-coded passwords
- Detects unsafe YAML loading
- Identifies SQL injection risks
- Finds insecure temp file usage

**Running Locally**:
```bash
# Install
pip install bandit[toml]

# Scan entire project
bandit -r src/

# Scan with JSON output
bandit -r src/ -f json -o bandit-report.json

# Scan with specific severity
bandit -r src/ -ll  # Only medium and high severity
```

**Common Issues Detected**:
- `B101`: Assert used (not secure for validation)
- `B108`: Insecure temp file usage
- `B201`: Flask debug mode
- `B301`: Pickle usage (insecure deserialization)
- `B501`: Request with verify=False
- `B601`: Paramiko usage without HostKeyPolicy
- `B603`: subprocess without shell=False

**Suppressing False Positives**:
```python
# nosec comment to suppress specific warning
subprocess.run(command, shell=True)  # nosec B602
```

---

### 4. Safety

**Purpose**: Dependency vulnerability scanner

**Features**:
- Checks for known vulnerabilities in dependencies
- Uses Safety DB (vulnerability database)
- Part of CI pipeline
- Integrated with development workflow

**Running Locally**:
```bash
# Install
pip install safety

# Check installed packages
safety check

# Check requirements.txt
safety check -r requirements.txt

# JSON output
safety check --json
```

**Example Output**:
```
+==============================================================================+
| REPORT                                                                       |
+==============================================================================+
| checked 15 packages, using default DB                                       |
+==============================================================================+
| -> 1 vulnerability found                                                    |
+==============================================================================+
| Package: numpy                                                               |
| Installed: 1.20.0                                                           |
| Affected: <1.22.0                                                           |
| ID: 44715                                                                   |
| Advisory: Numpy 1.22.0 includes a fix for CVE-2021-41495                   |
+==============================================================================+
```

---

### 5. Pip-audit

**Purpose**: Official Python vulnerability scanner

**Features**:
- Audits Python packages for known vulnerabilities
- Uses OSV (Open Source Vulnerabilities) database
- More comprehensive than Safety
- Part of CI pipeline

**Running Locally**:
```bash
# Install
pip install pip-audit

# Audit installed packages
pip-audit

# Audit and fix
pip-audit --fix

# JSON output
pip-audit --format json
```

---

## Dependency Management

### Viewing Dependencies

```bash
# List all dependencies
pip list

# Show dependency tree
pip install pipdeptree
pipdeptree

# Check for outdated packages
pip list --outdated
```

### Updating Dependencies

**For Security Updates**:
```bash
# Update specific package
pip install --upgrade package-name

# Update all packages (caution!)
pip install --upgrade -r requirements.txt
```

**For Development**:
1. Create feature branch
2. Update dependencies
3. Run full test suite
4. Create PR with changes
5. Review and merge

### Pinning Dependencies

**pyproject.toml** uses minimum versions:
```toml
dependencies = [
    "numpy>=1.20.0",     # Allows updates
    "scipy>=1.7.0",      # Allows updates
]
```

**For reproducible builds**, use lock files:
```bash
# Generate requirements with exact versions
pip freeze > requirements.lock

# Install from lock file
pip install -r requirements.lock
```

---

## Vulnerability Scanning

### GitHub Security Features

#### 1. Security Advisories

**Location**: Repository → Security → Advisories

**Purpose**: Private disclosure of vulnerabilities before public release

**How to Create**:
1. Go to Security tab
2. Click "Advisories"
3. Click "New draft security advisory"
4. Fill in details (CVE, severity, description)
5. Add affected versions and patches
6. Publish when patches are ready

#### 2. Secret Scanning

**Purpose**: Detect committed secrets (API keys, tokens, etc.)

**Enabled by default** for public repositories

**If secrets are detected**:
1. GitHub sends alert
2. Rotate the compromised secret immediately
3. Remove from git history:
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch path/to/file' \
     --prune-empty --tag-name-filter cat -- --all
   ```

#### 3. Dependency Graph

**Location**: Repository → Insights → Dependency graph

**Features**:
- Visualize all dependencies
- See dependents (who uses this package)
- Track dependency updates

---

## Security Best Practices

### For Users

1. **Verify Installation Source**
   ```bash
   # Only install from PyPI
   pip install flac-detective

   # Or from GitHub releases
   pip install https://github.com/GuillainM/FLAC_Detective/archive/v0.8.0.tar.gz
   ```

2. **Keep Updated**
   ```bash
   # Check version
   flac-detective --version

   # Update
   pip install --upgrade flac-detective
   ```

3. **Use Virtual Environments**
   ```bash
   python -m venv flac-env
   source flac-env/bin/activate  # Windows: flac-env\Scripts\activate
   pip install flac-detective
   ```

4. **Scan Untrusted Files Safely**
   - Use sandboxed environments for unknown files
   - Run with minimal privileges
   - Monitor system resources

### For Contributors

1. **Before Committing**
   ```bash
   # Run pre-commit hooks
   pre-commit run --all-files

   # Run security scans
   bandit -r src/
   safety check
   pip-audit
   ```

2. **Dependency Additions**
   - Research package reputation
   - Check for known vulnerabilities
   - Review source code if critical
   - Add with minimum required version
   - Document why it's needed

3. **Code Reviews**
   - Check for input validation
   - Verify subprocess calls are safe
   - Look for hardcoded secrets
   - Test with malicious inputs
   - Review security-sensitive changes carefully

4. **Secure Coding**
   ```python
   # ✅ Good: Parameterized, validated
   filepath = Path(user_input).resolve()
   if not filepath.exists():
       raise FileNotFoundError()

   # ❌ Bad: Direct string interpolation
   os.system(f"flac {user_input}")

   # ✅ Good: Subprocess with list
   subprocess.run(["flac", "--test", str(filepath)])

   # ❌ Bad: Shell=True with user input
   subprocess.run(f"flac --test {user_input}", shell=True)
   ```

---

## Reporting Vulnerabilities

### What to Report

- Security vulnerabilities (code execution, data leaks, etc.)
- Dependency vulnerabilities not yet patched
- Security misconfigurations
- Potential attack vectors

### What NOT to Report as Security Issue

- Feature requests → Use feature request template
- Performance issues → Use performance issue template
- General bugs → Use bug report template

### How to Report

**Email**: guillain@poulpe.us

**Include**:
1. Vulnerability type
2. Affected versions
3. Proof of concept
4. Reproduction steps
5. Impact assessment
6. Suggested fix (if any)

**Template**:
```
Subject: [SECURITY] Vulnerability in FLAC Detective

Vulnerability Type: Command Injection
Affected Versions: 0.8.0 and earlier
Severity: High

Description:
[Detailed description]

Reproduction Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Impact:
[What can an attacker do?]

Proof of Concept:
[Code or commands to demonstrate]

Suggested Fix:
[If you have one]

Contact:
[Your contact info if you want credit]
```

---

## Security Checklist

### For Releases

- [ ] All dependencies up to date
- [ ] Security scans passed (CodeQL, Bandit, Safety)
- [ ] No known vulnerabilities in dependencies
- [ ] SECURITY.md updated with supported versions
- [ ] Changelog includes security fixes
- [ ] Security advisories published (if any)
- [ ] Tests include security test cases
- [ ] Documentation reviewed for security guidance

### For Pull Requests

- [ ] Pre-commit hooks passed
- [ ] No secrets in code or config
- [ ] Input validation for user data
- [ ] Safe subprocess usage
- [ ] No SQL injection vectors
- [ ] No path traversal issues
- [ ] Error messages don't leak sensitive info
- [ ] Security-sensitive changes reviewed by maintainer

### For Deployments

- [ ] Deployed from verified source
- [ ] Environment variables configured
- [ ] File permissions set correctly
- [ ] Logs monitored for security events
- [ ] Backup and recovery tested
- [ ] Incident response plan in place

---

## Additional Resources

### Documentation

- [SECURITY.md](../SECURITY.md) - Security policy
- [CONTRIBUTING.md](development/CONTRIBUTING.md) - Contribution guidelines
- [CODE_QUALITY_SETUP.md](CODE_QUALITY_SETUP.md) - Quality tools setup

### External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [GitHub Security Features](https://docs.github.com/en/code-security)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://pyup.io/safety/)

### Tools

- **Bandit**: https://bandit.readthedocs.io/
- **Safety**: https://pyup.io/safety/
- **Pip-audit**: https://pypi.org/project/pip-audit/
- **CodeQL**: https://codeql.github.com/
- **Dependabot**: https://docs.github.com/en/code-security/dependabot

---

**Last Updated**: December 2024

Stay secure! 🔒
