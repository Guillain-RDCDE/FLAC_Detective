#!/usr/bin/env python3
"""
Quick script to check Codecov badge status and provide diagnostics.
"""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def check_badge_url(repo_owner="GuillainM", repo_name="FLAC_Detective", branch="main"):
    """Check if Codecov badge URL is accessible and returns valid data."""
    badge_url = f"https://codecov.io/gh/{repo_owner}/{repo_name}/branch/{branch}/graph/badge.svg"

    print(f"🔍 Checking Codecov badge URL...")
    print(f"   {badge_url}")
    print()

    try:
        req = Request(badge_url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        with urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')

            # Check if it's an SVG
            if '<svg' in content.lower():
                print("✅ Badge SVG is accessible")

                # Try to detect "unknown" in the SVG
                if 'unknown' in content.lower():
                    print("⚠️  Badge shows 'unknown' - no coverage data uploaded yet")
                    return False
                else:
                    # Try to find coverage percentage in SVG
                    if '%' in content:
                        print("✅ Badge shows coverage percentage!")
                        # Try to extract percentage (rough parsing)
                        for line in content.split('\n'):
                            if '%' in line and any(char.isdigit() for char in line):
                                print(f"   Coverage data found in badge")
                                return True
                    else:
                        print("⚠️  Badge exists but format is unexpected")
                        return None
            else:
                print("❌ Response is not an SVG")
                return False

    except HTTPError as e:
        print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False
    except URLError as e:
        print(f"❌ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_codecov_api(repo_owner="GuillainM", repo_name="FLAC_Detective"):
    """Check Codecov API for repository coverage data."""
    api_url = f"https://codecov.io/api/gh/{repo_owner}/{repo_name}"

    print()
    print(f"🔍 Checking Codecov API...")
    print(f"   {api_url}")
    print()

    try:
        req = Request(api_url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        req.add_header('Accept', 'application/json')

        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            if 'commit' in data:
                print("✅ Repository found on Codecov")

                commit = data.get('commit', {})
                totals = commit.get('totals', {})

                if totals:
                    coverage = totals.get('c', 'N/A')
                    print(f"   Latest coverage: {coverage}%")
                    print(f"   Commit: {commit.get('commitid', 'N/A')[:7]}")
                    print(f"   Branch: {commit.get('branch', 'N/A')}")
                    return True
                else:
                    print("⚠️  Repository found but no coverage data yet")
                    return False
            else:
                print("⚠️  Repository data format unexpected")
                return None

    except HTTPError as e:
        if e.code == 404:
            print("❌ Repository not found on Codecov")
            print("   Make sure the repository is added to Codecov")
        else:
            print(f"❌ HTTP Error: {e.code} - {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_local_files():
    """Check if local coverage files exist."""
    print()
    print("🔍 Checking local coverage files...")
    print()

    files_to_check = [
        ('coverage.xml', 'Coverage XML report'),
        ('htmlcov/index.html', 'HTML coverage report'),
        ('.coverage', 'Coverage data file'),
    ]

    any_exists = False
    for filepath, description in files_to_check:
        path = Path(filepath)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {description}: {filepath} ({size:,} bytes)")
            any_exists = True
        else:
            print(f"⚠️  {description}: {filepath} (not found)")

    return any_exists


def main():
    print("=" * 60)
    print("Codecov Configuration Status Check")
    print("=" * 60)
    print()

    # Check local files
    local_ok = check_local_files()

    # Check badge
    badge_ok = check_badge_url()

    # Check API
    api_ok = check_codecov_api()

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()

    if badge_ok and api_ok:
        print("✅ Codecov is fully configured and working!")
        print("   The badge should display coverage percentage.")
        return 0
    elif badge_ok is False and api_ok is False:
        print("❌ Codecov integration not working yet")
        print()
        print("Next steps:")
        print("1. Ensure Codecov GitHub App is installed and configured")
        print("2. Wait for CI to run and upload coverage")
        print("3. Check: https://github.com/GuillainM/FLAC_Detective/actions")
        return 1
    elif badge_ok is False and api_ok:
        print("⚠️  Codecov has data but badge shows 'unknown'")
        print("   This may be temporary - wait a few minutes and check again")
        return 0
    else:
        print("⚠️  Status unclear - check details above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
