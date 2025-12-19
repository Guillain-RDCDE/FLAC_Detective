#!/usr/bin/env python3
"""Simple runner for FLAC Detective that avoids LOGO encoding issues."""

import sys
import os

# Ensure UTF-8 encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")

# Add src to path
sys.path.insert(0, 'src')

# Monkey-patch the LOGO to avoid encoding issues
import flac_detective.utils as utils
utils.LOGO = "\n=== FLAC DETECTIVE ===\n"

# Now run main
from flac_detective.main import main

if __name__ == "__main__":
    main()
