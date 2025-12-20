# FLAC Detective Documentation

Complete documentation for FLAC Detective - Audio quality analysis and transcoding detection tool.

## Quick Start

**New to FLAC Detective?** Start here:
- [Getting Started](user-guide/GETTING_STARTED.md) - Installation and basic usage
- [Examples](user-guide/EXAMPLES.md) - Common use cases and scenarios
- [Troubleshooting](user-guide/TROUBLESHOOTING.md) - Common issues and solutions

## Documentation Structure

### 📘 User Guide (`user-guide/`)
Documentation for end users:
- [Getting Started](user-guide/GETTING_STARTED.md) - Installation and first steps
- [Examples](user-guide/EXAMPLES.md) - Usage examples
- [Report Format](user-guide/REPORT_FORMAT.md) - Understanding analysis reports
- [Troubleshooting](user-guide/TROUBLESHOOTING.md) - Common issues

### 🔧 Developer Guide (`development/`)
For contributors and developers:
- [Contributing](development/CONTRIBUTING.md) - Contribution guidelines
- [Development Setup](development/DEVELOPMENT_SETUP.md) - Setting up dev environment
- [Testing](development/TESTING.md) - Running and writing tests

### 🔬 Technical Documentation (`technical/`)
In-depth technical details:
- [Architecture](technical/ARCHITECTURE.md) - System design and components
- [Rules](technical/RULES.md) - Detection rules overview
- [Rule Specifications](technical/RULE_SPECIFICATIONS.md) - Detailed rule specs with diagrams
- [Logic Flow](technical/LOGIC_FLOW.md) - Analysis workflow
- [Technical Documentation](technical/TECHNICAL_DOCUMENTATION.md) - Comprehensive technical details
- [Error Handling](technical/FLAC_DECODER_ERROR_HANDLING.md) - FLAC decoder error handling
- [Retry Mechanism](technical/GUIDE_RETRY_MECHANISM.md) - Retry mechanism guide
- [Type Hints](technical/TYPE_HINTS.md) - Type annotations guide

### 📚 API Reference (`reference/`)
API and integration documentation:
- [API Documentation](reference/API_DOCUMENTATION.md) - Complete API reference
- [Python API Guide](reference/PYTHON_API_GUIDE.md) - Using FLAC Detective as a library

### 🤖 Automation (`automation/`)
Automation and deployment:
- [Docker Guide](automation/DOCKER_GUIDE.md) - Docker usage and deployment
- [Logging Guide](automation/LOGGING_GUIDE.md) - Logging configuration
- [Version Management](automation/VERSION_MANAGEMENT.md) - Version and release management

### 🚀 CI/CD (`ci-cd/`)
Continuous integration and quality:
- [CI/CD Guide](ci-cd/CI_CD_GUIDE.md) - CI/CD pipeline overview
- [Pre-commit Setup](ci-cd/PRE_COMMIT_SETUP.md) - Setting up pre-commit hooks
- [Code Quality Setup](ci-cd/CODE_QUALITY_SETUP.md) - Code quality tools
- [Coverage Setup](ci-cd/COVERAGE_SETUP.md) - Test coverage configuration
- [Changelog Automation](ci-cd/CHANGELOG_AUTOMATION.md) - Automated changelog generation
- [Dependency Automation](ci-cd/DEPENDENCY_AUTOMATION.md) - Dependency management
- [Performance Benchmarking](ci-cd/PERFORMANCE_BENCHMARKING.md) - Performance testing
- [Release Guide](ci-cd/RELEASE_GUIDE.md) - Release process
- [Security Guide](ci-cd/SECURITY_GUIDE.md) - Security scanning and practices
- [Pull Request Guide](ci-cd/PULL_REQUEST_GUIDE.md) - PR workflow
- [Issue Templates Guide](ci-cd/ISSUE_TEMPLATES_GUIDE.md) - Using issue templates
- [Stale Bot Guide](ci-cd/STALE_BOT_GUIDE.md) - Stale issue management

## Sphinx Documentation

This project uses Sphinx for generating API documentation:
- `conf.py` - Sphinx configuration
- `index.rst` - Sphinx documentation index
- `api/` - Auto-generated API documentation
- Build docs: `cd docs && make html`

## PyPI Publication

For PyPI package maintenance:
- See [pypi/](pypi/) directory for publication guides and troubleshooting

## Example Files

- [EXAMPLE_REPORT.txt](EXAMPLE_REPORT.txt) - Sample analysis report output

---

**Can't find what you're looking for?** Check the main [README](../README.md) or open an issue on [GitHub](https://github.com/yourusername/flac-detective).
