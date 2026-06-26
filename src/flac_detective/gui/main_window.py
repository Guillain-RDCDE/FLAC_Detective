"""The main FLAC Detective window: pick → scan → triage table → per-file detail.

A thin Qt shell over the analysis pipeline. All heavy lifting happens in
:class:`flac_detective.gui.worker.AnalysisWorker`; this module is layout, the
results table, the detail panel, and report export via the existing reporters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..__version__ import __version__
from ..reporting import CSVReporter, HTMLReporter
from ..utils import find_flac_files, find_non_flac_audio_files
from .spectrum_view import SpectrumView
from .worker import AnalysisWorker

# Lossless extensions the GUI will pick up from a dropped/selected folder.
_AUDIO_GLOB_EXTS = (".flac", ".wav", ".m4a", ".ape")

# Verdict -> (display label, row background). One source of truth for the table colours.
_VERDICT_STYLE = {
    "FAKE_CERTAIN": ("❌ FAKE", QColor(120, 30, 30)),
    "SUSPICIOUS": ("⚠ SUSPICIOUS", QColor(120, 80, 20)),
    "WARNING": ("❓ WARNING", QColor(90, 80, 20)),
    "AUTHENTIC": ("✅ AUTHENTIC", QColor(25, 70, 35)),
    "NON_FLAC": ("🚫 NON-FLAC", QColor(70, 30, 80)),
    "ERROR": ("⁉ ERROR", QColor(60, 60, 60)),
}

_HIRES_LABEL = {
    "UPSAMPLED": "⬆ Upsampled",
    "PADDED_DEPTH": "▭ Padded depth",
    "UPSAMPLED_AND_PADDED": "⬆▭ Upsampled+Padded",
    "GENUINE_HIRES": "✓ Genuine hi-res",
    "NOT_HIRES": "",
    "UNKNOWN": "",
    "": "",
}

_COLUMNS = ["Verdict", "Score", "Hi-Res", "Sample rate", "Depth", "Cutoff", "File"]


def _num_item(value: float) -> QTableWidgetItem:
    """A right-aligned table item that sorts numerically, not lexically."""
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.DisplayRole, value)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _text_item(text: str) -> QTableWidgetItem:
    """A non-editable text table item."""
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class MainWindow(QMainWindow):
    """Top-level window: target picker, progress, results table, detail panel."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"FLAC Detective {__version__}")
        self.resize(1100, 720)
        self.setAcceptDrops(True)

        self._targets: List[Path] = []
        self._results: List[Dict[str, Any]] = []
        self._worker: Optional[AnalysisWorker] = None

        self._build_ui()
        self._set_running(False)

    # ---------------------------------------------------------------- UI build
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- top controls -----------------------------------------------------
        controls = QHBoxLayout()
        self._pick_folder_btn = QPushButton("Choose folder…")
        self._pick_folder_btn.clicked.connect(self._choose_folder)
        self._pick_files_btn = QPushButton("Choose files…")
        self._pick_files_btn.clicked.connect(self._choose_files)
        controls.addWidget(self._pick_folder_btn)
        controls.addWidget(self._pick_files_btn)

        controls.addSpacing(16)
        controls.addWidget(QLabel("Sample (s):"))
        self._duration_spin = QDoubleSpinBox()
        self._duration_spin.setRange(5.0, 120.0)
        self._duration_spin.setValue(30.0)
        self._duration_spin.setToolTip("Audio sampled per file. Higher = slower but more robust.")
        controls.addWidget(self._duration_spin)

        self._deep_check = QCheckBox("Deep (run CNN on every file)")
        self._deep_check.setToolTip(
            "Run the ML rule on every file, catching high-bitrate AAC/Vorbis transcodes "
            "the fast path skips. Slower."
        )
        controls.addWidget(self._deep_check)

        controls.addStretch(1)
        self._analyse_btn = QPushButton("▶ Analyse")
        self._analyse_btn.clicked.connect(self._start_analysis)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._cancel_analysis)
        self._export_btn = QPushButton("Export…")
        self._export_btn.clicked.connect(self._export_report)
        controls.addWidget(self._analyse_btn)
        controls.addWidget(self._cancel_btn)
        controls.addWidget(self._export_btn)
        root.addLayout(controls)

        # --- target / status line --------------------------------------------
        self._target_label = QLabel("Drop a folder or files here, or use the buttons above.")
        self._target_label.setStyleSheet("color: #888;")
        root.addWidget(self._target_label)

        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        root.addWidget(self._progress)

        # --- splitter: table | detail ----------------------------------------
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        self._table.horizontalHeader().setSectionResizeMode(
            len(_COLUMNS) - 1, QHeaderView.ResizeMode.Stretch
        )
        splitter.addWidget(self._table)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self._spectrum = SpectrumView()
        detail_layout.addWidget(self._spectrum, stretch=2)
        self._reasons = QTextEdit()
        self._reasons.setReadOnly(True)
        self._reasons.setPlaceholderText("Per-file verdict details appear here.")
        detail_layout.addWidget(self._reasons, stretch=1)
        splitter.addWidget(detail)
        splitter.setSizes([620, 480])
        root.addWidget(splitter, stretch=1)

        # --- summary ----------------------------------------------------------
        self._summary_label = QLabel("")
        root.addWidget(self._summary_label)

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Accept drags that carry file/folder URLs."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Set dropped folders/files as the scan targets."""
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        paths = [p for p in paths if p.exists()]
        if paths:
            self._set_targets(paths)

    # ------------------------------------------------------------- target pick
    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder to scan")
        if folder:
            self._set_targets([Path(folder)])

    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Choose audio files", "", "Audio (*.flac *.wav *.m4a *.ape);;All files (*)"
        )
        if files:
            self._set_targets([Path(f) for f in files])

    def _set_targets(self, paths: List[Path]) -> None:
        self._targets = paths
        if len(paths) == 1 and paths[0].is_dir():
            self._target_label.setText(f"Target: {paths[0]}")
        else:
            self._target_label.setText(f"Target: {len(paths)} item(s) selected")
        self._target_label.setStyleSheet("color: #ddd;")

    def _collect_files(self) -> List[Path]:
        """Expand the chosen targets into a flat list of analysable audio files."""
        files: List[Path] = []
        for target in self._targets:
            if target.is_file():
                if target.suffix.lower() in _AUDIO_GLOB_EXTS:
                    files.append(target)
            elif target.is_dir():
                files.extend(find_flac_files(target))
                files.extend(sorted(target.rglob("*.wav")))
                files.extend(find_non_flac_audio_files(target))
        # De-duplicate, preserve order.
        seen, unique = set(), []
        for f in files:
            key = str(f).lower()
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    # --------------------------------------------------------------- analysis
    def _start_analysis(self) -> None:
        if self._worker is not None:
            return
        files = self._collect_files()
        if not files:
            QMessageBox.information(self, "Nothing to analyse", "No audio files in the selection.")
            return

        self._results.clear()
        self._table.setRowCount(0)
        self._reasons.clear()
        self._spectrum.clear("Analysing…")
        self._summary_label.setText("")
        self._progress.setRange(0, len(files))
        self._progress.setValue(0)

        self._worker = AnalysisWorker(
            files, self._duration_spin.value(), self._deep_check.isChecked()
        )
        self._worker.result.connect(self._on_result)
        self._worker.progress.connect(self._on_progress)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished_ok.connect(self._on_finished)
        self._set_running(True)
        self._worker.start()

    def _cancel_analysis(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._target_label.setText("Cancelling… (finishing in-flight files)")

    def _on_progress(self, done: int, total: int) -> None:
        self._progress.setValue(done)
        self._progress.setFormat(f"{done}/{total} files")

    def _on_result(self, result: Dict[str, Any]) -> None:
        self._results.append(result)
        self._append_row(result)

    def _on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Analysis failed", message)
        self._teardown_worker()

    def _on_finished(self, cancelled: bool) -> None:
        self._update_summary(cancelled)
        self._teardown_worker()

    def _teardown_worker(self) -> None:
        if self._worker is not None:
            self._worker.wait()
            self._worker = None
        self._set_running(False)

    def _set_running(self, running: bool) -> None:
        self._analyse_btn.setEnabled(not running)
        self._cancel_btn.setEnabled(running)
        self._pick_folder_btn.setEnabled(not running)
        self._pick_files_btn.setEnabled(not running)
        self._export_btn.setEnabled(not running and bool(self._results))

    # ------------------------------------------------------------ table & view
    def _append_row(self, r: Dict[str, Any]) -> None:
        verdict = r.get("verdict", "ERROR")
        label, colour = _VERDICT_STYLE.get(verdict, (verdict, None))
        was_sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)  # avoid re-sort mid-insert shuffling rows

        row = self._table.rowCount()
        self._table.insertRow(row)

        cutoff = r.get("cutoff_freq")
        cutoff_khz = cutoff / 1000.0 if isinstance(cutoff, (int, float)) and cutoff else 0.0
        hires = r.get("hires_verdict", "")
        cells = [
            _text_item(label),
            _num_item(int(r.get("score", 0) or 0)),
            _text_item(_HIRES_LABEL.get(hires, hires)),
            _text_item(str(r.get("sample_rate", ""))),
            _text_item(str(r.get("bit_depth", ""))),
            _num_item(round(cutoff_khz, 1)),
            _text_item(r.get("filename", "")),
        ]
        # Stash the full result on the first cell so selection can recover it.
        cells[0].setData(Qt.ItemDataRole.UserRole, r)
        for col, item in enumerate(cells):
            if colour is not None:
                item.setBackground(colour)
            self._table.setItem(row, col, item)

        self._table.setSortingEnabled(was_sorting)

    def _on_row_selected(self) -> None:
        items = self._table.selectedItems()
        if not items:
            return
        cell = self._table.item(items[0].row(), 0)
        result = cell.data(Qt.ItemDataRole.UserRole) if cell is not None else None
        if not result:
            return
        self._spectrum.show_file(result)
        self._show_reasons(result)

    def _show_reasons(self, r: Dict[str, Any]) -> None:
        lines = [
            f"<b>{r.get('filename', '')}</b>",
            f"Verdict: <b>{r.get('verdict', '')}</b> (score {r.get('score', 0)}/150)",
        ]
        hires = r.get("hires_verdict", "")
        if hires and hires not in ("NOT_HIRES", "UNKNOWN"):
            lines.append(f"Hi-res: <b>{hires}</b>")
            if r.get("hires_reason"):
                lines.append(f"<i>{r['hires_reason']}</i>")
        lines.append("")
        lines.append("<u>Scoring reasons</u>:")
        reason = str(r.get("reason", "") or "No anomaly detected")
        for part in reason.split(" | "):
            lines.append(f"• {part}")
        self._reasons.setHtml("<br>".join(lines))

    def _update_summary(self, cancelled: bool) -> None:
        n = len(self._results)
        fakes = sum(1 for r in self._results if r.get("verdict") == "FAKE_CERTAIN")
        suspicious = sum(1 for r in self._results if r.get("verdict") == "SUSPICIOUS")
        fake_hires = sum(
            1
            for r in self._results
            if r.get("hires_verdict") in ("UPSAMPLED", "PADDED_DEPTH", "UPSAMPLED_AND_PADDED")
        )
        prefix = "Cancelled — " if cancelled else "Done — "
        self._summary_label.setText(
            f"{prefix}{n} analysed · {fakes} fake · {suspicious} suspicious · "
            f"{fake_hires} fake hi-res"
        )
        self._export_btn.setEnabled(bool(self._results))

    # --------------------------------------------------------------- export
    def _export_report(self) -> None:
        if not self._results:
            return
        path, selected = QFileDialog.getSaveFileName(
            self,
            "Export report",
            "flac_report.html",
            "HTML report (*.html);;CSV triage (*.csv);;JSON (*.json)",
        )
        if not path:
            return
        out = Path(path)
        try:
            if out.suffix.lower() == ".csv" or "CSV" in selected:
                CSVReporter().generate_report(self._results, out)
            elif out.suffix.lower() == ".json" or "JSON" in selected:
                import json

                with open(out, "w", encoding="utf-8") as fh:
                    json.dump({"results": self._results}, fh, indent=2, default=str)
            else:
                HTMLReporter().generate_report(self._results, out)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Exported", f"Report written to:\n{out}")
