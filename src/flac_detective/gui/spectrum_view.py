"""A matplotlib spectrum panel for the GUI, reused from the HTML report's curve.

Plots the magnitude spectrum of the selected file (peak-normalised, the same
``_compute_spectrum_curve`` the HTML report uses) and marks the detected cutoff —
so the MP3 "cliff" is visible to the eye, exactly as in the static report.
"""

from __future__ import annotations

from typing import Any, Dict

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..reporting.html_reporter import _compute_spectrum_curve


class SpectrumView(FigureCanvasQTAgg):
    """A small matplotlib canvas showing one file's spectrum with the cutoff marked."""

    # Palette aligned with gui.style (kept local to avoid an import cycle pull).
    _BG = "#ffffff"
    _INK = "#1d1d1f"
    _MUTED = "#6e6e73"
    _HAIRLINE = "#d2d2d7"
    _ACCENT = "#0071e3"
    _CUTOFF = "#c1121f"

    def __init__(self) -> None:
        self._fig = Figure(figsize=(5, 3), tight_layout=True, facecolor=self._BG)
        super().__init__(self._fig)
        self.setStyleSheet("background: transparent;")
        self._ax = self._fig.add_subplot(111)
        self.clear("Select a file to see its spectrum")

    def _style_axes(self) -> None:
        """Apply the calm, light chrome shared by the populated state."""
        self._ax.set_facecolor(self._BG)
        for side in ("top", "right"):
            self._ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            self._ax.spines[side].set_visible(True)
            self._ax.spines[side].set_color(self._HAIRLINE)
        self._ax.tick_params(colors=self._MUTED, labelsize=8, length=0)

    def clear(self, message: str = "") -> None:
        """Reset the plot, optionally showing a centred placeholder message."""
        self._ax.clear()
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        for side in self._ax.spines.values():
            side.set_visible(False)
        if message:
            self._ax.text(
                0.5,
                0.5,
                message,
                ha="center",
                va="center",
                transform=self._ax.transAxes,
                color=self._MUTED,
                fontsize=10,
            )
        self.draw_idle()

    def show_file(self, result: Dict[str, Any]) -> None:
        """Plot the spectrum for ``result``'s file, marking its detected cutoff."""
        curve = _compute_spectrum_curve(result.get("filepath", ""))
        if curve is None:
            self.clear("Spectrum unavailable (file not natively readable).")
            return
        freqs_hz, norm, nyquist = curve
        khz = [f / 1000.0 for f in freqs_hz]

        self._ax.clear()
        self._style_axes()
        self._ax.fill_between(khz, norm, color=self._ACCENT, alpha=0.16, linewidth=0)
        self._ax.plot(khz, norm, color=self._ACCENT, linewidth=1.3)
        self._ax.set_xlim(0, nyquist / 1000.0)
        self._ax.set_ylim(0, 1.05)
        self._ax.set_xlabel("Frequency (kHz)", color=self._MUTED, fontsize=9)
        self._ax.set_ylabel("Magnitude", color=self._MUTED, fontsize=9)
        self._ax.grid(True, color=self._HAIRLINE, alpha=0.4, linewidth=0.6)

        cutoff = result.get("cutoff_freq")
        if isinstance(cutoff, (int, float)) and 0 < cutoff < nyquist:
            self._ax.axvline(cutoff / 1000.0, color=self._CUTOFF, linewidth=1.3, linestyle="--")
            self._ax.text(
                cutoff / 1000.0 + 0.3,
                0.96,
                f"cutoff {cutoff / 1000:.1f} kHz",
                color=self._CUTOFF,
                fontsize=8,
                fontweight="bold",
                va="top",
            )
        self.draw_idle()
