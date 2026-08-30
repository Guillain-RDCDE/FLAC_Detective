"""The main FLAC Detective window: pick → scan → triage table → per-file detail.

A thin Qt shell over the analysis pipeline. All heavy lifting happens in
:class:`flac_detective.gui.worker.AnalysisWorker`; this module is layout, the
results table, the detail card, and report export via the existing reporters.

The look is driven by :mod:`flac_detective.gui.style` — light, calm, spacious.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..__version__ import __version__
from ..presentation import plain_explanation, verdict_plain
from ..utils import find_flac_files, find_non_flac_audio_files
from . import style

if TYPE_CHECKING:  # imported lazily at runtime (heavy scipy / matplotlib imports)
    from .spectrum_view import SpectrumView
    from .worker import AnalysisWorker

# NOTE: the heavy modules — the analysis stack (scipy, ~4.5s) via .worker, the
# plotting (matplotlib, ~1.5s) via .spectrum_view, and the reporters — are
# imported lazily, inside the methods that first need them. This keeps the
# window itself near-instant to show; the cost is paid on first analyse/select,
# where a short wait reads as work, not as a slow launch.

# Lossless extensions the GUI will pick up from a dropped/selected folder.
_AUDIO_GLOB_EXTS = (".flac", ".wav", ".m4a", ".ape")

_HIRES_LABEL = {
    "UPSAMPLED": "Upsampled",
    "PADDED_DEPTH": "Padded depth",
    "UPSAMPLED_AND_PADDED": "Upsampled + padded",
    "GENUINE_HIRES": "Genuine hi-res",
    "NOT_HIRES": "—",
    "UNKNOWN": "—",
    "": "—",
}

# A deliberately lean triage table — the technical numbers live in the detail
# card on the right, not repeated as columns here.
_COLUMNS = ["Verdict", "File", "Score", "Hi-Res"]
_COL_VERDICT, _COL_FILE, _COL_SCORE, _COL_HIRES = 0, 1, 2, 3


def _num_item(value: float) -> QTableWidgetItem:
    """A right-aligned table item that sorts numerically, not lexically."""
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.DisplayRole, value)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setForeground(QColor(style.TEXT_SECONDARY))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _text_item(text: str, *, secondary: bool = False) -> QTableWidgetItem:
    """A non-editable text table item."""
    item = QTableWidgetItem(text)
    if secondary:
        item.setForeground(QColor(style.TEXT_SECONDARY))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class MainWindow(QMainWindow):
    """Top-level window: target picker, progress, results table, detail card."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FLAC Detective")
        self.resize(1180, 760)
        self.setMinimumSize(900, 560)
        self.setAcceptDrops(True)

        self._targets: List[Path] = []
        self._results: List[Dict[str, Any]] = []
        self._worker: Optional[AnalysisWorker] = None
        self._advanced = False  # easy mode by default — hide the plumbing
        self._selected: Optional[Dict[str, Any]] = None

        self._build_ui()
        self._set_running(False)
        self._show_empty_detail()
        self._apply_mode()

    # ---------------------------------------------------------------- UI build
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        root.addLayout(self._build_header())
        root.addLayout(self._build_toolbar())

        # Drop / status hint + thin progress bar.
        self._target_label = QLabel("Drop a folder or audio files here, or use the buttons above.")
        self._target_label.setObjectName("secondary")
        root.addWidget(self._target_label)

        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

        # Main split: results table | detail card.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(14)
        splitter.addWidget(self._build_table())
        splitter.addWidget(self._build_detail())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([680, 460])
        root.addWidget(splitter, stretch=1)

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summary")
        root.addWidget(self._summary_label)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        title = QLabel("FLAC Detective")
        title.setObjectName("title")
        version = QLabel(f"v{__version__}")
        version.setObjectName("secondary")
        header.addWidget(title)
        header.addWidget(version)
        header.addStretch(1)
        return header

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self._pick_folder_btn = QPushButton("Choose folder…")
        self._pick_folder_btn.clicked.connect(self._choose_folder)
        self._pick_files_btn = QPushButton("Choose files…")
        self._pick_files_btn.clicked.connect(self._choose_files)
        bar.addWidget(self._pick_folder_btn)
        bar.addWidget(self._pick_files_btn)

        bar.addSpacing(8)
        sample_lbl = QLabel("Sample")
        sample_lbl.setObjectName("secondary")
        bar.addWidget(sample_lbl)
        self._duration_spin = QDoubleSpinBox()
        self._duration_spin.setRange(5.0, 120.0)
        self._duration_spin.setValue(30.0)
        self._duration_spin.setSuffix(" s")
        self._duration_spin.setToolTip("Audio sampled per file. Higher = slower but more robust.")
        bar.addWidget(self._duration_spin)

        self._deep_check = QCheckBox("Deep scan")
        self._deep_check.setToolTip(
            "Run the ML rule on every file, catching high-bitrate AAC/Vorbis transcodes "
            "the fast path skips. Slower."
        )
        bar.addWidget(self._deep_check)

        self._advanced_check = QCheckBox("Advanced")
        self._advanced_check.setToolTip(
            "Show the plumbing: numeric scores, sample rate / bit depth / cutoff, and the "
            "per-rule reasoning. Off = plain-language verdicts and actions."
        )
        self._advanced_check.toggled.connect(self._on_advanced_toggled)
        bar.addWidget(self._advanced_check)

        bar.addStretch(1)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("danger")
        self._cancel_btn.clicked.connect(self._cancel_analysis)
        self._export_btn = QPushButton("Export…")
        self._export_btn.clicked.connect(self._export_report)
        self._analyse_btn = QPushButton("Analyse")
        self._analyse_btn.setObjectName("primary")
        self._analyse_btn.clicked.connect(self._start_analysis)
        bar.addWidget(self._cancel_btn)
        bar.addWidget(self._export_btn)
        bar.addWidget(self._analyse_btn)
        return bar

    def _build_table(self) -> QWidget:
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(40)
        self._table.itemSelectionChanged.connect(self._on_row_selected)

        header = self._table.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(_COL_VERDICT, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_FILE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_SCORE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_HIRES, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(_COL_SCORE, 80)
        # Worst offenders first; the user can re-sort by clicking any header.
        self._table.sortByColumn(_COL_SCORE, Qt.SortOrder.DescendingOrder)
        return self._table

    def _build_detail(self) -> QWidget:
        """The right-hand card: a stacked empty-state / file-detail view."""
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(360)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)

        self._detail_stack = QStackedWidget()
        outer.addWidget(self._detail_stack)

        # --- empty state ---------------------------------------------------
        empty = QWidget()
        empty_l = QVBoxLayout(empty)
        empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph = QLabel("🔎")
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph.setStyleSheet("font-size: 40px;")
        hint = QLabel("Select a file")
        hint.setObjectName("title")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Its verdict, metadata and spectrum appear here.")
        sub.setObjectName("secondary")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_l.addWidget(glyph)
        empty_l.addSpacing(6)
        empty_l.addWidget(hint)
        empty_l.addWidget(sub)
        self._detail_stack.addWidget(empty)

        # --- populated detail (scrollable) --------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        d = QVBoxLayout(body)
        d.setContentsMargins(20, 20, 20, 20)
        d.setSpacing(12)

        self._detail_name = QLabel("")
        self._detail_name.setObjectName("title")
        self._detail_name.setWordWrap(True)
        d.addWidget(self._detail_name)

        self._detail_path = QLabel("")
        self._detail_path.setObjectName("secondary")
        self._detail_path.setWordWrap(True)
        d.addWidget(self._detail_path)

        self._verdict_pill = QLabel("")
        self._verdict_pill.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        d.addWidget(self._verdict_pill)

        # metadata grid
        self._meta_grid = QGridLayout()
        self._meta_grid.setHorizontalSpacing(18)
        self._meta_grid.setVerticalSpacing(8)
        self._meta_grid.setColumnStretch(1, 1)
        d.addLayout(self._meta_grid)

        d.addSpacing(4)
        spectrum_lbl = QLabel("SPECTRUM")
        spectrum_lbl.setObjectName("sectionLabel")
        d.addWidget(spectrum_lbl)
        # The matplotlib-backed SpectrumView is created lazily on first file
        # selection (see _populate_detail) so launch never pays the import.
        self._spectrum: Optional["SpectrumView"] = None
        self._spectrum_holder = QVBoxLayout()
        self._spectrum_holder.setContentsMargins(0, 0, 0, 0)
        d.addLayout(self._spectrum_holder)

        reasons_lbl = QLabel("WHY")
        reasons_lbl.setObjectName("sectionLabel")
        d.addWidget(reasons_lbl)
        self._reasons = QTextEdit()
        self._reasons.setReadOnly(True)
        self._reasons.setFrameShape(QFrame.Shape.NoFrame)
        d.addWidget(self._reasons)

        d.addStretch(1)
        scroll.setWidget(body)
        self._detail_stack.addWidget(scroll)
        return card

    def _show_empty_detail(self) -> None:
        self._detail_stack.setCurrentIndex(0)

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
            self._target_label.setText(f"Target:  {paths[0]}")
        else:
            self._target_label.setText(f"Target:  {len(paths)} item(s) selected")

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
        self._show_empty_detail()
        self._summary_label.setText("")
        self._progress.setRange(0, len(files))
        self._progress.setValue(0)

        from .worker import AnalysisWorker  # heavy (scipy) — imported on first run

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
        self._target_label.setText(f"Analysing…  {done} / {total} files")

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
        self._cancel_btn.setVisible(running)
        self._pick_folder_btn.setEnabled(not running)
        self._pick_files_btn.setEnabled(not running)
        self._export_btn.setEnabled(not running and bool(self._results))

    # ------------------------------------------------------------ easy/advanced
    def _on_advanced_toggled(self, checked: bool) -> None:
        self._advanced = checked
        self._apply_mode()

    def _apply_mode(self) -> None:
        """Show/hide the plumbing for the current Easy/Advanced setting."""
        # The numeric Score column is plumbing — hidden in easy mode.
        self._table.setColumnHidden(_COL_SCORE, not self._advanced)
        # Re-render the open detail card so the pill/meta/reasons follow the mode.
        if self._selected is not None:
            self._populate_detail(self._selected)

    # ------------------------------------------------------------ table & view
    def _append_row(self, r: Dict[str, Any]) -> None:
        verdict = r.get("verdict", "ERROR")
        text_colour, pill_bg, label = style.verdict_theme(verdict)
        was_sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)  # avoid re-sort mid-insert shuffling rows

        row = self._table.rowCount()
        self._table.insertRow(row)

        hires = r.get("hires_verdict", "")

        verdict_item = _text_item(label)
        verdict_item.setForeground(QColor(text_colour))
        verdict_item.setBackground(QColor(pill_bg))
        font = verdict_item.font()
        font.setWeight(font.Weight.DemiBold)
        verdict_item.setFont(font)

        file_item = _text_item(r.get("filename", ""))
        file_item.setData(Qt.ItemDataRole.UserRole, r)  # stash result for selection

        cells = {
            _COL_VERDICT: verdict_item,
            _COL_FILE: file_item,
            # A missing score is not 0. 0 is AUTHENTIC, the most reassuring value in
            # the table, so `or 0` displayed an absence as a clean bill of health.
            _COL_SCORE: (
                _num_item(int(r["score"])) if r.get("score") is not None else QTableWidgetItem("—")
            ),
            _COL_HIRES: _text_item(_HIRES_LABEL.get(hires, hires), secondary=True),
        }
        for col, item in cells.items():
            self._table.setItem(row, col, item)

        self._table.setSortingEnabled(was_sorting)

    def _on_row_selected(self) -> None:
        items = self._table.selectedItems()
        if not items:
            return
        file_cell = self._table.item(items[0].row(), _COL_FILE)
        result = file_cell.data(Qt.ItemDataRole.UserRole) if file_cell is not None else None
        if not result:
            return
        self._populate_detail(result)

    # --------------------------------------------------------------- detail
    def _populate_detail(self, r: Dict[str, Any]) -> None:
        self._selected = r
        verdict = r.get("verdict", "")
        text_colour, pill_bg, label = style.verdict_theme(verdict)

        self._detail_name.setText(r.get("filename", ""))
        filepath = str(r.get("filepath", ""))
        self._detail_path.setText(str(Path(filepath).parent) if filepath else "")

        # Easy mode hides the 0-150 score; advanced shows it.
        pill_text = (
            f"  {label}  ·  score {r.get('score', 0)}/150  " if self._advanced else f"  {label}  "
        )
        self._verdict_pill.setText(pill_text)
        self._verdict_pill.setStyleSheet(
            f"background: {pill_bg}; color: {text_colour}; font-size: 15px;"
            f" font-weight: 700; border-radius: 13px; padding: 6px 4px;"
        )

        self._fill_meta(r)

        if self._spectrum is None:  # first selection pays the matplotlib import
            from .spectrum_view import SpectrumView

            self._spectrum = SpectrumView()
            self._spectrum.setMinimumHeight(200)
            self._spectrum_holder.addWidget(self._spectrum)
        self._spectrum.clear("Loading spectrum…")
        self._spectrum.show_file(r)

        self._reasons.setHtml(self._reasons_html(r))
        self._detail_stack.setCurrentIndex(1)

    def _fill_meta(self, r: Dict[str, Any]) -> None:
        while self._meta_grid.count():
            item = self._meta_grid.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()

        # Sample rate / bit depth / cutoff are plumbing — only in advanced mode.
        if not self._advanced:
            return

        sr = r.get("sample_rate")
        depth = r.get("bit_depth")
        cutoff = r.get("cutoff_freq")
        hires = r.get("hires_verdict", "")
        fields = [
            ("Sample rate", f"{sr / 1000:.1f} kHz" if sr else "—"),
            ("Bit depth", f"{depth}-bit" if depth else "—"),
            (
                "Cutoff",
                f"{cutoff / 1000:.1f} kHz" if isinstance(cutoff, (int, float)) and cutoff else "—",
            ),
            ("Hi-res", _HIRES_LABEL.get(hires, hires) or "—"),
        ]
        for i, (name, value) in enumerate(fields):
            row, col = divmod(i, 2)
            name_lbl = QLabel(name)
            name_lbl.setObjectName("fieldLabel")
            value_lbl = QLabel(value)
            value_lbl.setObjectName("fieldValue")
            cell = QVBoxLayout()
            cell.setSpacing(1)
            cell.addWidget(name_lbl)
            cell.addWidget(value_lbl)
            wrapper = QWidget()
            wrapper.setLayout(cell)
            self._meta_grid.addWidget(wrapper, row, col)

    def _reasons_html(self, r: Dict[str, Any]) -> str:
        # Easy mode: one plain-language paragraph + the recommended action — no
        # rule codes, points or per-rule bullets.
        if not self._advanced:
            explanation = plain_explanation(r) or "No anomaly detected."
            _icon, _label, action = verdict_plain(r.get("verdict", ""))
            html = f"<p style='margin:0 0 10px 0;'>{explanation}</p>"
            if action:
                html += (
                    f"<p style='margin:0; color:{style.ACCENT}; font-weight:600;'>"
                    f"→ {action}</p>"
                )
            return html

        # Advanced mode: the hi-res note (if any) + the per-rule reasoning bullets.
        parts = []
        hires = r.get("hires_verdict", "")
        if hires and hires not in ("NOT_HIRES", "UNKNOWN") and r.get("hires_reason"):
            parts.append(
                f"<p style='margin:0 0 10px 0; color:{style.TEXT_SECONDARY};'>"
                f"<i>{r['hires_reason']}</i></p>"
            )
        reason = str(r.get("reason", "") or "No anomaly detected.")
        bullets = "".join(
            f"<li style='margin-bottom:5px;'>{part.strip()}</li>"
            for part in reason.split(" | ")
            if part.strip()
        )
        parts.append(f"<ul style='margin:0; padding-left:18px;'>{bullets}</ul>")
        return "".join(parts)

    def _update_summary(self, cancelled: bool) -> None:
        n = len(self._results)
        fakes = sum(1 for r in self._results if r.get("verdict") == "FAKE_CERTAIN")
        suspicious = sum(1 for r in self._results if r.get("verdict") == "SUSPICIOUS")
        fake_hires = sum(
            1
            for r in self._results
            if r.get("hires_verdict") in ("UPSAMPLED", "PADDED_DEPTH", "UPSAMPLED_AND_PADDED")
        )
        prefix = "Cancelled" if cancelled else "Done"
        self._target_label.setText(f"{prefix} — {n} file(s) analysed.")
        self._summary_label.setText(
            f"{n} analysed   ·   {fakes} fake   ·   {suspicious} suspicious   ·   "
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
        from ..reporting import CSVReporter, HTMLReporter  # imported on first export

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
