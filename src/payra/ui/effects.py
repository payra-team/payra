"""Visual helpers — soft card elevation without fragile graphics effects."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


class _NullShadow:
    """Stand-in so callers can still call setEnabled() safely."""

    def setEnabled(self, _enabled: bool) -> None:
        return None


def apply_card_shadow(
    widget: QWidget,
    *,
    blur: float = 28,
    x: float = 0,
    y: float = 10,
    alpha: int = 38,
) -> _NullShadow:
    """
    Soft elevation via stylesheet border.

    Avoids QGraphicsDropShadowEffect — on macOS Cocoa it regularly segfaults when
    combined with QScrollArea, stacked pages, overlays, or modal dialogs.
    """
    del blur, x, y, alpha
    widget.setAttribute(Qt.WA_StyledBackground, True)
    marker = "/* payra-card-elevation */"
    existing = widget.styleSheet() or ""
    if marker not in existing:
        widget.setStyleSheet(
            f"{existing}\n{marker}\n"
            "border: 1px solid rgba(90, 70, 160, 0.10);\n"
        )
    return _NullShadow()
