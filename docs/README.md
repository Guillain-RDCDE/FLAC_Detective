# FLAC Detective Documentation

This directory contains the complete documentation for FLAC Detective v0.6.7

## ?? Documentation Files

### User Documentation

- **[RULE_SPECIFICATIONS.md](RULE_SPECIFICATIONS.md)** - Complete specifications of all 11 detection rules with visual diagrams
  - Detailed explanation of each rule
  - Visual ASCII diagrams showing detection patterns
  - Example scenarios and edge cases
  - Essential reading to understand how FLAC Detective works

- **[GUIDE_RETRY_MECHANISM.md](GUIDE_RETRY_MECHANISM.md)** - **NEW v0.6.6** - User guide for retry mechanism
  - How the automatic retry works for FLAC decoder errors
  - Examples of usage and troubleshooting
  - FAQ and best practices
  - Essential for understanding error handling improvements

- **[EXAMPLE_REPORT.txt](EXAMPLE_REPORT.txt)** - Sample output report
  - Shows what a typical FLAC Detective report looks like
  - Helps understand the output format

### Technical Documentation

- **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)** - Technical architecture documentation
  - Code structure and organization
  - Class diagrams and relationships
  - Development guidelines
  - For developers who want to contribute or understand the internals

- **[FLAC_DECODER_ERROR_HANDLING.md](FLAC_DECODER_ERROR_HANDLING.md)** - **NEW v0.6.6** - Technical implementation details
  - Retry mechanism architecture
  - Implementation details for Rules 9 and 11
  - Corruption detection improvements
  - For developers working on error handling

- **[LOGIC_FLOW.md](LOGIC_FLOW.md)** - Analysis logic flow and decision trees
  - Step-by-step analysis process
  - Rule execution order and dependencies
  - Optimization strategies

### Change Documentation

- **[RESUME_MODIFICATIONS.md](RESUME_MODIFICATIONS.md)** - **NEW v0.6.6** - Summary of retry mechanism changes
  - Complete overview of modifications
  - Before/after comparisons
  - Validation and testing results
  - Quick reference for what changed in v0.6.6

## ?? Quick Start

1. **New users**: Start with the main [README.md](../README.md) at the project root
2. **Understanding detection**: Read [RULE_SPECIFICATIONS.md](RULE_SPECIFICATIONS.md)
3. **Understanding error handling (v0.6.6)**: Read [GUIDE_RETRY_MECHANISM.md](GUIDE_RETRY_MECHANISM.md)
4. **Developers**: Check [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)
5. **Working on error handling**: See [FLAC_DECODER_ERROR_HANDLING.md](FLAC_DECODER_ERROR_HANDLING.md)

## ?? Additional Resources

- **README.md** (project root) - Installation, usage, and quick start guide
- **CHANGELOG.md** (project root) - Version history and release notes (see v0.6.6)
- **examples/** directory - Sample files and use cases
- **examples/retry_mechanism_examples.py** - **NEW v0.6.6** - Interactive examples for retry mechanism
