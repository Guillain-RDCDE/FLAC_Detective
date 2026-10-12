#!/usr/bin/env python3
"""Simple runner for FLAC Detective that avoids LOGO encoding issues."""

import os
import sys

# Ensure UTF-8 encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")  # noqa: S605 - a fixed command, no input in it

# Add src to path
sys.path.insert(0, "src")

# Monkey-patch the LOGO to avoid encoding issues
import flac_detective.utils as utils

utils.LOGO = "\n=== FLAC DETECTIVE ===\n"

# Now run main
from flac_detective.main import main  # noqa: E402 - after the sys.path insert above

if __name__ == "__main__":
    main()
