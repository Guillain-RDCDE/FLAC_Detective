"""Visual design system for the FLAC Detective GUI.

One source of truth for the palette, the verdict colours, and the global Qt
stylesheet. The look is deliberately light, spacious and calm — closer to a
modern macOS app than a dense data grid.
"""

from __future__ import annotations

# --- palette ------------------------------------------------------------
WINDOW_BG = "#f5f5f7"   # app background (Apple light grey)
CARD_BG = "#ffffff"     # panels / table
TEXT = "#1d1d1f"        # primary text (near-black)
TEXT_SECONDARY = "#6e6e73"
SEPARATOR = "#e5e5ea"
HAIRLINE = "#d2d2d7"
ACCENT = "#0071e3"      # primary button / highlights
ACCENT_HOVER = "#0077ed"
ACCENT_PRESSED = "#006edb"
SELECTION = "#e8f1ff"   # selected table row

# Verdict -> (text colour, soft pill background, human label).
VERDICT_THEME = {
    "FAKE_CERTAIN": ("#c1121f", "#fdebec", "Fake"),
    "SUSPICIOUS": ("#b25e00", "#fdf1e3", "Suspicious"),
    "WARNING": ("#8a7400", "#faf4dc", "Warning"),
    "AUTHENTIC": ("#1a7f37", "#e7f7ec", "Authentic"),
    "NON_FLAC": ("#6f42c1", "#f1ecfb", "Non-FLAC"),
    "ERROR": ("#6e6e73", "#eeeef0", "Error"),
}


def verdict_theme(verdict: str):
    """(text colour, pill background, label) for a verdict, with a safe default."""
    return VERDICT_THEME.get(verdict, ("#6e6e73", "#eeeef0", verdict or "—"))


# --- global stylesheet --------------------------------------------------
APP_STYLE = f"""
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
    color: {TEXT};
    outline: none;
}}

QMainWindow, QWidget#central {{
    background: {WINDOW_BG};
}}

/* ---- buttons ---- */
QPushButton {{
    background: {CARD_BG};
    border: 1px solid {HAIRLINE};
    border-radius: 9px;
    padding: 8px 16px;
    color: {TEXT};
}}
QPushButton:hover {{ background: #fbfbfd; border-color: #c4c4cc; }}
QPushButton:pressed {{ background: #f0f0f2; }}
QPushButton:disabled {{ color: #b8b8be; border-color: #ececef; background: #fafafb; }}

QPushButton#primary {{
    background: {ACCENT};
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 22px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton#primary:disabled {{ background: #b9d6f6; color: #eaf3fd; }}

QPushButton#danger {{ color: {VERDICT_THEME['FAKE_CERTAIN'][0]}; }}
QPushButton#danger:disabled {{ color: #d9b6b8; }}

/* ---- inputs ---- */
QDoubleSpinBox {{
    background: {CARD_BG};
    border: 1px solid {HAIRLINE};
    border-radius: 9px;
    padding: 6px 8px;
    min-width: 64px;
}}
QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 18px; border: none; }}

QCheckBox {{ spacing: 8px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {HAIRLINE};
    border-radius: 6px;
    background: {CARD_BG};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    image: none;
}}

/* ---- labels ---- */
QLabel#title {{ font-size: 19px; font-weight: 700; }}
QLabel#sectionLabel {{ font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; }}
QLabel#secondary {{ color: {TEXT_SECONDARY}; }}
QLabel#summary {{ color: {TEXT_SECONDARY}; font-size: 13px; }}
QLabel#fieldLabel {{ color: {TEXT_SECONDARY}; font-size: 13px; }}
QLabel#fieldValue {{ color: {TEXT}; font-size: 14px; font-weight: 600; }}

/* ---- table ---- */
QTableWidget {{
    background: {CARD_BG};
    border: 1px solid {SEPARATOR};
    border-radius: 14px;
    gridline-color: transparent;
    selection-background-color: {SELECTION};
    selection-color: {TEXT};
    alternate-background-color: #fafafc;
    padding: 4px;
}}
QTableWidget::item {{
    padding: 9px 10px;
    border: none;
    border-bottom: 1px solid #f0f0f3;
}}
QTableWidget::item:selected {{ background: {SELECTION}; color: {TEXT}; }}

QHeaderView::section {{
    background: {CARD_BG};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {SEPARATOR};
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background: {CARD_BG}; border: none; }}

/* ---- progress ---- */
QProgressBar {{
    border: none;
    background: {SEPARATOR};
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}

/* ---- detail card ---- */
QFrame#card {{
    background: {CARD_BG};
    border: 1px solid {SEPARATOR};
    border-radius: 14px;
}}
QTextEdit {{
    background: transparent;
    border: none;
    color: {TEXT};
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ---- scrollbars ---- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #c7c7cc; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #b0b0b6; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
QScrollBar::handle:horizontal {{ background: #c7c7cc; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- splitter ---- */
QSplitter::handle {{ background: transparent; width: 14px; }}
"""
