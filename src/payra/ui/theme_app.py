"""Force Payra light theme (ignore OS dark mode for readable dialogs)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QStyleFactory

_STYLES = Path(__file__).resolve().parent / "styles" / "app.qss"

_PANEL = QColor("#FFFFFF")
_TEXT = QColor("#1C1730")
_MUTED = QColor("#8B849C")
_ACCENT = QColor("#7B61FF")
_INPUT = QColor("#F0EEF6")


def light_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, _PANEL)
    palette.setColor(QPalette.WindowText, _TEXT)
    palette.setColor(QPalette.Base, _PANEL)
    palette.setColor(QPalette.AlternateBase, _INPUT)
    palette.setColor(QPalette.Text, _TEXT)
    palette.setColor(QPalette.Button, _PANEL)
    palette.setColor(QPalette.ButtonText, _TEXT)
    palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.Highlight, _ACCENT)
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipBase, _PANEL)
    palette.setColor(QPalette.ToolTipText, _TEXT)
    palette.setColor(QPalette.PlaceholderText, _MUTED)
    palette.setColor(QPalette.Link, _ACCENT)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, _MUTED)
    palette.setColor(QPalette.Disabled, QPalette.Text, _MUTED)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, _MUTED)
    return palette


def apply_app_theme(app: QApplication) -> None:
    """Single white/light theme for main window + all dialogs."""
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    app.setPalette(light_palette())
    if _STYLES.exists():
        app.setStyleSheet(_STYLES.read_text(encoding="utf-8"))


class PayraDialog(QDialog):
    """Base dialog — white look matching the main app."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PayraDialog")
        self.setPalette(light_palette())
        self.setAttribute(Qt.WA_StyledBackground, True)
        from payra.resources import load_app_icon

        self.setWindowIcon(load_app_icon())
