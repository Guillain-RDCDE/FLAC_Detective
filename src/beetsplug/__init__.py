"""Namespace package so beets discovers plugins shipped by FLAC Detective.

Uses the pkgutil-style declaration so this ``beetsplug`` directory coexists with
``beetsplug`` directories provided by beets itself and by other installed plugins.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
