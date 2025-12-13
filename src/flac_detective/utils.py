"""General utilities for the application."""

import logging
from pathlib import Path
from typing import List

from .colors import Colors
from .__version__ import __version__, __release_date__

logger = logging.getLogger(__name__)

# Parse release date for display
try:
    from datetime import datetime
    _dt = datetime.strptime(__release_date__, "%Y-%m-%d")
    _date_str = _dt.strftime("%B %Y")
except (ValueError, ImportError):
    _date_str = __release_date__

_version_str = f"Version {__version__} - {_date_str}"
# Center version string in 75 characters width
_padding = 75 - len(_version_str)
_left_pad = " " * (_padding // 2)
_right_pad = " " * (_padding - len(_left_pad))
_version_line = f"{_left_pad}{_version_str}{_right_pad}"

# Logo FLAC Detective
LOGO = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                          {Colors.BRIGHT_WHITE}FLAC DETECTIVE{Colors.CYAN}                                   ║
║                                                                           ║
║              "Every FLAC file tells a story... I find the truth"          ║
║                                                                           ║
║   ┌─────────────────────────────────────────────────────────────────────┐ ║
║   │ {Colors.GREEN}Spectral Analysis{Colors.CYAN}         │ {Colors.GREEN}Duration Check{Colors.CYAN}                          │ ║
║   │ {Colors.GREEN}Energy Profiling{Colors.CYAN}          │ {Colors.GREEN}Metadata Validation{Colors.CYAN}                     │ ║
║   │ {Colors.GREEN}Auto Repair{Colors.CYAN}               │ {Colors.GREEN}Smart Backup{Colors.CYAN}                            │ ║
║   └─────────────────────────────────────────────────────────────────────┘ ║
║                                                                           ║
║{_version_line}║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""


def find_flac_files(root_dir: Path) -> List[Path]:
    """Recursively finds all .flac files.

    Args:
        root_dir: Root directory to scan.

    Returns:
        List of paths to found FLAC files.
    """
    logger.info(f"Scanning folder: {root_dir}")
    flac_files = list(root_dir.rglob("*.flac"))
    logger.info(f"{len(flac_files)} FLAC files found")
    return flac_files


def find_non_flac_audio_files(root_dir: Path) -> List[Path]:
    """Recursively finds all non-FLAC audio files (MP3, M4A, AAC, OGG, WMA, etc.).

    Args:
        root_dir: Root directory to scan.

    Returns:
        List of paths to found non-FLAC audio files.
    """
    logger.info(f"Scanning for non-FLAC audio files in: {root_dir}")

    # Common lossy audio formats
    extensions = ["*.mp3", "*.m4a", "*.aac", "*.ogg", "*.wma", "*.opus", "*.ape"]

    non_flac_files = []
    for ext in extensions:
        files = list(root_dir.rglob(ext))
        non_flac_files.extend(files)

    logger.info(f"{len(non_flac_files)} non-FLAC audio files found")
    return non_flac_files
