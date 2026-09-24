"""Visual helpers — soft card shadows for the ChatFlow-style shell."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_card_shadow(
    widget: QWidget,
    *,
    blur: float = 28,
    x: float = 0,
    y: float = 10,
    alpha: int = 38,
) -> QGraphicsDropShadowEffect:
    """Soft purple-tinted elevation (matches floating cards in the reference)."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(x, y)
    effect.setColor(QColor(90, 70, 160, alpha))
    widget.setGraphicsEffect(effect)
    widget.setAttribute(Qt.WA_StyledBackground, True)
    return effect
