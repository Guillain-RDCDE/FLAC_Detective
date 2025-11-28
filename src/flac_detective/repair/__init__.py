"""Module de réparation de fichiers FLAC.

Ce module fournit des outils pour réparer automatiquement
les problèmes de durée dans les fichiers FLAC.
"""

from .fixer import FLACDurationFixer

__all__ = ["FLACDurationFixer"]
