"""Module d'analyse de fichiers FLAC (rétrocompatibilité).

Ce module maintient la rétrocompatibilité en important depuis le nouveau package analysis.
"""

from .analysis import FLACAnalyzer

__all__ = ["FLACAnalyzer"]
