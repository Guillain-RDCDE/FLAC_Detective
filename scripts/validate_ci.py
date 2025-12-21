#!/usr/bin/env python3
"""Validate CI workflow configuration."""

import sys
from pathlib import Path


def validate_yaml_syntax(file_path: Path) -> bool:
    """Basic YAML syntax validation."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Basic checks
        if not content.strip():
            print(f"[FAIL] {file_path} is empty")
            return False

        # Check for common YAML issues
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            # Check for tabs (YAML doesn't allow tabs)
            if "\t" in line:
                print(f"[FAIL] {file_path}:{i} contains tabs (use spaces)")
                return False

        print(f"[PASS] {file_path} - Basic syntax OK")
        return True

    except Exception as e:
        print(f"[FAIL] {file_path} - Error: {e}")
        return False


def check_ci_workflow(file_path: Path) -> bool:
    """Check CI workflow for required elements."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_elements = [
            "name:",
            "on:",
            "jobs:",
            "runs-on:",
            "steps:",
        ]

        missing = []
        for element in required_elements:
            if element not in content:
                missing.append(element)

        if missing:
            print(f"[FAIL] Missing required elements: {', '.join(missing)}")
            return False

        # Check for test matrix
        if "matrix:" in content:
            print("[PASS] Test matrix found")

        # Check for coverage
        if "coverage" in content.lower():
            print("[PASS] Coverage reporting configured")

        # Check for multiple Python versions
        if "3.8" in content and "3.12" in content:
            print("[PASS] Testing Python 3.8-3.12")

        # Check for multiple OS
        os_count = sum(1 for os in ["ubuntu", "windows", "macos"] if os in content.lower())
        if os_count >= 2:
            print(f"[PASS] Testing on {os_count} operating systems")

        return True

    except Exception as e:
        print(f"[FAIL] Error checking workflow: {e}")
        return False


def main():
    """Main validation function."""
    print("Validating CI workflow configuration\n")

    ci_file = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"

    if not ci_file.exists():
        print(f"[FAIL] CI workflow file not found: {ci_file}")
        sys.exit(1)

    # Validate syntax
    if not validate_yaml_syntax(ci_file):
        sys.exit(1)

    print()

    # Check CI workflow
    if not check_ci_workflow(ci_file):
        sys.exit(1)

    print("\nCI workflow validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
