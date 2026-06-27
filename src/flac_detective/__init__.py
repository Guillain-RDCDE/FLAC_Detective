"""FLAC Detective - Advanced FLAC Authenticity Analyzer.

This package provides tools for analyzing FLAC files to detect MP3-to-FLAC
transcodes and other audio quality issues.

Main Classes
------------
FLACAnalyzer : class
    Main analyzer for FLAC files that detects transcoding and quality issues.
ProgressTracker : class
    Tracks analysis progress and manages results across sessions.

Functions
---------
find_flac_files : function
    Recursively finds all FLAC files in a directory.

Attributes
----------
__version__ : str
    Current version of FLAC Detective.
LOGO : str
    ASCII art logo for the application.

Examples
--------
Basic usage for analyzing a single file:

>>> from flac_detective import FLACAnalyzer
>>> analyzer = FLACAnalyzer(sample_duration=30.0)
>>> result = analyzer.analyze_file('path/to/file.flac')
>>> print(f"{result['verdict']} (score {result['score']}/150)")

Analyzing multiple files with progress tracking:

>>> from flac_detective import FLACAnalyzer, ProgressTracker
>>> from pathlib import Path
>>>
>>> analyzer = FLACAnalyzer()
>>> tracker = ProgressTracker(progress_file=Path('progress.json'))
>>>
>>> for flac_file in Path('music').rglob('*.flac'):
...     if not tracker.is_processed(str(flac_file)):
...         result = analyzer.analyze_file(flac_file)
...         tracker.add_result(result)
...
>>> tracker.save()
>>> results = tracker.get_results()

See Also
--------
flac_detective.analysis.analyzer : Main analyzer implementation
flac_detective.repair.fixer : FLAC file repair functionality
flac_detective.reporting.text_reporter : Report generation
"""

from .__version__ import __version__

__all__ = [
    "FLACAnalyzer",
    "ProgressTracker",
    "find_flac_files",
    "LOGO",
    "__version__",
]


# Lazy re-exports (PEP 562). Importing FLACAnalyzer eagerly here pulled in the
# whole analysis stack (scipy, ~4.5s) on *any* `import flac_detective.*`,
# including the GUI shell that doesn't need it until you actually analyse. The
# public API (`from flac_detective import FLACAnalyzer`) is unchanged — the
# import just happens on first access instead of at package load.
def __getattr__(name: str):
    if name == "FLACAnalyzer":
        from .analysis import FLACAnalyzer

        return FLACAnalyzer
    if name == "ProgressTracker":
        from .tracker import ProgressTracker

        return ProgressTracker
    if name in ("LOGO", "find_flac_files"):
        from . import utils

        return getattr(utils, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
