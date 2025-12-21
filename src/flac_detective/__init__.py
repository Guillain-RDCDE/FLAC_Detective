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
>>> print(f"Score: {result['score']}/100")

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
from .analysis import FLACAnalyzer
from .tracker import ProgressTracker
from .utils import LOGO, find_flac_files

__all__ = [
    "FLACAnalyzer",
    "ProgressTracker",
    "find_flac_files",
    "LOGO",
    "__version__",
]
