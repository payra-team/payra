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
    Mark a panel as a styled surface.

    Do NOT set an unscoped `border:` stylesheet here — Qt applies bare
    properties to the widget AND all descendants, which draws boxes around
    every QLabel/icon. Card borders live in app.qss on named panels only.
    """
    del blur, x, y, alpha
    widget.setAttribute(Qt.WA_StyledBackground, True)
    return _NullShadow()
