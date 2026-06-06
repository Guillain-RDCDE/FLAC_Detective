"""HTML report writer — a visual, self-contained triage view.

Where the text report is for reading, JSON is for machines and CSV is for
spreadsheets, the HTML report is for *seeing*: a single self-contained ``.html``
file (no external assets, no JS framework) that you double-click to open. It pairs
the ranked triage table with an **inline-SVG spectrum plot** for every flagged
file, so the MP3 "spectral cliff" — the thing the whole tool reasons about — is
visible to the eye.

Design choices that keep this lightweight and on-brand:

- **No new dependency.** The spectrum curve is computed with numpy (already a core
  dep) and drawn as a hand-rolled inline ``<svg>`` polyline — no matplotlib, no
  PNGs, no base64 image blobs. The output stays a single readable HTML file.
- **The core analysis path is untouched.** The spectrum is recomputed here, at
  report time, and *only for flagged files* (typically a handful), so the per-file
  result dict carries no extra payload and the json/csv reports stay lean.
- **Graceful degradation.** A file soundfile cannot read natively (e.g. ALAC/APE
  without ffmpeg, or an unreadable file) simply gets no plot — its table row and
  facts are still shown. The report never fails because one curve could not render.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..__version__ import __version__
from ..analysis.new_scoring import determine_verdict

logger = logging.getLogger(__name__)

# Verdicts the tool flags as worth a closer look — these get a spectrum plot.
_FLAGGED_VERDICTS = ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING")

# Verdict → (label, CSS class). The CSS class drives the badge colour and the
# table-row filter. AUTHENTIC/NON_FLAC/ERROR are handled by the .get() fallback.
_VERDICT_META: Dict[str, Tuple[str, str]] = {
    "FAKE_CERTAIN": ("Fake (certain)", "v-fake"),
    "SUSPICIOUS": ("Suspicious", "v-suspicious"),
    "WARNING": ("Warning", "v-warning"),
    "AUTHENTIC": ("Authentic", "v-authentic"),
    "NON_FLAC": ("Non-FLAC", "v-fake"),
    "ERROR": ("Error", "v-error"),
}

# Spectrum-curve sampling: a 10 s middle segment, downsampled to this many points
# for the SVG polyline (enough to render the cliff cleanly, small enough to keep
# the HTML compact).
_CURVE_POINTS = 240
_CURVE_SECONDS = 10.0
_DB_FLOOR = -100.0  # clamp the normalised magnitude floor (peak = 0 dB)

# Each detail card re-decodes its file to draw the spectrum (an I/O + FFT pass).
# On a full-library scan that flags thousands of files this would be very slow and
# produce a huge page, so we cap the number of spectrum cards to the worst-scoring
# files. The triage table still lists *every* file; only the (expensive) plots are
# capped, with a banner pointing back to the table for the rest.
_MAX_SPECTRUM_CARDS = 200


class HTMLReporter:
    """Write analysis results to a single self-contained HTML file."""

    def generate_report(
        self,
        results: List[Dict[str, Any]],
        output_file: Path,
        scan_paths: Optional[List[Path]] = None,
    ) -> None:
        """Write ``results`` to ``output_file`` as a self-contained HTML report.

        Args:
            results: Per-file analysis result dicts (as returned by FLACAnalyzer).
            output_file: Destination ``.html`` path.
            scan_paths: Scan roots, used to show paths relative to them.
        """
        logger.info(f"Generating HTML report: {output_file}")

        ranked = sorted(results, key=lambda r: r.get("score", 0) or 0, reverse=True)
        flagged = [r for r in ranked if self._verdict_of(r) in _FLAGGED_VERDICTS]

        parts: List[str] = [
            self._document_head(),
            self._summary(ranked),
            self._triage_table(ranked, scan_paths),
            self._detail_cards(flagged, scan_paths),
            self._document_foot(),
        ]
        output_file.write_text("\n".join(parts), encoding="utf-8")
        logger.info(f"HTML report generated: {output_file} ({len(flagged)} flagged)")

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _verdict_of(result: Dict[str, Any]) -> str:
        """The authoritative verdict for a result (falls back to score-derived)."""
        return result.get("verdict") or determine_verdict(result.get("score", 0))[0]

    @staticmethod
    def _display_path(result: Dict[str, Any], scan_paths: Optional[List[Path]]) -> str:
        """Path shown to the user — relative to a scan root when possible."""
        name = result.get("filename", "Unknown")
        filepath = result.get("filepath", "")
        if scan_paths and filepath:
            try:
                p = Path(filepath)
                for root in scan_paths:
                    try:
                        return str(p.relative_to(root))
                    except ValueError:
                        continue
            except Exception:
                pass
        return str(name)

    # ------------------------------------------------------------ doc sections

    def _document_head(self) -> str:
        generated = datetime.now().strftime("%Y-%m-%d %H:%M")
        return _HTML_HEAD.replace("__VERSION__", html.escape(__version__)).replace(
            "__GENERATED__", generated
        )

    def _document_foot(self) -> str:
        return _HTML_FOOT

    def _summary(self, results: List[Dict[str, Any]]) -> str:
        total = len(results)
        counts: Dict[str, int] = {}
        for r in results:
            counts[self._verdict_of(r)] = counts.get(self._verdict_of(r), 0) + 1

        # Order the cards worst-first; only show verdicts that occur.
        order = ["FAKE_CERTAIN", "SUSPICIOUS", "WARNING", "NON_FLAC", "ERROR", "AUTHENTIC"]
        cards = [
            f'<div class="card total"><span class="n">{total}</span><span class="l">files</span></div>'
        ]
        for verdict in order:
            n = counts.get(verdict, 0)
            if n == 0:
                continue
            label, cls = _VERDICT_META.get(verdict, (verdict, "v-authentic"))
            cards.append(
                f'<div class="card {cls}"><span class="n">{n}</span>'
                f'<span class="l">{html.escape(label)}</span></div>'
            )
        return '<section class="summary">' + "".join(cards) + "</section>"

    def _triage_table(self, results: List[Dict[str, Any]], scan_paths: Optional[List[Path]]) -> str:
        if not results:
            return '<section><p class="empty">No files analyzed.</p></section>'

        # Filter buttons: one per verdict present, plus "All".
        present = []
        for verdict in ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING", "AUTHENTIC", "NON_FLAC", "ERROR"):
            if any(self._verdict_of(r) == verdict for r in results):
                present.append(verdict)
        filters = ['<button class="flt active" data-f="all">All</button>']
        for verdict in present:
            label, cls = _VERDICT_META.get(verdict, (verdict, ""))
            filters.append(
                f'<button class="flt {cls}" data-f="{verdict}">{html.escape(label)}</button>'
            )

        rows = []
        for rank, r in enumerate(results, start=1):
            verdict = self._verdict_of(r)
            label, cls = _VERDICT_META.get(verdict, (verdict, "v-authentic"))
            score = r.get("score", "")
            cutoff = r.get("cutoff_freq")
            cutoff_str = (
                f"{cutoff / 1000:.1f} kHz" if isinstance(cutoff, (int, float)) and cutoff else "—"
            )
            sr = r.get("sample_rate", "")
            sr_str = f"{sr} Hz" if isinstance(sr, (int, float)) else html.escape(str(sr))
            bit = r.get("bit_depth", "")
            reason = html.escape(str(r.get("reason", "")).replace("\n", " ").strip())
            path = html.escape(self._display_path(r, scan_paths))
            rows.append(
                f'<tr class="{cls}" data-v="{verdict}">'
                f"<td>{rank}</td>"
                f'<td class="num">{html.escape(str(score))}</td>'
                f'<td><span class="badge {cls}">{html.escape(label)}</span></td>'
                f'<td class="path" title="{path}">{path}</td>'
                f'<td class="num">{cutoff_str}</td>'
                f'<td class="num">{sr_str}</td>'
                f'<td class="num">{html.escape(str(bit))}</td>'
                f'<td class="reason">{reason}</td>'
                "</tr>"
            )

        return (
            "<section><h2>Triage</h2>"
            '<div class="filters">' + "".join(filters) + "</div>"
            '<table id="triage"><thead><tr>'
            "<th>#</th><th>Score</th><th>Verdict</th><th>File</th>"
            "<th>Cutoff</th><th>Rate</th><th>Bits</th><th>Reason</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>"
        )

    def _detail_cards(self, flagged: List[Dict[str, Any]], scan_paths: Optional[List[Path]]) -> str:
        if not flagged:
            return '<section><h2>Flagged files</h2><p class="empty">None — nothing to inspect.</p></section>'

        # Cap the (expensive, re-decoding) spectrum cards to the worst-scoring files;
        # `flagged` is already sorted by descending score. The table keeps the full list.
        total_flagged = len(flagged)
        shown = flagged[:_MAX_SPECTRUM_CARDS]
        banner = ""
        if total_flagged > _MAX_SPECTRUM_CARDS:
            banner = (
                f'<p class="cap-note">Showing spectrum plots for the top '
                f"{_MAX_SPECTRUM_CARDS} of {total_flagged} flagged files (capped for "
                f"performance) — the full list is in the triage table above.</p>"
            )

        cards = []
        for r in shown:
            verdict = self._verdict_of(r)
            label, cls = _VERDICT_META.get(verdict, (verdict, "v-authentic"))
            path = html.escape(self._display_path(r, scan_paths))
            score = html.escape(str(r.get("score", "")))
            cutoff = r.get("cutoff_freq")
            cutoff_str = (
                f"{cutoff / 1000:.1f} kHz" if isinstance(cutoff, (int, float)) and cutoff else "—"
            )
            bitrate = r.get("estimated_mp3_bitrate", 0) or 0
            bitrate_str = f"~{bitrate} kbps" if bitrate else "—"
            reason = html.escape(str(r.get("reason", "")).replace("\n", " ").strip())

            svg = self._spectrum_svg(r)
            facts = (
                f'<dl class="facts">'
                f"<dt>Score</dt><dd>{score}</dd>"
                f"<dt>Cutoff</dt><dd>{cutoff_str}</dd>"
                f"<dt>Est. MP3 bitrate</dt><dd>{html.escape(bitrate_str)}</dd>"
                f"</dl>"
            )
            cards.append(
                f'<article class="detail {cls}">'
                f'<header><span class="badge {cls}">{html.escape(label)}</span>'
                f'<code title="{path}">{path}</code></header>'
                f"{svg}{facts}"
                f'<p class="reason">{reason}</p>'
                "</article>"
            )

        return "<section><h2>Flagged files</h2>" + banner + "".join(cards) + "</section>"

    # ------------------------------------------------------------- spectrum SVG

    def _spectrum_svg(self, result: Dict[str, Any]) -> str:
        """Render an inline-SVG magnitude spectrum for one file, or a placeholder.

        The curve is the real FFT magnitude (dB, peak-normalised) of a 10 s middle
        segment; a vertical marker shows the detected cutoff. If the file cannot be
        read natively, a small "spectrum unavailable" note replaces the plot.
        """
        curve = _compute_spectrum_curve(result.get("filepath", ""))
        if curve is None:
            return '<p class="no-spectrum">Spectrum unavailable (file not natively readable).</p>'

        freqs, norm, nyquist = curve
        width, height = 620.0, 170.0
        pad_l, pad_r, pad_t, pad_b = 44.0, 12.0, 12.0, 26.0
        plot_w = width - pad_l - pad_r
        plot_h = height - pad_t - pad_b

        def x_of(freq: float) -> float:
            return pad_l + (freq / nyquist) * plot_w if nyquist else pad_l

        def y_of(value: float) -> float:
            # value in 0..1 (1 = peak) → top of plot area
            return pad_t + (1.0 - value) * plot_h

        points = " ".join(f"{x_of(f):.1f},{y_of(v):.1f}" for f, v in zip(freqs, norm))

        # Frequency grid every 5 kHz.
        grid = []
        tick = 5000
        f = tick
        while f < nyquist:
            x = x_of(f)
            grid.append(
                f'<line class="grid" x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{pad_t + plot_h:.1f}"/>'
            )
            grid.append(f'<text class="axis" x="{x:.1f}" y="{height - 8:.1f}">{f // 1000}k</text>')
            f += tick

        # Cutoff marker.
        cutoff = result.get("cutoff_freq")
        marker = ""
        if isinstance(cutoff, (int, float)) and 0 < cutoff < nyquist:
            xc = x_of(cutoff)
            marker = (
                f'<line class="cutoff" x1="{xc:.1f}" y1="{pad_t}" x2="{xc:.1f}" y2="{pad_t + plot_h:.1f}"/>'
                f'<text class="cutoff-lbl" x="{xc + 4:.1f}" y="{pad_t + 12:.1f}">cutoff {cutoff / 1000:.1f}k</text>'
            )

        return (
            f'<svg class="spectrum" viewBox="0 0 {width:.0f} {height:.0f}" '
            f'role="img" aria-label="magnitude spectrum">'
            f'<rect class="plot-bg" x="{pad_l}" y="{pad_t}" width="{plot_w:.1f}" height="{plot_h:.1f}"/>'
            + "".join(grid)
            + f'<polyline class="curve" points="{points}"/>'
            + marker
            + f'<text class="axis y" x="6" y="{pad_t + 8:.1f}">dB</text>'
            + "</svg>"
        )


def _compute_spectrum_curve(
    filepath: str,
) -> Optional[Tuple[List[float], List[float], float]]:
    """Compute a downsampled, peak-normalised magnitude spectrum for a file.

    Reads a middle segment, mono-mixes, applies a Hann window, takes the rfft,
    converts to dB, downsamples to ``_CURVE_POINTS`` (max-per-bin, which preserves
    the cliff edge), and normalises so the peak is 1.0 and ``_DB_FLOOR`` is 0.0.

    Returns ``(freqs_hz, norm_0_1, nyquist_hz)`` or ``None`` if the file cannot be
    read (the caller renders a placeholder instead of failing).
    """
    if not filepath:
        return None
    try:
        import numpy as np
        import soundfile as sf

        info = sf.info(filepath)
        sr = int(info.samplerate)
        total_frames = int(info.frames)
        if sr <= 0 or total_frames <= 0:
            return None

        seg_frames = min(int(_CURVE_SECONDS * sr), total_frames)
        start = max(0, (total_frames - seg_frames) // 2)
        data, sr = sf.read(filepath, start=start, frames=seg_frames, always_2d=True)
        if data.size == 0:
            return None

        mono = data.mean(axis=1)
        window = np.hanning(len(mono))
        mag = np.abs(np.fft.rfft(mono * window))
        freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
        mag_db = 20.0 * np.log10(mag + 1e-10)

        # Downsample to a fixed number of points by max-per-bin (keeps the cliff).
        n = min(_CURVE_POINTS, len(mag_db))
        if n < 2:
            return None
        idx = np.linspace(0, len(mag_db), n + 1).astype(int)
        ds_db = np.array([mag_db[idx[i] : max(idx[i] + 1, idx[i + 1])].max() for i in range(n)])
        ds_freq = np.array([float(freqs[min(idx[i], len(freqs) - 1)]) for i in range(n)])

        # Peak-normalise to 0..1 with a fixed dB floor.
        peak = float(ds_db.max())
        norm = (ds_db - peak - _DB_FLOOR) / (-_DB_FLOOR)
        norm = np.clip(norm, 0.0, 1.0)

        return ds_freq.tolist(), norm.tolist(), float(sr) / 2.0
    except Exception as exc:  # pragma: no cover - defensive: any decode/read failure
        logger.debug(f"Spectrum curve unavailable for {filepath}: {exc}")
        return None


_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FLAC Detective Report</title>
<style>
:root{--bg:#0f1115;--panel:#181b22;--ink:#e6e8ec;--muted:#9aa3b2;--line:#262b35;
--fake:#e5484d;--susp:#f5a524;--warn:#3b82f6;--ok:#22c55e;--err:#8b5cf6;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:24px}
h1{font-size:20px;margin:0 0 2px}h2{font-size:16px;margin:28px 0 10px;color:var(--muted)}
.sub{color:var(--muted);margin:0 0 18px;font-size:13px}
.summary{display:flex;flex-wrap:wrap;gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:12px 16px;min-width:104px;display:flex;flex-direction:column}
.card .n{font-size:22px;font-weight:700}.card .l{color:var(--muted);font-size:12px}
.card.v-fake{border-left:4px solid var(--fake)}.card.v-suspicious{border-left:4px solid var(--susp)}
.card.v-warning{border-left:4px solid var(--warn)}.card.v-authentic{border-left:4px solid var(--ok)}
.card.v-error{border-left:4px solid var(--err)}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.flt{background:var(--panel);color:var(--ink);border:1px solid var(--line);
border-radius:6px;padding:4px 10px;cursor:pointer;font-size:12px}
.flt.active{outline:2px solid var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);cursor:pointer;user-select:none;position:sticky;top:0;background:var(--bg)}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
td.path{max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td.reason{color:var(--muted);max-width:420px}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600;color:#0b0d11}
.badge.v-fake{background:var(--fake)}.badge.v-suspicious{background:var(--susp)}
.badge.v-warning{background:var(--warn)}.badge.v-authentic{background:var(--ok)}
.badge.v-error{background:var(--err);color:#fff}
.detail{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 16px;margin:0 0 14px}
.detail header{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.detail code{color:var(--ink);font-size:13px;word-break:break-all}
.facts{display:flex;gap:24px;margin:8px 0 0}.facts dt{color:var(--muted);font-size:12px}
.facts dd{margin:0;font-weight:600}
.detail .reason{color:var(--muted);margin:8px 0 0}
.no-spectrum{color:var(--muted);font-style:italic;margin:4px 0}
.cap-note{color:var(--susp);background:var(--panel);border:1px solid var(--line);
border-radius:8px;padding:8px 12px;margin:0 0 12px;font-size:13px}
svg.spectrum{width:100%;max-width:640px;height:auto;display:block;margin:4px 0}
.plot-bg{fill:#0b0d11;stroke:var(--line)}
.curve{fill:none;stroke:var(--ok);stroke-width:1.4}
.detail.v-fake .curve{stroke:var(--fake)}.detail.v-suspicious .curve{stroke:var(--susp)}
.detail.v-warning .curve{stroke:var(--warn)}
.grid{stroke:var(--line);stroke-width:.5}
.cutoff{stroke:var(--susp);stroke-width:1;stroke-dasharray:3 3}
.cutoff-lbl{fill:var(--susp);font-size:10px}
.axis{fill:var(--muted);font-size:10px;text-anchor:middle}.axis.y{text-anchor:start}
.empty{color:var(--muted)}
footer{margin-top:30px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:12px}
</style>
</head>
<body>
<h1>FLAC Detective</h1>
<p class="sub">Report v__VERSION__ · generated __GENERATED__ · higher score = more likely a transcode</p>
"""

