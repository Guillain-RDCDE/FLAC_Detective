#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate GitHub Actions workflow YAML files.

This script checks workflow files for syntax errors and common issues.

Usage:
    python scripts/validate_workflows.py
"""

import io
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

try:
    import yaml
except ImportError:
    print("⚠️  PyYAML not installed. Installing...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml


def validate_workflow(workflow_path):
    """Validate a single workflow file."""
    print(f"\n📋 Validating {workflow_path.name}...")

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)

        # Check required top-level keys
        if "name" not in content:
            print(f"  ⚠️  Missing 'name' field")
        else:
            print(f"  ✅ Name: {content['name']}")

        # Check 'on' field (YAML preserves it as string key)
        trigger_key = "on" if "on" in content else True if True in content else None
        if trigger_key is None:
            print(f"  ❌ ERROR: Missing 'on' (trigger) field")
            return False
        else:
            triggers = content.get("on") or content.get(True)
            if isinstance(triggers, dict):
                print(f"  ✅ Triggers: {list(triggers.keys())}")
            else:
                print(f"  ✅ Triggers: {triggers}")

        if "jobs" not in content:
            print(f"  ❌ ERROR: Missing 'jobs' field")
            return False
        else:
            job_count = len(content["jobs"])
            print(f"  ✅ Jobs: {job_count} ({', '.join(content['jobs'].keys())})")

        # Validate each job
        for job_name, job_config in content["jobs"].items():
            if "runs-on" not in job_config and "uses" not in job_config:
                print(f"  ⚠️  Job '{job_name}' missing 'runs-on' or 'uses'")

            if "steps" in job_config:
                step_count = len(job_config["steps"])
                print(f"  ✅ Job '{job_name}': {step_count} steps")

        print(f"  ✅ {workflow_path.name} is valid")
        return True

    except yaml.YAMLError as e:
        print(f"  ❌ ERROR: YAML syntax error")
        print(f"     {e}")
        return False

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False


def main():
    print("🔍 GitHub Actions Workflow Validator")
    print("=" * 70)

    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        print(f"❌ ERROR: Directory {workflows_dir} not found")
        sys.exit(1)

    # Find all YAML workflow files
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    if not workflow_files:
        print(f"⚠️  No workflow files found in {workflows_dir}")
        sys.exit(0)

    print(f"\nFound {len(workflow_files)} workflow file(s)")

    # Validate each workflow
    results = {}
    for workflow_file in workflow_files:
        results[workflow_file.name] = validate_workflow(workflow_file)

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    valid_count = sum(results.values())
    total_count = len(results)

    for name, valid in results.items():
        status = "✅ VALID" if valid else "❌ INVALID"
        print(f"{status}: {name}")

    print(f"\nResult: {valid_count}/{total_count} workflows valid")

    if valid_count == total_count:
        print("\n✅ All workflows are valid!")
        sys.exit(0)
    else:
        print("\n❌ Some workflows have errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
