"""Small reusable UI pieces — circular avatars (initials or network photo)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from payra.ui.avatar_cache import avatar_cache


class Avatar(QWidget):
    """Circular avatar: network image when available, else initials."""

    clicked = Signal()

    def __init__(
        self,
        initials: str,
        color: str = "#7B61FF",
        size: int = 44,
        *,
        image_url: str | None = None,
        clickable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._initials = (initials or "?").upper()[:2]
        self._color = QColor(color)
        self._size = size
        self._image_url = image_url or ""
        self._photo: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("View profile")
        if self._image_url:
            self._request_photo()

    def set_identity(
        self,
        initials: str,
        color: str = "#7B61FF",
        image_url: str | None = None,
    ) -> None:
        self._initials = (initials or "?").upper()[:2]
        self._color = QColor(color)
        url = image_url or ""
        if url != self._image_url:
            self._image_url = url
            self._photo = None
            if url:
                self._request_photo()
        self.update()

    def _request_photo(self) -> None:
        cached = avatar_cache().get(self._image_url, self._on_photo)
        if cached is not None:
            self._photo = cached
            self.update()

    def _on_photo(self, url: str, pixmap: QPixmap) -> None:
        if url != self._image_url:
            return
        self._photo = pixmap
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.cursor().shape() == Qt.PointingHandCursor:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)

        if self._photo and not self._photo.isNull():
            path = QPainterPath()
            path.addEllipse(0, 0, self._size, self._size)
            painter.setClipPath(path)
            scaled = self._photo.scaled(
                self._size,
                self._size,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (scaled.width() - self._size) // 2
            y = (scaled.height() - self._size) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self._size, self._size)
            return

        painter.setBrush(self._color)
        painter.drawEllipse(0, 0, self._size, self._size)
        painter.setPen(QColor("#FFFFFF"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(max(11, self._size // 3))
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._initials)


class OnlineDot(QWidget):
    def __init__(self, size: int = 10, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#22C55E"))
        painter.drawEllipse(0, 0, self._size, self._size)


class UnreadBadge(QLabel):
    def __init__(self, count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("UnreadBadge")
        self.setAlignment(Qt.AlignCenter)
        self.set_count(count)

    def set_count(self, count: int) -> None:
        if count <= 0:
            self.hide()
            return
        self.setText(str(count if count < 100 else "99+"))
        self.show()
