"""Module de génération de rapports Excel (rétrocompatibilité).

Ce module maintient la rétrocompatibilité en important depuis le nouveau package reporting.
"""

from .reporting import ExcelReporter

__all__ = ["ExcelReporter"]
