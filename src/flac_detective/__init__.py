"""FLAC Detective - Advanced FLAC Authenticity Analyzer."""

from .analysis import FLACAnalyzer
from .reporting import ExcelReporter
from .tracker import ProgressTracker
from .utils import LOGO, find_flac_files

__version__ = "0.2.0"
