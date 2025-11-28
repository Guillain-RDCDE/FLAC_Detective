"""Utilitaires généraux pour l'application."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Logo FLAC Detective
LOGO = r"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                          🔍 FLAC DETECTIVE 🔍                             ║
║                                                                           ║
║              "Every FLAC file tells a story... I find the truth"          ║
║                                                                           ║
║   ┌─────────────────────────────────────────────────────────────┐        ║
║   │  📊 Spectral Analysis    │  ⏱️  Duration Check              │        ║
║   │  🎵 Energy Profiling     │  🏷️  Metadata Validation         │        ║
║   │  🔧 Auto Repair          │  💾 Smart Backup                 │        ║
║   └─────────────────────────────────────────────────────────────┘        ║
║                                                                           ║
║                         Version 4.0 - November 2025                       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""


def find_flac_files(root_dir: Path) -> List[Path]:
    """Trouve récursivement tous les fichiers .flac.

    Args:
        root_dir: Dossier racine à scanner.

    Returns:
        Liste des chemins vers les fichiers FLAC trouvés.
    """
    logger.info(f"🔍 Scan du dossier: {root_dir}")
    flac_files = list(root_dir.rglob("*.flac"))
    logger.info(f"📁 {len(flac_files)} fichiers FLAC trouvés")
    return flac_files
