"""Recent chats — time + unread badge always visible (no right clipping)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from payra.models.demo_data import Conversation
from payra.ui.theme import CHAT_LIST_WIDTH
from payra.ui.widgets.avatar import Avatar


class ElidingLabel(QLabel):
    """Label that shrinks and shows … instead of forcing the row wider."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = text
        # Ignored = take only the width the layout gives us (critical for no overflow)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)
        QLabel.setText(self, text)

    def sizeHint(self) -> QSize:  # noqa: N802
        h = super().sizeHint().height()
        return QSize(40, h)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(0, super().minimumSizeHint().height())

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text
        self._elide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        metrics = QFontMetrics(self.font())
        width = max(0, self.width() - 2)
        elided = metrics.elidedText(self._full, Qt.ElideRight, width)
        QLabel.setText(self, elided)
        self.setToolTip(self._full if elided != self._full else "")


class UnreadDot(QLabel):
    """Purple circular unread count (always sized, hidden when 0)."""

    def __init__(self, count: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("UnreadBadge")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(22, 22)
        self.set_count(count)

    def set_count(self, count: int) -> None:
        if count <= 0:
            self.hide()
            self.clear()
            return
        self.setText(str(count if count < 100 else "99+"))
        self.show()


class ChatRow(QFrame):
    clicked = Signal(str)

    def __init__(self, conversation: Conversation, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.conversation_id = conversation.id
        self.setProperty("class", "ChatRow")
        self.setProperty("selected", "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(78)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        # Left: avatar (fixed)
        root.addWidget(
            Avatar(
                conversation.initials,
                conversation.accent,
                48,
                image_url=conversation.avatar_url,
            ),
            0,
            Qt.AlignVCenter,
        )

        # Middle: name + preview (flexible, may elide)
        mid = QWidget()
        mid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        mid.setMinimumWidth(48)
        mid_layout = QVBoxLayout(mid)
        mid_layout.setContentsMargins(0, 2, 0, 2)
        mid_layout.setSpacing(4)

        name = ElidingLabel(conversation.name)
        name.setObjectName("ChatRowName")
        preview = ElidingLabel(conversation.preview)
        preview.setObjectName("ChatRowPreview")
        mid_layout.addWidget(name)
        mid_layout.addWidget(preview)
        root.addWidget(mid, 1)

        # Right: time + unread (fixed width — never clipped)
        right = QWidget()
        right.setFixedWidth(70)
        right.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 2, 0, 2)
        right_layout.setSpacing(6)
        right_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        time = QLabel(conversation.time)
        time.setObjectName("ChatRowTime")
        time.setAlignment(Qt.AlignRight | Qt.AlignTop)
        time.setWordWrap(False)
        # Prefer shorter display for very long stamps
        time.setFixedWidth(68)
        right_layout.addWidget(time)

        badge = UnreadDot(conversation.unread)
        right_layout.addWidget(badge, 0, Qt.AlignRight)
        right_layout.addStretch(1)
        root.addWidget(right, 0, Qt.AlignTop)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.conversation_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class ChatListPanel(QWidget):
    conversation_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChatListPanel")
        self.setFixedWidth(CHAT_LIST_WIDTH)
        self._rows: dict[str, ChatRow] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 18, 14, 16)
        root.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("SearchField")
        self.search.setPlaceholderText("Search messages, people, groups...")
        root.addWidget(self.search)

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        title = QLabel("Recent Chats")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        # Filter icon (visual match to reference)
        filt = QLabel("☰")
        filt.setStyleSheet("color: #8B849C; font-size: 14px; background: transparent;")
        filt.setToolTip("Filter")
        header.addWidget(filt)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self._list_host = QWidget()
        self._list_host.setObjectName("ChatListHost")
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_host)
        root.addWidget(scroll, stretch=1)

    def set_conversations(self, conversations: list[Conversation]) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

        for conversation in conversations:
            row = ChatRow(conversation)
            row.clicked.connect(self._on_row_clicked)
            self._rows[conversation.id] = row
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def select(self, conversation_id: str) -> None:
        for cid, row in self._rows.items():
            row.set_selected(cid == conversation_id)

    def _on_row_clicked(self, conversation_id: str) -> None:
        self.select(conversation_id)
        self.conversation_selected.emit(conversation_id)
