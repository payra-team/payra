"""Small reusable UI pieces — circular avatars (photo or professional default)."""

from __future__ import annotations

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from payra.resources import load_default_avatar_pixmap, normalize_avatar_url
from payra.ui.avatar_cache import avatar_cache


class Avatar(QWidget):
    """Circular avatar: network/local image when available, else default silhouette."""

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
        self._image_url = ""
        self._photo: QPixmap | None = None
        self._default = load_default_avatar_pixmap(size)
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("View profile")
        self.set_identity(initials, color, image_url=image_url)

    def set_identity(
        self,
        initials: str,
        color: str = "#7B61FF",
        image_url: str | None = None,
    ) -> None:
        self._initials = (initials or "?").upper()[:2]
        self._color = QColor(color)
        url = normalize_avatar_url(image_url)
        if url != self._image_url:
            self._image_url = url
            self._photo = None
            self._request_photo()
        self.update()

    def _request_photo(self) -> None:
        url = self._image_url
        if not url:
            self._photo = self._default
            return

        # Local file / resource URI — load without network
        local = QUrl(url)
        if local.isLocalFile():
            pix = QPixmap(local.toLocalFile())
            self._photo = pix if not pix.isNull() else self._default
            return

        if url.startswith("file:"):
            pix = QPixmap(QUrl(url).toLocalFile())
            self._photo = pix if not pix.isNull() else self._default
            return

        cached = avatar_cache().get(url, self._on_photo)
        if cached is not None:
            self._photo = cached
        else:
            # Show default while remote photo loads
            self._photo = self._default

    def _on_photo(self, url: str, pixmap: QPixmap) -> None:
        if url != self._image_url:
            return
        self._photo = pixmap if not pixmap.isNull() else self._default
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

        photo = self._photo if self._photo and not self._photo.isNull() else self._default
        if photo is not None and not photo.isNull():
            path = QPainterPath()
            path.addEllipse(0, 0, self._size, self._size)
            painter.setClipPath(path)
            scaled = photo.scaled(
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
