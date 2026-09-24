"""White elevated icon buttons (ChatFlow card style)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QToolButton

from payra.ui.effects import apply_card_shadow
from payra.ui.theme import ACCENT


class WhiteCardButton(QToolButton):
    """White rounded card + soft shadow; primary-colored glyph."""

    def __init__(
        self,
        glyph: str,
        *,
        tooltip: str = "",
        size: int = 44,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._glyph = glyph
        self._accent = QColor(ACCENT)
        self.setObjectName("WhiteCardButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size, size)
        if tooltip:
            self.setToolTip(tooltip)
        apply_card_shadow(self, blur=14, y=3, alpha=28)

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        inset = 2
        painter.drawRoundedRect(
            self.rect().adjusted(inset, inset, -inset, -inset), 12, 12
        )
        painter.setPen(self._accent)
        font = painter.font()
        font.setPixelSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._glyph)
