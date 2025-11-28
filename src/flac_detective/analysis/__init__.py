"""Module d'analyse de fichiers FLAC.

Ce module fournit des outils pour analyser la qualité des fichiers FLAC
et détecter les transcodages MP3 potentiels.
"""

from .analyzer import FLACAnalyzer

__all__ = ["FLACAnalyzer"]
