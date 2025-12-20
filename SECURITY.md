# Security Policy

## Supported Versions

We release patches for security vulnerabilities. The following versions are currently supported:

| Version | Supported          |
| ------- | ------------------ |
| 0.8.x   | :white_check_mark: |
| 0.7.x   | :white_check_mark: |
| < 0.7   | :x:                |

## Reporting a Vulnerability

We take the security of FLAC Detective seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

📧 **guillain@poulpe.us**

### What to Include

To help us better understand and resolve the issue, please include as much of the following information as possible:

- **Type of vulnerability** (e.g., command injection, XSS, path traversal, etc.)
- **Full paths of affected source file(s)**
- **Location of the affected source code** (tag/branch/commit or direct URL)
- **Step-by-step instructions to reproduce** the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit it

### What to Expect

When you report a vulnerability, we will:

1. **Acknowledge receipt** within 48 hours
2. **Confirm the problem** and determine affected versions
3. **Audit code** to find similar problems
4. **Prepare fixes** for all supported versions
5. **Release patched versions** as soon as possible
6. **Publicly disclose** the vulnerability after fixes are available

### Disclosure Policy

- **Coordinated disclosure**: We kindly request that you give us reasonable time to address the vulnerability before any public disclosure
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)
- **CVE**: For significant vulnerabilities, we will request a CVE identifier

### Security Update Process

When a security vulnerability is fixed:

1. **Patch release** is published with a new version number
2. **Security advisory** is published on GitHub
3. **Release notes** include security fix details
4. **Users are notified** through GitHub releases and PyPI

## Security Best Practices

### For Users

When using FLAC Detective:

1. **Keep updated**: Always use the latest version
   ```bash
   pip install --upgrade flac-detective
   ```

2. **Verify installation**: Install only from official sources
   - PyPI: https://pypi.org/project/flac-detective/
   - GitHub: https://github.com/GuillainM/FLAC_Detective

3. **File permissions**: Be cautious when analyzing files from untrusted sources
   - FLAC Detective reads audio files but does not execute code from them
   - Malformed files are handled safely with error recovery

4. **Isolated environments**: Consider using virtual environments
   ```bash
   python -m venv flac-env
   source flac-env/bin/activate  # On Windows: flac-env\Scripts\activate
   pip install flac-detective
   ```

5. **Network drives**: Exercise caution when analyzing files on network/cloud drives
   - Use local copies for sensitive analysis
   - Be aware of who has access to the analyzed files

### For Developers

If you're contributing to FLAC Detective:

1. **Dependency security**:
   - Review new dependencies before adding
   - Keep dependencies up to date
   - Monitor security advisories

2. **Input validation**:
   - Validate all file paths
   - Sanitize user inputs
   - Handle malformed files gracefully

3. **Code review**:
   - All PRs require review before merging
   - Security-sensitive changes require extra scrutiny

4. **Testing**:
   - Write security tests for new features
   - Test with malformed/malicious inputs
   - Use fuzzing when appropriate

5. **Secrets management**:
   - Never commit secrets, API keys, or credentials
   - Use environment variables for sensitive config
   - Review `.gitignore` before commits

## Known Security Considerations

### File System Access

FLAC Detective:
- **Reads** FLAC and audio files from the file system
- **Writes** analysis reports and log files
- **Creates** temporary files during repair operations
- **Does NOT** execute code from analyzed files
- **Does NOT** modify source files (except during explicit repair with `--repair`)

### Dependency Security

FLAC Detective depends on:
- **NumPy**: Scientific computing (potential for buffer overflows in native code)
- **SciPy**: Scientific algorithms (same considerations as NumPy)
- **Mutagen**: Audio metadata parsing (potential for malformed file exploits)
- **soundfile**: Audio file I/O (depends on libsndfile)
- **Rich**: Terminal formatting (minimal security risk)

We monitor these dependencies for security updates and update promptly when vulnerabilities are disclosed.

### External Tools

FLAC Detective optionally uses:
- **flac command-line tool**: For file repair and validation
  - Only executes with user-provided file paths
  - Input is validated and sanitized
  - Subprocess calls use secure patterns

### Temporary Files

During repair operations:
- Temporary files are created in system temp directory
- Files are cleaned up after processing
- Permissions are set appropriately (user-only access)

## Security Scanning

### Automated Security Checks

We use the following automated security tools:

1. **Dependabot**: Automated dependency updates
   - Monitors for vulnerable dependencies
   - Creates PRs for security updates
   - Configured in `.github/dependabot.yml`

2. **CodeQL**: Static code analysis
   - Scans for common vulnerabilities
   - Runs on every push and PR
   - Configured in `.github/workflows/codeql.yml`

3. **Bandit**: Python security linter
   - Checks for common security issues
   - Part of pre-commit hooks
   - Configured in `pyproject.toml`

4. **Safety**: Dependency vulnerability scanner
   - Scans for known vulnerabilities
   - Part of development dependencies
   - Run with `safety check`

### Manual Security Reviews

Before major releases, we conduct:
- Code review focused on security
- Dependency audit
- Threat modeling updates
- Security testing with edge cases

## Vulnerability Disclosure History

### Public Security Advisories

To date, no security vulnerabilities have been publicly disclosed for FLAC Detective.

When vulnerabilities are disclosed, they will be listed here with:
- CVE identifier (if applicable)
- Affected versions
- Severity rating
- Mitigation steps
- Credit to reporter

## Security Contacts

- **Primary contact**: guillain@poulpe.us
- **GitHub Security Advisory**: https://github.com/GuillainM/FLAC_Detective/security/advisories

## Recognition

We appreciate the efforts of security researchers who help keep FLAC Detective safe:

- [List will be maintained here as vulnerabilities are responsibly disclosed]

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org/)

---

**Last Updated**: December 2024

Thank you for helping keep FLAC Detective and its users safe!
