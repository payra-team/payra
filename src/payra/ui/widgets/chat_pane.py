"""Center conversation — bubbles, composer, image open + auto-scroll."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QTimer, Qt, Signal
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

from payra.models.demo_data import ME_AVATAR, Conversation, Message, current_user
from payra.ui.avatar_cache import avatar_cache
from payra.ui.effects import apply_card_shadow
from payra.ui.widgets.avatar import Avatar, OnlineDot
from payra.ui.widgets.image_viewer import ImageViewerDialog
from payra.ui.widgets.shimmer import MessageThreadShimmer

_BUBBLE_IN = QColor("#FFFFFF")
_BUBBLE_OUT = QColor("#E6DFFF")
_RADIUS = 14

_EMOJI_SET = [
    "😀", "😁", "😂", "🤣", "😊", "😇", "🙂", "😉",
    "😍", "😘", "😜", "🤔", "😎", "🤩", "😢", "😭",
    "😤", "😅", "🤗", "🙌", "👍", "👎", "👏", "🙏",
    "🔥", "✨", "💯", "🎉", "❤️", "💜", "💙", "💚",
]


class BubbleCard(QWidget):
    def __init__(self, outgoing: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._outgoing = outgoing
        self._bg = _BUBBLE_OUT if outgoing else _BUBBLE_IN
        self.setMaximumWidth(320)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 6)
        self._layout.setSpacing(4)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bg)
        painter.drawRoundedRect(self.rect(), _RADIUS, _RADIUS)


class _ClickableImage(QLabel):
    clicked = Signal(str)

    def __init__(self, url: str, max_w: int = 260, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self._orig_pixmap = None
        self._max_w = max_w
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Tap to view · zoom")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.setStyleSheet("background: transparent; border: none;")
        # Placeholder until pixmap loads — compact, not a huge empty frame
        w = max(80, min(160, max_w))
        self.setFixedSize(w, int(w * 0.75))

    def set_photo(self, pixmap) -> None:
        if pixmap is None or pixmap.isNull():
            return
        self._orig_pixmap = pixmap
        self._rescale()

    def set_max_width(self, max_w: int) -> None:
        if max_w == self._max_w:
            return
        self._max_w = max_w
        self._rescale()

    def _rescale(self) -> None:
        if self._orig_pixmap is None or self._orig_pixmap.isNull():
            w = max(80, min(160, self._max_w))
            self.setFixedSize(w, int(w * 0.75))
            return
        max_w = max(80, min(260, self._max_w))
        scaled = self._orig_pixmap.scaled(
            max_w, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setFixedSize(scaled.size())
        self.setPixmap(scaled)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._url:
            self.clicked.emit(self._url)
        super().mousePressEvent(event)


class MessageBubble(QWidget):
    image_clicked = Signal(str)

    def __init__(
        self,
        message: Message,
        *,
        peer_url: str,
        peer_initials: str,
        peer_accent: str,
        me_url: str = ME_AVATAR,
        max_bubble_width: int = 320,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        del peer_url, peer_initials, peer_accent, me_url
        outgoing = message.outgoing
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(0)

        card = BubbleCard(outgoing)
        card.setMaximumWidth(max(120, max_bubble_width))
        self._card = card
        self._image: _ClickableImage | None = None
        self._text: QLabel | None = None
        inner_max = max(80, max_bubble_width - 24)

        if message.image_path:
            img = _ClickableImage(message.image_path, max_w=inner_max)
            img.clicked.connect(self.image_clicked.emit)
            self._image = img

            def _apply(url: str, pix, label=img) -> None:
                del url
                label.set_photo(pix)

            cached = avatar_cache().get(message.image_path, _apply)
            if cached is not None:
                _apply(message.image_path, cached)
            card._layout.addWidget(img, 0, Qt.AlignLeft if not outgoing else Qt.AlignRight)

        show_text = bool(message.text) and not (
            message.image_path and message.text.startswith("📷")
        )
        if show_text:
            text = QLabel(message.text)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            text.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            text.setStyleSheet(
                "background: transparent; color: #1C1730; font-size: 14px; "
                "border: none; padding: 0;"
            )
            text.setMaximumWidth(inner_max)
            self._text = text
            card._layout.addWidget(text)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(4)
        meta.addStretch()
        time = QLabel(message.time)
        time.setStyleSheet(
            "background: transparent; color: #8B849C; font-size: 10px; border: none;"
        )
        meta.addWidget(time)
        if outgoing:
            mark = "✓✓" if message.seen else "✓"
            checks = QLabel(mark)
            color = "#7B61FF" if message.seen else "#B0A8C4"
            checks.setStyleSheet(
                f"background: transparent; color: {color}; font-size: 10px; "
                "font-weight: 700; border: none; padding-left: 2px;"
            )
            checks.setToolTip("Seen" if message.seen else "Sent")
            meta.addWidget(checks)
        card._layout.addLayout(meta)

        if outgoing:
            row.addStretch(1)
            row.addWidget(card, 0, Qt.AlignRight | Qt.AlignBottom)
        else:
            row.addWidget(card, 0, Qt.AlignLeft | Qt.AlignBottom)
            row.addStretch(1)

    def set_max_bubble_width(self, max_w: int) -> None:
        max_w = max(120, max_w)
        self._card.setMaximumWidth(max_w)
        inner = max(80, max_w - 24)
        if self._text is not None:
            self._text.setMaximumWidth(inner)
        if self._image is not None:
            self._image.set_max_width(inner)


class ExpandingInput(QTextEdit):
    send_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ComposerInput")
        self.setPlaceholderText("Write a message…")
        self.setToolTip("Enter to send · Shift+Enter for new line")
        self.setAcceptRichText(False)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(40)
        self.setMaximumHeight(130)
        self.textChanged.connect(self._fit_height)
        self._fit_height()

    def _fit_height(self) -> None:
        doc = self.document()
        doc.setTextWidth(max(self.viewport().width(), 100))
        h = int(doc.size().height()) + 18
        h = max(40, min(130, h))
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
        painter.setBrush(QColor("#1C1730"))
        cx = self.width() // 2
        for dy in (-8, 0, 8):
            painter.drawEllipse(cx - 2, self.height() // 2 + dy - 2, 4, 4)


class ChatPane(QWidget):
    send_requested = Signal(str)
    attach_requested = Signal()
    profile_clicked = Signal()
    star_requested = Signal()
    load_older_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChatPane")
        self._peer_url = ""
        self._peer_initials = "?"
        self._peer_accent = "#7B61FF"
        self._emoji_picker = EmojiPicker(self)
        self._empty: QLabel | None = None
        self._has_more = False
        self._loading_older = False
        self._conversation_id = ""
        self._scroll: QScrollArea | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

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

        message_well = QFrame()
        message_well.setObjectName("MessageArea")
        message_well.setAttribute(Qt.WA_StyledBackground, True)
        well_layout = QVBoxLayout(message_well)
        well_layout.setContentsMargins(8, 8, 8, 8)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("MessageScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._thread_host = QWidget()
        self._thread_host.setStyleSheet("background: transparent;")
        self._thread = QVBoxLayout(self._thread_host)
        self._thread.setContentsMargins(4, 8, 4, 12)
        self._thread.setSpacing(4)
        self._thread.addStretch()
        self._scroll.setWidget(self._thread_host)
        self._scroll.viewport().installEventFilter(self)
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)
        well_layout.addWidget(self._scroll)
        root.addWidget(message_well, stretch=1)

        composer = QWidget()
        composer.setObjectName("ComposerBar")
        composer.setAttribute(Qt.WA_StyledBackground, True)
        apply_card_shadow(composer, blur=16, y=3, alpha=24)
        composer_row = QHBoxLayout(composer)
        composer_row.setContentsMargins(12, 10, 12, 10)
        composer_row.setSpacing(10)
        composer_row.setAlignment(Qt.AlignBottom)

        self._attach = QToolButton()
        self._attach.setText("📎")
        self._attach.setObjectName("AttachButton")
        self._attach.setToolTip("Attach image")
        self._attach.setCursor(Qt.PointingHandCursor)
        self._attach.clicked.connect(self.attach_requested.emit)
        composer_row.addWidget(self._attach)

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

        self._emoji_btn = QToolButton()
        self._emoji_btn.setText("☺")
        self._emoji_btn.setObjectName("EmojiButton")
        self._emoji_btn.setToolTip("Emoji")
        self._emoji_btn.setCursor(Qt.PointingHandCursor)
        self._emoji_btn.clicked.connect(self._toggle_emoji)
        input_row.addWidget(self._emoji_btn, 0, Qt.AlignBottom)
        composer_row.addWidget(input_wrap, stretch=1)

        self._send = QPushButton("➤")
        self._send.setObjectName("SendButton")
        self._send.setCursor(Qt.PointingHandCursor)
        self._send.clicked.connect(self._emit_send)
        composer_row.addWidget(self._send)

        root.addWidget(composer)
        self._emoji_picker.emoji_chosen.connect(self._insert_emoji)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._name and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.profile_clicked.emit()
                return True
        if (
            self._scroll is not None
            and obj is self._scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._reflow_bubbles()
        return super().eventFilter(obj, event)

    def _bubble_max_width(self) -> int:
        vp_w = self._scroll.viewport().width()
        if vp_w <= 0:
            return 320
        return max(150, min(380, int(vp_w * 0.78)))

    def _reflow_bubbles(self) -> None:
        vp_w = self._scroll.viewport().width()
        if vp_w > 0:
            self._thread_host.setMaximumWidth(vp_w)
        max_w = self._bubble_max_width()
        for i in range(self._thread.count() - 1):
            w = self._thread.itemAt(i).widget()
            if isinstance(w, MessageBubble):
                w.set_max_bubble_width(max_w)

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

    def _open_image(self, url: str) -> None:
        ImageViewerDialog(url, self.window()).exec()

    def set_loading(self, loading: bool, message: str = "Loading messages…") -> None:
        """WhatsApp-style shimmer while messages load (no modal dialog)."""
        del message
        if loading:
            self._clear_thread()
            self._thread.insertWidget(self._thread.count() - 1, MessageThreadShimmer())
            self._status.setText("Loading…")
            self._online_dot.hide()
        # caller replaces content via show_conversation when done

    def set_sending(self, sending: bool) -> None:
        enabled = not sending
        self._input.setEnabled(enabled)
        self._attach.setEnabled(enabled)
        self._emoji_btn.setEnabled(enabled)
        self._send.setEnabled(enabled)
        if sending:
            if not hasattr(self, "_status_before_send"):
                self._status_before_send = self._status.text()
            self._status.setText("Sending…")
            self._input.setPlaceholderText("Sending…")
        else:
            prev = getattr(self, "_status_before_send", None)
            if prev:
                self._status.setText(prev)
            self._status_before_send = None
            self._input.setPlaceholderText("Write a message…")

    def show_conversation(self, conversation: Conversation) -> None:
        self._conversation_id = conversation.id or ""
        self._has_more = bool(getattr(conversation, "has_more_messages", False))
        self._loading_older = False
        self.update_header(conversation)

        self._clear_thread()

        if not conversation.id:
            empty = QLabel(conversation.about or "Pick a chat from the left, or start a new one.")
            empty.setObjectName("DialogMuted")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #8B849C; font-size: 14px; padding: 48px 24px; background: transparent;"
            )
            self._empty = empty
            self._thread.insertWidget(self._thread.count() - 1, empty)
            return

        if self._has_more:
            tip = QLabel("Scroll up for earlier messages")
            tip.setObjectName("DialogMuted")
            tip.setAlignment(Qt.AlignCenter)
            tip.setStyleSheet(
                "color: #A39BB8; font-size: 11px; padding: 8px; background: transparent;"
            )
            self._thread.insertWidget(self._thread.count() - 1, tip)

        chip = QLabel("Today")
        chip.setObjectName("DateChip")
        chip.setAlignment(Qt.AlignCenter)
        chip.setAttribute(Qt.WA_StyledBackground, True)
        chip.setMaximumWidth(88)
        wrap = QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(chip)
        wrap.addStretch()
        host = QWidget()
        host.setLayout(wrap)
        self._thread.insertWidget(self._thread.count() - 1, host)

        if not conversation.messages:
            empty = QLabel("No messages yet — say hello 👋")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #8B849C; font-size: 13px; padding: 28px; background: transparent;"
            )
            self._empty = empty
            self._thread.insertWidget(self._thread.count() - 1, empty)
        else:
            for message in conversation.messages:
                bubble = self._make_bubble(message)
                self._thread.insertWidget(self._thread.count() - 1, bubble)

        self._scroll_to_bottom()

    def update_header(self, conversation: Conversation) -> None:
        """Update header title/avatar/status without clearing the message thread."""
        self._name.setText(conversation.name or "Select a chat")
        self._peer_url = conversation.avatar_url
        self._peer_initials = conversation.initials
        self._peer_accent = conversation.accent
        self._avatar.set_identity(
            conversation.initials or "?",
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

    def prepend_messages(self, messages: list[Message], has_more: bool) -> None:
        """Insert an older page above the current thread, keeping scroll position."""
        self._has_more = has_more
        self._loading_older = False
        if not messages:
            return

        bar = self._scroll.verticalScrollBar()
        old_max = bar.maximum()
        old_val = bar.value()

        # Insert after optional tip / before existing bubbles: find first MessageBubble index
        insert_at = 0
        for i in range(self._thread.count() - 1):
            widget = self._thread.itemAt(i).widget()
            if isinstance(widget, MessageBubble):
                insert_at = i
                break
            insert_at = i + 1

        for offset, message in enumerate(messages):
            self._thread.insertWidget(insert_at + offset, self._make_bubble(message))

        def _restore() -> None:
            new_max = bar.maximum()
            bar.setValue(old_val + max(0, new_max - old_max))

        QTimer.singleShot(0, self, _restore)
        QTimer.singleShot(40, self, _restore)

    def _on_scroll(self, value: int) -> None:
        if value > 40:
            return
        if not self._has_more or self._loading_older or not self._conversation_id:
            return
        self._loading_older = True
        self.load_older_requested.emit()

    def _dismiss_empty(self) -> None:
        if self._empty is not None:
            self._thread.removeWidget(self._empty)
            self._empty.deleteLater()
            self._empty = None

    def _is_near_bottom(self) -> bool:
        bar = self._scroll.verticalScrollBar()
        return bar.maximum() <= 0 or bar.value() >= bar.maximum() - 140

    def append_message(self, message: Message) -> None:
        """Append a live incoming or outgoing Message bubble."""
        self._dismiss_empty()
        should_scroll = message.outgoing or self._is_near_bottom()
        self._thread.insertWidget(self._thread.count() - 1, self._make_bubble(message))
        if should_scroll:
            self._scroll_to_bottom()

    def append_outgoing(self, text: str, image_path: str | None = None, *, time_label: str = "Now") -> None:
        self.append_message(
            Message(
                text=text,
                outgoing=True,
                time=time_label or "Now",
                seen=False,
                image_path=image_path,
            )
        )

    def append_incoming(self, message: Message) -> None:
        self.append_message(message)

    def _make_bubble(self, message: Message) -> MessageBubble:
        me = current_user()
        bubble = MessageBubble(
            message,
            peer_url=self._peer_url,
            peer_initials=self._peer_initials,
            peer_accent=self._peer_accent,
            me_url=me.avatar_url or ME_AVATAR,
            max_bubble_width=self._bubble_max_width(),
        )
        bubble.image_clicked.connect(self._open_image)
        return bubble

    def _scroll_to_bottom(self) -> None:
        def _go() -> None:
            if self._scroll is None:
                return
            bar = self._scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        QTimer.singleShot(0, self, _go)
        QTimer.singleShot(50, self, _go)
        QTimer.singleShot(160, self, _go)

    def _clear_thread(self) -> None:
        self._empty = None
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
