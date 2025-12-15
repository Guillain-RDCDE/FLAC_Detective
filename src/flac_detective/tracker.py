"""Analysis progress management module."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization.

    Args:
        obj: Object that may contain numpy types.

    Returns:
        Object with numpy types converted to Python native types.
    """
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj


class ProgressTracker:
    """Progress management and resume after interruption."""

    def __init__(self, progress_file: Path | None = None):
        """Initializes the tracker.

        Args:
            progress_file: Path to progress file (default 'progress.json').
        """
        if progress_file is None:
            progress_file = Path("progress.json")
        self.progress_file = progress_file
        self.data: Dict = self._load()

    def _load(self) -> Dict:
        """Loads progress state.

        Returns:
            Dictionary containing progress state.
        """
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return dict(json.load(f))
            except Exception as e:
                logger.warning(f"Unable to load progress.json: {e}")

        return {
            "processed_files": [],
            "results": [],
            "total_files": 0,
            "current_index": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
        }

    def save(self):
        """Saves current state."""
        self.data["last_update"] = datetime.now().isoformat()
        try:
            # Convert numpy types to Python native types before serialization
            data_to_save = _convert_numpy_types(self.data)
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving progress.json: {e}")

    def is_processed(self, filepath: str) -> bool:
        """Checks if a file has already been processed.

        Args:
            filepath: File path.

        Returns:
            True if file has already been processed, False otherwise.
        """
        return filepath in self.data["processed_files"]

    def add_result(self, result: Dict):
        """Adds an analysis result.

        Args:
            result: Dictionary containing analysis result.
        """
        self.data["results"].append(result)
        self.data["processed_files"].append(result["filepath"])
        self.data["current_index"] += 1

    def get_results(self) -> List[Dict]:
        """Returns all results.

        Returns:
            List of analysis results.
        """
        return list(self.data["results"])

    def set_total(self, total: int):
        """Sets total number of files.

        Args:
            total: Total number of files to process.
        """
        self.data["total_files"] = total

    def get_progress(self) -> Tuple[int, int]:
        """Returns current progress.

        Returns:
            Tuple (processed files, total).
        """
        return self.data["current_index"], self.data["total_files"]

    def cleanup(self):
        """Deletes the progress file after successful completion."""
        if self.progress_file.exists():
            try:
                self.progress_file.unlink()
                logger.info(f"Progress file deleted: {self.progress_file}")
            except Exception as e:
                logger.warning(f"Unable to delete progress file: {e}")
