"""Version information for FLAC Detective.

This is the single source of truth for the version number.
All other files should reference this file.
"""

__version__ = "0.9.7"
__version_info__ = tuple(int(x) for x in __version__.split("."))

# Release information
__release_date__ = "2026-05-25"
__release_name__ = "Circular Import & Docker Image Fix"

# Metadata
__author__ = "Guillain Méjane"
__email__ = "guillain@poulpe.us"
__license__ = "MIT"
__url__ = "https://github.com/Guillain-RDCDE/FLAC_Detective"
