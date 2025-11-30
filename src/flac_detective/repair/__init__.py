"""FLAC file repair module.

This module provides tools to automatically repair
duration issues in FLAC files.
"""

from .fixer import FLACDurationFixer

__all__ = ["FLACDurationFixer"]
