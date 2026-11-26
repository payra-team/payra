"""Lightweight shimmer placeholders (WhatsApp-style inline loading)."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, Property
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget


class ShimmerBlock(QWidget):
    """Animated soft bar used inside loading skeletons."""

    def __init__(
        self,
        *,
        width: int | None = None,
        height: int = 12,
        radius: int = 8,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._phase = 0.0
        self.setFixedHeight(height)
        if width is not None:
            self.setFixedWidth(width)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        self._anim = QPropertyAnimation(self, b"phase", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1200)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.start()

    def get_phase(self) -> float:
        return self._phase

    def set_phase(self, value: float) -> None:
        self._phase = float(value)
        self.update()

    phase = Property(float, get_phase, set_phase)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        base = QColor("#EDE8FF")
        painter.setBrush(base)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)

        grad = QLinearGradient(0, 0, self.width(), 0)
        x = self._phase
        grad.setColorAt(max(0.0, x - 0.25), QColor("#EDE8FF"))
        grad.setColorAt(x, QColor("#FFFFFF"))
        grad.setColorAt(min(1.0, x + 0.25), QColor("#EDE8FF"))
        painter.setBrush(grad)
        painter.setOpacity(0.75)
        painter.drawRoundedRect(QRectF(self.rect()), self._radius, self._radius)


class ChatListShimmer(QWidget):
    """Skeleton rows for the conversation list."""

    def __init__(self, rows: int = 6, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(10)
        for _ in range(rows):
            lay.addWidget(self._row())
        lay.addStretch(1)

    @staticmethod
    def _row() -> QWidget:
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(12)
        avatar = ShimmerBlock(width=44, height=44, radius=22)
        row.addWidget(avatar)
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(ShimmerBlock(height=12, radius=6))
        col.addWidget(ShimmerBlock(width=120, height=10, radius=5))
        row.addLayout(col, stretch=1)
        return host


class MessageThreadShimmer(QWidget):
    """Skeleton bubbles while a chat is opening."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(14)

        left = QHBoxLayout()
        left.addWidget(self._bubble(180), 0, Qt.AlignLeft)
        left.addStretch()
        lay.addLayout(left)

        right = QHBoxLayout()
        right.addStretch()
        right.addWidget(self._bubble(220), 0, Qt.AlignRight)
        lay.addLayout(right)

        left2 = QHBoxLayout()
        left2.addWidget(self._bubble(140), 0, Qt.AlignLeft)
        left2.addStretch()
        lay.addLayout(left2)

        right2 = QHBoxLayout()
        right2.addStretch()
        right2.addWidget(self._bubble(260), 0, Qt.AlignRight)
        lay.addLayout(right2)
        lay.addStretch(1)

    @staticmethod
    def _bubble(width: int) -> QWidget:
        return ShimmerBlock(width=width, height=44, radius=16)
