"""WhatsApp-style image preview + caption before sending."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QPixmap, QTextOption
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from payra.ui.theme_app import PayraDialog


class _CaptionInput(QTextEdit):
    send_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DialogSearch")
        self.setPlaceholderText("Add a caption…")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setFixedHeight(72)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ImageComposeDialog(PayraDialog):
    """Preview selected image, optional caption, then send."""

    send_requested = Signal(str, str)  # local_path, caption

    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Send image")
        self.setMinimumSize(520, 620)
        self.resize(560, 680)
        self._path = str(image_path)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("Send image")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        preview_wrap = QLabel()
        preview_wrap.setAlignment(Qt.AlignCenter)
        preview_wrap.setMinimumHeight(360)
        preview_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_wrap.setStyleSheet(
            "background: #1C1730; border-radius: 18px; color: #FFFFFF;"
        )
        pix = QPixmap(self._path)
        if pix.isNull():
            preview_wrap.setText("Could not load image")
        else:
            scaled = pix.scaled(
                480,
                480,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            preview_wrap.setPixmap(scaled)
        root.addWidget(preview_wrap, stretch=1)

        name = QLabel(Path(self._path).name)
        name.setObjectName("DialogMuted")
        name.setAlignment(Qt.AlignCenter)
        root.addWidget(name)

        self._caption = _CaptionInput()
        self._caption.send_requested.connect(self._accept)
        root.addWidget(self._caption)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("DialogGhostButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        send = QPushButton("Send")
        send.setObjectName("DialogPrimaryButton")
        send.setCursor(Qt.PointingHandCursor)
        send.clicked.connect(self._accept)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(send)
        root.addLayout(buttons)

        self._caption.setFocus()

    def _accept(self) -> None:
        self.send_requested.emit(self._path, self._caption.toPlainText().strip())
        self.accept()
