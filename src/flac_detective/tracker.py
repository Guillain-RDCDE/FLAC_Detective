"""Module de gestion de la progression de l'analyse."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Gestion de la progression et reprise après interruption."""

    def __init__(self, progress_file: Path | None = None):
        """Initialise le tracker.

        Args:
            progress_file: Chemin du fichier de progression (par défaut 'progress.json').
        """
        if progress_file is None:
            progress_file = Path("progress.json")
        self.progress_file = progress_file
        self.data: Dict = self._load()

    def _load(self) -> Dict:
        """Charge l'état de progression.

        Returns:
            Dictionnaire contenant l'état de la progression.
        """
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return dict(json.load(f))
            except Exception as e:
                logger.warning(f"Impossible de charger progress.json: {e}")

        return {
            "processed_files": [],
            "results": [],
            "total_files": 0,
            "current_index": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
        }

    def save(self):
        """Sauvegarde l'état actuel."""
        self.data["last_update"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur sauvegarde progress.json: {e}")

    def is_processed(self, filepath: str) -> bool:
        """Vérifie si un fichier a déjà été traité.

        Args:
            filepath: Chemin du fichier.

        Returns:
            True si le fichier a déjà été traité, False sinon.
        """
        return filepath in self.data["processed_files"]

    def add_result(self, result: Dict):
        """Ajoute un résultat d'analyse.

        Args:
            result: Dictionnaire contenant le résultat d'analyse.
        """
        self.data["results"].append(result)
        self.data["processed_files"].append(result["filepath"])
        self.data["current_index"] += 1

    def get_results(self) -> List[Dict]:
        """Retourne tous les résultats.

        Returns:
            Liste des résultats d'analyse.
        """
        return list(self.data["results"])

    def set_total(self, total: int):
        """Définit le nombre total de fichiers.

        Args:
            total: Nombre total de fichiers à traiter.
        """
        self.data["total_files"] = total

    def get_progress(self) -> Tuple[int, int]:
        """Retourne la progression actuelle.

        Returns:
            Tuple (fichiers traités, total).
        """
        return self.data["current_index"], self.data["total_files"]
