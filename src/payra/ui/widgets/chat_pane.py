"""Center conversation — ChatFlow bubbles (painted cards), multi-line + emoji."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QAction, QColor, QKeyEvent, QPainter, QPaintEvent, QTextOption
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from payra.models.demo_data import ME_AVATAR, Conversation, Message
from payra.ui.effects import apply_card_shadow
from payra.ui.widgets.avatar import Avatar, OnlineDot

# Soft ChatFlow palette
_BUBBLE_IN = QColor("#FFFFFF")
_BUBBLE_OUT = QColor("#E6DFFF")
_RADIUS = 18

_EMOJI_SET = [
    "😀", "😁", "😂", "🤣", "😊", "😇", "🙂", "😉",
    "😍", "😘", "😜", "🤔", "😎", "🤩", "😢", "😭",
    "😤", "😅", "🤗", "🙌", "👍", "👎", "👏", "🙏",
    "🔥", "✨", "💯", "🎉", "❤️", "💜", "💙", "💚",
]


class BubbleCard(QWidget):
    """Opaque rounded bubble — painted so drop-shadow does not kill the fill."""

    def __init__(self, outgoing: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._outgoing = outgoing
        self._bg = _BUBBLE_OUT if outgoing else _BUBBLE_IN
        self.setMaximumWidth(460)
        self.setAttribute(Qt.WA_TranslucentBackground)
        apply_card_shadow(self, blur=20, y=5, alpha=36)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 10)
        self._layout.setSpacing(6)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg)
        # Inset slightly so shadow has room around the card
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), _RADIUS, _RADIUS)


class MessageBubble(QWidget):
    """Avatar + card bubble with time and seen ticks (ChatFlow)."""

    def __init__(
        self,
        message: Message,
        *,
        peer_url: str,
        peer_initials: str,
        peer_accent: str,
        me_url: str = ME_AVATAR,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        outgoing = message.outgoing

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(10)

        peer_avatar = Avatar(peer_initials, peer_accent, 38, image_url=peer_url)
        me_avatar = Avatar("YO", "#7B61FF", 38, image_url=me_url)

        card = BubbleCard(outgoing)
        text = QLabel(message.text)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.setStyleSheet(
            "background: transparent; color: #1C1730; font-size: 13px; border: none;"
        )
        card._layout.addWidget(text)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(4)
        meta.addStretch()
        time = QLabel(message.time)
        time.setStyleSheet(
            "background: transparent; color: #8B849C; font-size: 11px; border: none;"
        )
        meta.addWidget(time)
        if outgoing:
            # ✓ = sent, ✓✓ = seen
            mark = "✓✓" if message.seen else "✓"
            checks = QLabel(mark)
            color = "#7B61FF" if message.seen else "#B0A8C4"
            checks.setStyleSheet(
                f"background: transparent; color: {color}; font-size: 11px; "
                "font-weight: 700; border: none; padding-left: 2px;"
            )
            checks.setToolTip("Seen" if message.seen else "Sent")
            meta.addWidget(checks)
        card._layout.addLayout(meta)

        if outgoing:
            row.addStretch()
            row.addWidget(card, 0, Qt.AlignBottom)
            row.addWidget(me_avatar, 0, Qt.AlignBottom)
        else:
            row.addWidget(peer_avatar, 0, Qt.AlignBottom)
            row.addWidget(card, 0, Qt.AlignBottom)
            row.addStretch()


class ExpandingInput(QTextEdit):
    """Multi-line composer: grows with content; Enter sends, Shift+Enter = newline."""

    send_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ComposerInput")
        self.setPlaceholderText("Type a message...")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(36)
        self.setMaximumHeight(120)
        self.textChanged.connect(self._fit_height)
        self._fit_height()

    def _fit_height(self) -> None:
        doc = self.document()
        doc.setTextWidth(max(self.viewport().width(), 100))
        h = int(doc.size().height()) + 16
        h = max(36, min(120, h))
        self.setFixedHeight(h)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def plain(self) -> str:
        return self.toPlainText().strip()


class EmojiPicker(QFrame):
    emoji_chosen = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("EmojiPicker")
        self.setAttribute(Qt.WA_StyledBackground, True)
        grid = QGridLayout(self)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(4)
        cols = 8
        for i, emoji in enumerate(_EMOJI_SET):
            btn = QToolButton()
            btn.setText(emoji)
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QToolButton { border: none; border-radius: 8px; font-size: 18px; }"
                "QToolButton:hover { background: #EDE8FF; }"
            )
            btn.clicked.connect(lambda _=False, e=emoji: self._pick(e))
            grid.addWidget(btn, i // cols, i % cols)

    def _pick(self, emoji: str) -> None:
        self.emoji_chosen.emit(emoji)
        self.hide()


class KebabMenuButton(QToolButton):
    """White card button with vertical three black dots."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HeaderMenuButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 42)
        self.setToolTip("More")
        apply_card_shadow(self, blur=14, y=3, alpha=30)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)
        # Three vertical black dots
        painter.setBrush(QColor("#1C1730"))
        cx = self.width() // 2
        for dy in (-8, 0, 8):
            painter.drawEllipse(cx - 2, self.height() // 2 + dy - 2, 4, 4)


class ChatPane(QWidget):
    send_requested = Signal(str)
    attach_requested = Signal()
    profile_clicked = Signal()
    star_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChatPane")
        self._peer_url = ""
        self._peer_initials = "?"
        self._peer_accent = "#7B61FF"
        self._emoji_picker = EmojiPicker(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        # Header
        header = QWidget()
        header.setObjectName("ChatHeaderBar")
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(4, 4, 4, 4)
        header_row.setSpacing(12)

        self._avatar = Avatar("?", size=48, clickable=True)
        self._avatar.clicked.connect(self.profile_clicked.emit)
        header_row.addWidget(self._avatar)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        self._name = QLabel("Select a chat")
        self._name.setObjectName("ChatHeaderName")
        self._name.setCursor(Qt.PointingHandCursor)
        self._name.setToolTip("View profile")
        self._name.installEventFilter(self)
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self._online_dot = OnlineDot(8)
        self._status = QLabel("")
        self._status.setObjectName("ChatHeaderStatus")
        status_row.addWidget(self._online_dot)
        status_row.addWidget(self._status)
        status_row.addStretch()
        titles.addWidget(self._name)
        titles.addLayout(status_row)
        header_row.addLayout(titles, stretch=1)

        self._menu_btn = KebabMenuButton()
        self._chat_menu = QMenu(self)
        self._chat_menu.setObjectName("ChatHeaderMenu")
        info_action = QAction("ℹ️   Info", self)
        star_action = QAction("⭐   Starred", self)
        info_action.triggered.connect(self.profile_clicked.emit)
        star_action.triggered.connect(self.star_requested.emit)
        self._chat_menu.addAction(info_action)
        self._chat_menu.addAction(star_action)
        self._menu_btn.setMenu(self._chat_menu)
        self._menu_btn.setPopupMode(QToolButton.InstantPopup)
        header_row.addWidget(self._menu_btn)

        root.addWidget(header)

        # Message well
        message_well = QFrame()
        message_well.setObjectName("MessageArea")
        message_well.setAttribute(Qt.WA_StyledBackground, True)
        well_layout = QVBoxLayout(message_well)
        well_layout.setContentsMargins(10, 10, 10, 10)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("MessageScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._thread_host = QWidget()
        self._thread_host.setStyleSheet("background: transparent;")
        self._thread = QVBoxLayout(self._thread_host)
        self._thread.setContentsMargins(4, 10, 4, 10)
        self._thread.setSpacing(12)
        self._thread.addStretch()
        self._scroll.setWidget(self._thread_host)
        well_layout.addWidget(self._scroll)
        root.addWidget(message_well, stretch=1)

        # Composer: [attach] [ input + emoji ] [send]
        composer = QWidget()
        composer.setObjectName("ComposerBar")
        composer.setAttribute(Qt.WA_StyledBackground, True)
        apply_card_shadow(composer, blur=16, y=3, alpha=24)
        composer_row = QHBoxLayout(composer)
        composer_row.setContentsMargins(12, 10, 12, 10)
        composer_row.setSpacing(10)
        composer_row.setAlignment(Qt.AlignBottom)

        attach = QToolButton()
        attach.setText("📎")
        attach.setObjectName("AttachButton")
        attach.setToolTip("Attach image")
        attach.setCursor(Qt.PointingHandCursor)
        attach.clicked.connect(self.attach_requested.emit)
        composer_row.addWidget(attach)

        input_wrap = QFrame()
        input_wrap.setObjectName("ComposerInputWrap")
        input_wrap.setAttribute(Qt.WA_StyledBackground, True)
        input_row = QHBoxLayout(input_wrap)
        input_row.setContentsMargins(12, 4, 6, 4)
        input_row.setSpacing(4)
        input_row.setAlignment(Qt.AlignBottom)

        self._input = ExpandingInput()
        self._input.send_requested.connect(self._emit_send)
        input_row.addWidget(self._input, stretch=1)

        emoji_btn = QToolButton()
        emoji_btn.setText("☺")
        emoji_btn.setObjectName("EmojiButton")
        emoji_btn.setToolTip("Emoji")
        emoji_btn.setCursor(Qt.PointingHandCursor)
        emoji_btn.clicked.connect(self._toggle_emoji)
        input_row.addWidget(emoji_btn, 0, Qt.AlignBottom)
        composer_row.addWidget(input_wrap, stretch=1)

        send = QPushButton("➤")
        send.setObjectName("SendButton")
        send.setCursor(Qt.PointingHandCursor)
        send.clicked.connect(self._emit_send)
        composer_row.addWidget(send)

        root.addWidget(composer)
        self._emoji_picker.emoji_chosen.connect(self._insert_emoji)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._name and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.profile_clicked.emit()
                return True
        return super().eventFilter(obj, event)

    def _toggle_emoji(self) -> None:
        if self._emoji_picker.isVisible():
            self._emoji_picker.hide()
            return
        btn = self.sender()
        if isinstance(btn, QWidget):
            pos = btn.mapToGlobal(QPoint(0, -self._emoji_picker.sizeHint().height() - 8))
            self._emoji_picker.move(pos)
        self._emoji_picker.show()

    def _insert_emoji(self, emoji: str) -> None:
        self._input.insertPlainText(emoji)
        self._input.setFocus()

    def show_conversation(self, conversation: Conversation) -> None:
        self._name.setText(conversation.name)
        self._peer_url = conversation.avatar_url
        self._peer_initials = conversation.initials
        self._peer_accent = conversation.accent
        self._avatar.set_identity(
            conversation.initials,
            conversation.accent,
            image_url=conversation.avatar_url,
        )

        if conversation.online:
            self._online_dot.show()
            self._status.setText("Online")
            self._status.setStyleSheet("")
        else:
            self._online_dot.hide()
            self._status.setText("Group" if conversation.is_group else "Offline")
            self._status.setStyleSheet("color: #8B849C; font-size: 12px;")

        self._clear_thread()
        chip = QLabel("Today")
        chip.setObjectName("DateChip")
        chip.setAlignment(Qt.AlignCenter)
        chip.setAttribute(Qt.WA_StyledBackground, True)
        chip.setMaximumWidth(80)
        wrap = QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(chip)
        wrap.addStretch()
        host = QWidget()
        host.setLayout(wrap)
        self._thread.insertWidget(self._thread.count() - 1, host)

        for message in conversation.messages:
            self._thread.insertWidget(
                self._thread.count() - 1,
                self._make_bubble(message),
            )
        self._scroll_to_bottom()

    def append_outgoing(self, text: str) -> None:
        self._thread.insertWidget(
            self._thread.count() - 1,
            self._make_bubble(
                Message(text=text, outgoing=True, time="Now", seen=False)
            ),
        )
        self._scroll_to_bottom()

    def _make_bubble(self, message: Message) -> MessageBubble:
        return MessageBubble(
            message,
            peer_url=self._peer_url,
            peer_initials=self._peer_initials,
            peer_accent=self._peer_accent,
            me_url=ME_AVATAR,
        )

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _clear_thread(self) -> None:
        while self._thread.count() > 1:
            item = self._thread.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _emit_send(self) -> None:
        text = self._input.plain()
        if not text:
            return
        self._input.clear()
        self._input._fit_height()
        self.send_requested.emit(text)
