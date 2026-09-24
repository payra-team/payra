"""Left navigation — soft selected state, icons, mascot, You profile."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from payra.resources import brand_mark_label, load_mascot_pixmap, load_tinted_icon
from payra.ui.theme import ACCENT, NAV_WIDTH, TEXT_MUTED
from payra.ui.widgets.avatar import Avatar


class NavItem(QFrame):
    """One nav row: icon + label (ChatFlow selected style)."""

    clicked = Signal(str)

    def __init__(
        self,
        key: str,
        label: str,
        icon_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.key = key
        self._icon_name = icon_name
        self._active = False

        self.setObjectName("NavItemRow")
        self.setProperty("active", "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumHeight(48)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)

        self._icon = QLabel()
        self._icon.setFixedSize(22, 22)
        self._icon.setAlignment(Qt.AlignCenter)
        row.addWidget(self._icon)

        self._label = QLabel(label)
        self._label.setObjectName("NavItemLabel")
        row.addWidget(self._label, stretch=1)

        self._apply_icons()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)
        self._apply_icons()

    def _apply_icons(self) -> None:
        color = ACCENT if self._active else TEXT_MUTED
        icon = load_tinted_icon(self._icon_name, color, 22)
        self._icon.setPixmap(icon.pixmap(22, 22))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class NavSidebar(QWidget):
    new_chat_clicked = Signal()
    section_changed = Signal(str)
    you_clicked = Signal()

    _SECTIONS = (
        ("chats", "Chats", "chats"),
        ("groups", "Groups", "groups"),
        ("contacts", "Contacts", "contacts"),
        ("starred", "Starred", "starred"),
        ("ai", "Payra AI", "ai"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavSidebar")
        self.setFixedWidth(NAV_WIDTH)

        from payra.models.demo_data import current_user

        me = current_user()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 14)
        root.setSpacing(4)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(brand_mark_label(36, "BrandMark"))
        title = QLabel("Payra")
        title.setObjectName("BrandLabel")
        brand.addWidget(title)
        brand.addStretch()
        root.addLayout(brand)
        root.addSpacing(14)

        new_chat = QPushButton("+  New Chat")
        new_chat.setObjectName("NewChatButton")
        new_chat.setCursor(Qt.PointingHandCursor)
        new_chat.clicked.connect(self.new_chat_clicked.emit)
        root.addWidget(new_chat)
        root.addSpacing(14)

        self._items: dict[str, NavItem] = {}
        for key, label, icon in self._SECTIONS:
            item = NavItem(key, label, icon)
            item.clicked.connect(self._select)
            self._items[key] = item
            root.addWidget(item)

        root.addStretch(1)

        mascot = QLabel()
        mascot.setObjectName("NavMascot")
        mascot.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        mascot.setPixmap(load_mascot_pixmap(max_width=NAV_WIDTH - 28))
        mascot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        root.addWidget(mascot)

        self._you = QFrame()
        self._you.setObjectName("YouRow")
        self._you.setCursor(Qt.PointingHandCursor)
        self._you.setAttribute(Qt.WA_StyledBackground, True)
        you_row = QHBoxLayout(self._you)
        you_row.setContentsMargins(10, 8, 10, 8)
        you_row.setSpacing(10)
        you_row.addWidget(
            Avatar(me.initials, me.accent, 40, image_url=me.avatar_url)
        )
        you_meta = QVBoxLayout()
        you_meta.setSpacing(0)
        you_name = QLabel("You")
        you_name.setObjectName("YouName")
        you_status = QLabel(me.status)
        you_status.setObjectName("YouStatus")
        you_meta.addWidget(you_name)
        you_meta.addWidget(you_status)
        you_row.addLayout(you_meta, stretch=1)
        self._you.installEventFilter(self)
        root.addWidget(self._you)

        self._select("chats")

    def eventFilter(self, obj, event):  # noqa: N802
        from PySide6.QtCore import QEvent

        if obj is self._you and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.you_clicked.emit()
                return True
        return super().eventFilter(obj, event)

    def _select(self, key: str) -> None:
        for k, item in self._items.items():
            item.set_active(k == key)
        self.section_changed.emit(key)
