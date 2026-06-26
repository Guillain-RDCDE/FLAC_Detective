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

    def __init__(self) -> None:
        self._fig = Figure(figsize=(5, 3), tight_layout=True)
        super().__init__(self._fig)
        self._ax = self._fig.add_subplot(111)
        self.clear("Select a file to see its spectrum")

    def clear(self, message: str = "") -> None:
        """Reset the plot, optionally showing a centred placeholder message."""
        self._ax.clear()
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        if message:
            self._ax.text(
                0.5,
                0.5,
                message,
                ha="center",
                va="center",
                transform=self._ax.transAxes,
                color="gray",
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
        self._ax.fill_between(khz, norm, color="#4c8bf5", alpha=0.35, linewidth=0)
        self._ax.plot(khz, norm, color="#1c5fd0", linewidth=1.0)
        self._ax.set_xlim(0, nyquist / 1000.0)
        self._ax.set_ylim(0, 1.05)
        self._ax.set_xlabel("Frequency (kHz)")
        self._ax.set_ylabel("Magnitude (norm.)")
        self._ax.grid(True, alpha=0.2)

        cutoff = result.get("cutoff_freq")
        if isinstance(cutoff, (int, float)) and 0 < cutoff < nyquist:
            self._ax.axvline(cutoff / 1000.0, color="#d23b3b", linewidth=1.2, linestyle="--")
            self._ax.text(
                cutoff / 1000.0 + 0.3,
                0.92,
                f"cutoff {cutoff / 1000:.1f} kHz",
                color="#d23b3b",
                fontsize=8,
                va="top",
            )
        self._ax.set_title(result.get("filename", ""), fontsize=9)
        self.draw_idle()
