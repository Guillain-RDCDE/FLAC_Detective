"""General utilities for the application."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Logo FLAC Detective
from .colors import Colors, colorize

# Logo FLAC Detective
LOGO = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                          {Colors.BRIGHT_WHITE}FLAC DETECTIVE{Colors.CYAN}                                   ║
║                                                                           ║
║              "Every FLAC file tells a story... I find the truth"          ║
║                                                                           ║
║   ┌───────────────────────────────────────────────────────────┐           ║
║   │ {Colors.GREEN}Spectral Analysis{Colors.CYAN}         │ {Colors.GREEN}Duration Check{Colors.CYAN}              │           ║
║   │ {Colors.GREEN}Energy Profiling{Colors.CYAN}          │ {Colors.GREEN}Metadata Validation{Colors.CYAN}         │           ║
║   │ {Colors.GREEN}Auto Repair{Colors.CYAN}               │ {Colors.GREEN}Smart Backup{Colors.CYAN}                │           ║
║   └───────────────────────────────────────────────────────────┘           ║
║                                                                           ║
║                         Version 0.1 - November 2025                       ║
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
