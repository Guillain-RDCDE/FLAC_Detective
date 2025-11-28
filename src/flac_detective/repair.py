"""Module de réparation de fichiers FLAC (rétrocompatibilité).

Ce module maintient la rétrocompatibilité en important depuis le nouveau package repair.
"""

from .repair import FLACDurationFixer
from .repair.__main__ import main

__all__ = ["FLACDurationFixer", "main"]
