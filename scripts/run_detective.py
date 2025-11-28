#!/usr/bin/env python3
"""
Script wrapper for FLAC Detective Analyzer
"""
import sys
from pathlib import Path

# Add src to path so we can import flac_detective
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from flac_detective.main import main

if __name__ == '__main__':
    main()