_HTML_FOOT = """<footer>
The spectrum plots show the real FFT magnitude (dB, peak-normalised) of a 10&nbsp;s middle
segment; the dashed marker is the detected cutoff. A sharp drop (&ldquo;the cliff&rdquo;) well
below Nyquist is the classic MP3-transcode signature. Plots are shown for flagged files only.
</footer>
<script>
(function(){
  // Verdict filter buttons.
  var btns=document.querySelectorAll('.flt');
  btns.forEach(function(b){b.addEventListener('click',function(){
    btns.forEach(function(x){x.classList.remove('active')});b.classList.add('active');
    var f=b.dataset.f;
    document.querySelectorAll('#triage tbody tr').forEach(function(tr){
      tr.style.display=(f==='all'||tr.dataset.v===f)?'':'none';
    });
  });});
  // Click a column header to sort (numeric columns sort numerically).
  var table=document.getElementById('triage');
  if(!table)return;
  var numeric={0:1,1:1,4:1,5:1,6:1};
  table.querySelectorAll('th').forEach(function(th,col){
    var asc=true;
    th.addEventListener('click',function(){
      var rows=Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
      rows.sort(function(a,b){
        var x=a.cells[col].innerText, y=b.cells[col].innerText;
        if(numeric[col]){x=parseFloat(x.replace(/[^0-9.\\-]/g,''))||0;y=parseFloat(y.replace(/[^0-9.\\-]/g,''))||0;return asc?x-y:y-x;}
        return asc?x.localeCompare(y):y.localeCompare(x);
      });
      asc=!asc;var tb=table.querySelector('tbody');rows.forEach(function(r){tb.appendChild(r);});
    });
  });
})();
</script>
</body>
</html>
"""
