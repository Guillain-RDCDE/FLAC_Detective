"""Ré-encodage de fichiers FLAC."""

import logging
import subprocess
from pathlib import Path

from ..config import repair_config

logger = logging.getLogger(__name__)


def check_flac_tool_available() -> bool:
    """Vérifie que l'outil 'flac' est disponible.

    Returns:
        True si l'outil est disponible, False sinon.
    """
    try:
        result = subprocess.run(
            ["flac", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _decode_to_wav(input_path: Path, temp_wav: Path) -> bool:
    """Décode un fichier FLAC en WAV temporaire.

    Args:
        input_path: Fichier FLAC source.
        temp_wav: Chemin du fichier WAV temporaire.

    Returns:
        True si succès, False sinon.
    """
    logger.debug("  Décodage en WAV temporaire...")
    decode_cmd = [
        "flac",
        "--decode",
        "--silent",
        "--output-name",
        str(temp_wav),
        str(input_path),
    ]

    result = subprocess.run(
        decode_cmd, capture_output=True, text=True, timeout=repair_config.REENCODE_TIMEOUT
    )

    if result.returncode != 0:
        logger.error(f"Erreur décodage: {result.stderr}")
        if temp_wav.exists():
            temp_wav.unlink()
        return False

    return True


def _encode_from_wav(temp_wav: Path, output_path: Path, compression_level: int) -> bool:
    """Encode un fichier WAV en FLAC.

    Args:
        temp_wav: Fichier WAV source.
        output_path: Fichier FLAC destination.
        compression_level: Niveau de compression (0-8).

    Returns:
        True si succès, False sinon.
    """
    logger.debug(f"  Re-encodage en FLAC (niveau {compression_level})...")
    encode_cmd = [
        "flac",
        f"-{compression_level}",
        "--verify",  # Vérification intégrité
        "--silent",
        "--output-name",
        str(output_path),
        str(temp_wav),
    ]

    result = subprocess.run(
        encode_cmd, capture_output=True, text=True, timeout=repair_config.REENCODE_TIMEOUT
    )

    if result.returncode != 0:
        logger.error(f"Erreur encodage: {result.stderr}")
        if output_path.exists():
            output_path.unlink()
        return False

    return True


def reencode_flac(
    input_path: Path, output_path: Path, compression_level: int | None = None
) -> bool:
    """Ré-encode un fichier FLAC avec l'outil officiel 'flac'.

    Args:
        input_path: Fichier source.
        output_path: Fichier destination.
        compression_level: 0-8 (8 = meilleure compression). Si None, utilise la config.

    Returns:
        True si succès, False sinon.
    """
    if compression_level is None:
        compression_level = repair_config.FLAC_COMPRESSION_LEVEL

    try:
        # Vérifier que l'outil 'flac' est disponible
        if not check_flac_tool_available():
            logger.error("L'outil 'flac' n'est pas installé. Installez-le avec:")
            logger.error("  Ubuntu/Debian: sudo apt install flac")
            logger.error("  macOS: brew install flac")
            logger.error("  Windows: Téléchargez depuis xiph.org")
            return False

        # Décodage en WAV temporaire
        temp_wav = output_path.with_suffix(".temp.wav")

        if not _decode_to_wav(input_path, temp_wav):
            return False

        # Re-encodage en FLAC
        success = _encode_from_wav(temp_wav, output_path, compression_level)

        # Nettoyage du WAV temporaire
        if temp_wav.exists():
            temp_wav.unlink()

        return success

    except subprocess.TimeoutExpired:
        logger.error("Timeout lors du ré-encodage (fichier trop long)")
        return False
    except Exception as e:
        logger.error(f"Erreur ré-encodage: {e}")
        return False
