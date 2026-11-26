"""Full-screen-ish image viewer with zoom in / out."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from payra.ui.avatar_cache import avatar_cache
from payra.ui.theme_app import PayraDialog


class ImageViewerDialog(PayraDialog):
    """Tap-to-open viewer: scroll + zoom controls."""

    def __init__(self, image_url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Photo")
        self.setMinimumSize(720, 560)
        self.resize(900, 680)
        self._url = image_url
        self._pixmap: QPixmap | None = None
        self._scale = 1.0

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        title = QLabel("Photo")
        title.setObjectName("DialogTitle")
        toolbar.addWidget(title)
        toolbar.addStretch()

        zoom_out = QPushButton("−")
        zoom_out.setObjectName("DialogGhostButton")
        zoom_out.setFixedSize(40, 36)
        zoom_out.setToolTip("Zoom out")
        zoom_out.clicked.connect(lambda: self._zoom(0.8))
        toolbar.addWidget(zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setObjectName("DialogMuted")
        self._zoom_label.setMinimumWidth(48)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        toolbar.addWidget(self._zoom_label)

        zoom_in = QPushButton("+")
        zoom_in.setObjectName("DialogGhostButton")
        zoom_in.setFixedSize(40, 36)
        zoom_in.setToolTip("Zoom in")
        zoom_in.clicked.connect(lambda: self._zoom(1.25))
        toolbar.addWidget(zoom_in)

        fit = QPushButton("Fit")
        fit.setObjectName("DialogGhostButton")
        fit.clicked.connect(self._fit)
        toolbar.addWidget(fit)

        close = QPushButton("Close")
        close.setObjectName("DialogPrimaryButton")
        close.clicked.connect(self.accept)
        toolbar.addWidget(close)
        root.addLayout(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setStyleSheet(
            "QScrollArea { background: #1C1730; border-radius: 16px; border: none; }"
        )
        self._image = QLabel()
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setStyleSheet("background: transparent; color: #FFFFFF;")
        self._image.setText("Loading…")
        self._scroll.setWidget(self._image)
        root.addWidget(self._scroll, stretch=1)

        tip = QLabel("Scroll wheel zooms · drag scrollbars to pan")
        tip.setObjectName("DialogMuted")
        tip.setAlignment(Qt.AlignCenter)
        root.addWidget(tip)

        self._scroll.viewport().installEventFilter(self)

        cached = avatar_cache().get(image_url, self._on_loaded)
        if cached is not None:
            self._on_loaded(image_url, cached)

    def _on_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url != self._url or pixmap.isNull():
            return
        self._pixmap = pixmap
        self._fit()

    def _fit(self) -> None:
        if self._pixmap is None:
            return
        vp = self._scroll.viewport().size()
        if vp.width() < 40 or vp.height() < 40:
            self._scale = 1.0
            self._apply()
            return
        sx = (vp.width() - 24) / max(1, self._pixmap.width())
        sy = (vp.height() - 24) / max(1, self._pixmap.height())
        self._scale = max(0.1, min(sx, sy, 1.0))
        self._apply()

    def _zoom(self, factor: float) -> None:
        self._scale = max(0.15, min(6.0, self._scale * factor))
        self._apply()

    def _apply(self) -> None:
        if self._pixmap is None:
            return
        w = max(1, int(self._pixmap.width() * self._scale))
        h = max(1, int(self._pixmap.height() * self._scale))
        scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._image.setPixmap(scaled)
        self._image.resize(scaled.size())
        self._zoom_label.setText(f"{int(self._scale * 100)}%")

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._scroll.viewport() and isinstance(event, QWheelEvent):
            if event.modifiers() & Qt.ControlModifier or True:
                delta = event.angleDelta().y()
                if delta > 0:
                    self._zoom(1.12)
                elif delta < 0:
                    self._zoom(1 / 1.12)
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._pixmap is not None and self._scale <= 1.05:
            # Keep fitted view reasonable on first resize
            pass
