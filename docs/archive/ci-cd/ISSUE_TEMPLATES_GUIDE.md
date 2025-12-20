# GitHub Issue Templates Guide

## Overview

FLAC Detective uses GitHub issue templates to streamline bug reports, feature requests, and other contributions. This ensures we collect the right information to help you effectively.

## Available Templates

### 🐛 Bug Report
Use this template when FLAC Detective is not working as expected.

**When to use:**
- Crashes or errors
- Incorrect analysis results
- Unexpected behavior
- Installation problems

**What you'll need:**
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

**Template file:** [`.github/ISSUE_TEMPLATE/bug_report.yml`](../.github/ISSUE_TEMPLATE/bug_report.yml)

---

### ✨ Feature Request
Use this template to suggest new features or enhancements.

**When to use:**
- Requesting new functionality
- Suggesting improvements to existing features
- Proposing API changes
- Requesting new output formats

**What you'll need:**
- Problem statement (what limitation you're facing)
- Proposed solution
- Use cases
- Examples or mock-ups

**Template file:** [`.github/ISSUE_TEMPLATE/feature_request.yml`](../.github/ISSUE_TEMPLATE/feature_request.yml)

---

### ⚡ Performance Issue
Use this template to report slow performance or high resource usage.

**When to use:**
- Analysis is too slow
- High memory or CPU usage
- Disk I/O problems
- Application hangs or freezes

**What you'll need:**
- Description of the performance issue
- Performance metrics (time, CPU%, memory usage)
- Environment details (hardware specs)
- Comparison data (expected vs actual)

**Template file:** [`.github/ISSUE_TEMPLATE/performance_issue.yml`](../.github/ISSUE_TEMPLATE/performance_issue.yml)

---

### 📝 Documentation Issue
Use this template to report documentation problems or suggest improvements.

**When to use:**
- Missing documentation
- Unclear explanations
- Incorrect information
- Broken links
- Outdated examples

**What you'll need:**
- Location of the documentation issue
- Description of the problem
- Suggested improvement

**Template file:** [`.github/ISSUE_TEMPLATE/documentation.yml`](../.github/ISSUE_TEMPLATE/documentation.yml)

---

### ❓ Question / Discussion
Use this template to ask questions about FLAC Detective.

**When to use:**
- How-to questions
- Understanding results
- Best practices
- Integration questions

**What you'll need:**
- Your question
- Relevant context
- What you've tried so far

**Template file:** [`.github/ISSUE_TEMPLATE/question.yml`](../.github/ISSUE_TEMPLATE/question.yml)

**Note:** For in-depth discussions, consider using [GitHub Discussions](https://github.com/GuillainM/FLAC_Detective/discussions) instead.

---

## How to Use Templates

### Creating a New Issue

1. **Go to the Issues page:**
   Visit https://github.com/GuillainM/FLAC_Detective/issues

2. **Click "New Issue":**
   You'll see a list of available templates

3. **Choose the appropriate template:**
   Select the template that best matches your issue

4. **Fill out the form:**
   Complete all required fields (marked with *)

5. **Submit:**
   Click "Submit new issue"

### Template Selection Guide

```
Issue Type                     → Template to Use
─────────────────────────────────────────────────
Application crashes            → Bug Report
Wrong analysis results         → Bug Report
Installation fails             → Bug Report
Error messages                 → Bug Report

New feature idea               → Feature Request
API improvements               → Feature Request
New output format              → Feature Request

Slow analysis                  → Performance Issue
High memory usage              → Performance Issue
Freezing/hanging               → Performance Issue

Missing docs                   → Documentation Issue
Unclear examples               → Documentation Issue
Broken links                   → Documentation Issue

How do I...?                   → Question
Why does...?                   → Question
Best way to...?                → Question
```

---

## Best Practices

### For Bug Reports

1. **Search first:** Check if the bug has already been reported
2. **Use latest version:** Update to the latest version before reporting
3. **Provide logs:** Include error messages and log files
4. **Minimal reproduction:** Provide the simplest way to reproduce the bug
5. **One issue per report:** Don't combine multiple bugs in one issue

**Example of a good bug report:**
```
Title: [Bug]: Analysis fails with corrupted FLAC files on Windows 11

Description:
When analyzing corrupted FLAC files, the application crashes with
"OSError: [Errno 22] Invalid argument" on Windows 11.

Steps to Reproduce:
1. Download test file: corrupted_sample.flac
2. Run: flac-detective corrupted_sample.flac
3. Application crashes with error

Expected: Graceful error handling with diagnostic message
Actual: Application crashes

Environment:
- OS: Windows 11 22H2
- Python: 3.11.5
- FLAC Detective: 0.8.0
- Installation: pip

Logs: [attached]
```

### For Feature Requests

1. **Explain the problem:** Start with what limitation you're facing
2. **Describe the solution:** Be specific about what you want
3. **Provide use cases:** Show when and why this would be useful
4. **Show examples:** Include code snippets or mock-ups
5. **Consider impact:** Think about who else would benefit

**Example of a good feature request:**
```
Title: [Feature]: Add JSON export format for analysis results

Problem Statement:
Currently, FLAC Detective only outputs text reports. When integrating
with other tools or scripts, parsing text is error-prone and fragile.

Proposed Solution:
Add a --format json flag that outputs structured JSON:

flac-detective --format json /path/to/music > results.json

Use Cases:
1. Automating music library management
2. Integrating with web dashboards
3. Batch processing workflows
4. Data analysis with pandas/R

Example Output:
{
  "metadata": {...},
  "results": [
    {
      "filename": "song.flac",
      "score": 85,
      "verdict": "FAKE",
      ...
    }
  ]
}

Impact: Many users (common automation use case)
Priority: Important
```

### For Performance Issues

1. **Provide metrics:** Give concrete numbers (time, memory, CPU)
2. **Describe environment:** Include hardware specs
3. **Show comparison:** Compare to expected or previous performance
4. **Test isolation:** Rule out network/disk issues
5. **Profile if possible:** Include profiling data if available

---

## Template Structure

All templates use GitHub's YAML format with these components:

### Metadata
```yaml
name: Template Name
description: Template description
title: "[Category]: "
labels: ["label1", "label2"]
```

### Form Fields

**Text Input:**
```yaml
- type: input
  id: field_id
  attributes:
    label: Field Label
    description: Help text
    placeholder: Example text
  validations:
    required: true
```

**Text Area:**
```yaml
- type: textarea
  id: field_id
  attributes:
    label: Field Label
    description: Help text
    placeholder: Multi-line example
    render: shell  # Syntax highlighting
  validations:
    required: true
```

**Dropdown:**
```yaml
- type: dropdown
  id: field_id
  attributes:
    label: Select an option
    options:
      - Option 1
      - Option 2
      - Option 3
  validations:
    required: true
```

**Checkboxes:**
```yaml
- type: checkboxes
  id: field_id
  attributes:
    label: Checkbox label
    options:
      - label: Option 1
        required: true
      - label: Option 2
        required: false
```

---

## Customizing Templates

### For Project Maintainers

Templates are located in `.github/ISSUE_TEMPLATE/`:

```
.github/ISSUE_TEMPLATE/
├── bug_report.yml
├── feature_request.yml
├── performance_issue.yml
├── documentation.yml
├── question.yml
└── config.yml
```

### Template Configuration

The `config.yml` file controls:
- Whether blank issues are allowed
- Links to external resources (docs, discussions, etc.)

```yaml
blank_issues_enabled: false
contact_links:
  - name: Documentation
    url: https://flac-detective.readthedocs.io
    about: Read the full documentation
```

### Modifying Templates

1. Edit the YAML file in `.github/ISSUE_TEMPLATE/`
2. Test locally using GitHub's template preview
3. Commit and push changes
4. Templates update automatically on GitHub

### Testing Templates

Before deploying:
1. Use [GitHub's template validator](https://github.com/actions/toolkit/tree/main/packages/issue-form-validator)
2. Create a test issue on your fork
3. Verify all fields render correctly
4. Check required field validation

---

## Labels and Triage

### Automatic Labels

Templates automatically apply labels:

| Template | Labels |
|----------|--------|
| Bug Report | `bug`, `needs-triage` |
| Feature Request | `enhancement`, `needs-triage` |
| Performance Issue | `performance`, `needs-triage` |
| Documentation | `documentation` |
| Question | `question` |

### Triage Process

1. **needs-triage**: New issues awaiting review
2. **confirmed**: Issue verified and accepted
3. **duplicate**: Duplicate of existing issue
4. **wontfix**: Won't be implemented
5. **help-wanted**: Good for contributors

---

## Additional Resources

- [GitHub Issue Forms Documentation](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
- [GitHub Issue Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)
- [FLAC Detective Contributing Guide](../docs/development/CONTRIBUTING.md)

---

## Examples

### Good Issue Titles

✅ `[Bug]: Analysis crashes on corrupted FLAC files`
✅ `[Feature]: Add support for batch export to CSV`
✅ `[Performance]: Memory leak when analyzing large libraries`
✅ `[Docs]: Missing example for Python API integration`

### Poor Issue Titles

❌ `Bug`
❌ `Help!`
❌ `This doesn't work`
❌ `Question about thing`

---

## Contributing to Templates

We welcome improvements to issue templates!

To contribute:
1. Identify what's missing or unclear
2. Create a documentation issue or PR
3. Propose specific changes
4. Test the template locally

Templates should be:
- Clear and easy to understand
- Comprehensive but not overwhelming
- Helpful for both reporters and maintainers
- Consistent with existing templates

---

**Thank you for helping improve FLAC Detective! 🎵**
