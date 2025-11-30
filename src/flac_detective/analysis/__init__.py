"""FLAC file analysis module.

This module provides tools to analyze FLAC file quality
and detect potential MP3 transcoding.
"""

from .analyzer import FLACAnalyzer

__all__ = ["FLACAnalyzer"]
