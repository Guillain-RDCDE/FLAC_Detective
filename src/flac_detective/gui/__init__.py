"""Desktop GUI for FLAC Detective (PySide6).

A windowed front-end over the same :class:`flac_detective.analysis.FLACAnalyzer`
the CLI uses: pick a folder, watch a live progress bar, get a sortable verdict
table, and click any file to see its spectrum (with the detected cutoff marked)
and the reasons behind its verdict — including the fake-hi-res axis.

Launched via the ``flac-detective-gui`` entry point (``pip install
"flac-detective[gui]"``). The heavy Qt/matplotlib imports live in the submodules
so importing this package stays cheap; :func:`flac_detective.gui.app.main` is the
entry point and reports a friendly hint if PySide6 isn't installed.
"""

from __future__ import annotations
