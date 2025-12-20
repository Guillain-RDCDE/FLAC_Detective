# Documentation Navigation Guide

Welcome to FLAC Detective's documentation! This guide helps you find the right documentation for your needs.

## Choose Your Path

### 🎯 I want to use FLAC Detective

**Start here:** [User Guide](user-guide/GETTING_STARTED.md)

1. [Getting Started](user-guide/GETTING_STARTED.md) - Installation and first steps
2. [Examples](user-guide/EXAMPLES.md) - Common usage scenarios
3. [Report Format](user-guide/REPORT_FORMAT.md) - Understanding analysis reports
4. [Troubleshooting](user-guide/TROUBLESHOOTING.md) - Solving common issues

### 🔬 I want to understand how it works

**Start here:** [Technical Documentation](technical/TECHNICAL_DOCUMENTATION.md)

1. [Architecture](technical/ARCHITECTURE.md) - System design overview
2. [Rules](technical/RULES.md) - Detection rules explained
3. [Rule Specifications](technical/RULE_SPECIFICATIONS.md) - Detailed rule specs
4. [Logic Flow](technical/LOGIC_FLOW.md) - How analysis works step-by-step

### 💻 I want to contribute code

**Start here:** [Contributing Guide](development/CONTRIBUTING.md)

1. [Contributing](development/CONTRIBUTING.md) - Contribution guidelines
2. [Development Setup](development/DEVELOPMENT_SETUP.md) - Setting up your environment
3. [Testing](development/TESTING.md) - Running and writing tests
4. [Code Quality Setup](ci-cd/CODE_QUALITY_SETUP.md) - Pre-commit hooks and linting

### 📚 I want to use the Python API

**Start here:** [Python API Guide](reference/PYTHON_API_GUIDE.md)

1. [Python API Guide](reference/PYTHON_API_GUIDE.md) - Using FLAC Detective as a library
2. [API Documentation](reference/API_DOCUMENTATION.md) - Complete API reference

### 🐳 I want to use Docker

**Start here:** [Docker Guide](automation/DOCKER_GUIDE.md)

Comprehensive guide covering:
- Installation
- Basic usage
- Volume mounting
- Building custom images
- Docker Compose

### 🚀 I want to set up CI/CD or automation

**Start here:** [CI/CD Guide](ci-cd/CI_CD_GUIDE.md)

Available guides:
- [CI/CD Guide](ci-cd/CI_CD_GUIDE.md) - Overview of the pipeline
- [Pre-commit Setup](ci-cd/PRE_COMMIT_SETUP.md) - Code quality automation
- [Coverage Setup](ci-cd/COVERAGE_SETUP.md) - Test coverage configuration
- [Release Guide](ci-cd/RELEASE_GUIDE.md) - How to release new versions
- [Security Guide](ci-cd/SECURITY_GUIDE.md) - Security scanning
- [Performance Benchmarking](ci-cd/PERFORMANCE_BENCHMARKING.md) - Performance testing

### 🔐 I want to report a security issue

**Read:** [SECURITY.md](../SECURITY.md) (in project root)

Then email: guillain@poulpe.us

## Documentation by Category

### User Documentation
| Document | Purpose |
|----------|---------|
| [Getting Started](user-guide/GETTING_STARTED.md) | Installation and basic usage |
| [Examples](user-guide/EXAMPLES.md) | Real-world usage examples |
| [Report Format](user-guide/REPORT_FORMAT.md) | Understanding analysis output |
| [Troubleshooting](user-guide/TROUBLESHOOTING.md) | Common issues and solutions |

### Technical Documentation
| Document | Purpose |
|----------|---------|
| [Architecture](technical/ARCHITECTURE.md) | System design and components |
| [Rules](technical/RULES.md) | Detection rules overview |
| [Rule Specifications](technical/RULE_SPECIFICATIONS.md) | Detailed rule documentation |
| [Logic Flow](technical/LOGIC_FLOW.md) | Analysis workflow |
| [Technical Documentation](technical/TECHNICAL_DOCUMENTATION.md) | Comprehensive technical details |
| [Error Handling](technical/FLAC_DECODER_ERROR_HANDLING.md) | FLAC decoder error handling |
| [Retry Mechanism](technical/GUIDE_RETRY_MECHANISM.md) | Retry mechanism guide |
| [Type Hints](technical/TYPE_HINTS.md) | Type annotations guide |

### Developer Documentation
| Document | Purpose |
|----------|---------|
| [Contributing](development/CONTRIBUTING.md) | How to contribute |
| [Development Setup](development/DEVELOPMENT_SETUP.md) | Dev environment setup |
| [Testing](development/TESTING.md) | Testing guide |

### API Reference
| Document | Purpose |
|----------|---------|
| [API Documentation](reference/API_DOCUMENTATION.md) | Complete API reference |
| [Python API Guide](reference/PYTHON_API_GUIDE.md) | Using as a Python library |

### Automation & Deployment
| Document | Purpose |
|----------|---------|
| [Docker Guide](automation/DOCKER_GUIDE.md) | Docker usage and deployment |
| [Logging Guide](automation/LOGGING_GUIDE.md) | Logging configuration |
| [Version Management](automation/VERSION_MANAGEMENT.md) | Versioning and releases |

### CI/CD & Quality
| Document | Purpose |
|----------|---------|
| [CI/CD Guide](ci-cd/CI_CD_GUIDE.md) | Pipeline overview |
| [Pre-commit Setup](ci-cd/PRE_COMMIT_SETUP.md) | Pre-commit hooks |
| [Code Quality Setup](ci-cd/CODE_QUALITY_SETUP.md) | Code quality tools |
| [Coverage Setup](ci-cd/COVERAGE_SETUP.md) | Test coverage |
| [Changelog Automation](ci-cd/CHANGELOG_AUTOMATION.md) | Automated changelog |
| [Dependency Automation](ci-cd/DEPENDENCY_AUTOMATION.md) | Dependency management |
| [Performance Benchmarking](ci-cd/PERFORMANCE_BENCHMARKING.md) | Performance testing |
| [Release Guide](ci-cd/RELEASE_GUIDE.md) | Release process |
| [Security Guide](ci-cd/SECURITY_GUIDE.md) | Security practices |
| [Pull Request Guide](ci-cd/PULL_REQUEST_GUIDE.md) | PR workflow |
| [Issue Templates Guide](ci-cd/ISSUE_TEMPLATES_GUIDE.md) | Using issue templates |
| [Stale Bot Guide](ci-cd/STALE_BOT_GUIDE.md) | Stale issue management |

## Quick Links

- **Main README**: [../README.md](../README.md)
- **Project Overview**: [../PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)
- **Changelog**: [../CHANGELOG.md](../CHANGELOG.md)
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Security Policy**: [../SECURITY.md](../SECURITY.md)
- **Code of Conduct**: [../CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)

## Documentation Structure Philosophy

Our documentation is organized by **audience and purpose**:

1. **User Guide**: For end users who want to analyze FLAC files
2. **Technical**: For those who want to understand the science
3. **Reference**: For developers integrating the API
4. **Development**: For contributors improving the code
5. **Automation**: For deploying in production
6. **CI/CD**: For maintaining quality and releases

This structure ensures you find what you need quickly, without navigating through irrelevant documentation.

## Still Can't Find What You Need?

1. Check the [main README](../README.md) for overview
2. Browse the [Project Overview](../PROJECT_OVERVIEW.md) for complete structure
3. Search the [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)
4. Ask in [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions)

---

**Documentation Version**: v0.9.0
**Last Updated**: December 2024
**Status**: Complete ✅
