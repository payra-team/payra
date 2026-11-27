"""Left navigation — soft selected state, icons, mascot, You profile."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from payra.resources import (
    MASCOT_PATH,
    PIGEON_PATH,
    brand_mark_label,
    load_tinted_icon,
)
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
        self._icon.setObjectName("NavItemIcon")
        self._icon.setFixedSize(22, 22)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._icon.setStyleSheet("border: none; background: transparent;")
        row.addWidget(self._icon)

        self._label = QLabel(label)
        self._label.setObjectName("NavItemLabel")
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._label.setStyleSheet("border: none; background: transparent;")
        row.addWidget(self._label, stretch=1)

        self._apply_icons()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", "true" if active else "false")
        # Avoid style().polish/unpolish — known macOS Cocoa segfault vector.
        # Force a repaint; QSS property selectors refresh on next style event.
        self.setStyle(self.style())
        self._label.setStyle(self._label.style())
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
    new_group_clicked = Signal()
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

        new_group = QPushButton("+  New Group")
        new_group.setObjectName("NewGroupButton")
        new_group.setCursor(Qt.PointingHandCursor)
        new_group.clicked.connect(self.new_group_clicked.emit)
        root.addWidget(new_group)
        root.addSpacing(14)

        self._items: dict[str, NavItem] = {}
        for key, label, icon in self._SECTIONS:
            item = NavItem(key, label, icon)
            item.clicked.connect(self._select)
            self._items[key] = item
            root.addWidget(item)

        root.addStretch(1)

        self._mascot = QLabel(self)
        self._mascot.setObjectName("NavMascot")
        self._mascot.setAlignment(Qt.AlignCenter)
        self._mascot.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._mascot.setStyleSheet("background: transparent; border: none;")
        self._mascot_source = self._load_mascot_source()
        self._last_nav_item = self._items[self._SECTIONS[-1][0]]

        self._you = QFrame()
        self._you.setObjectName("YouRow")
        self._you.setCursor(Qt.PointingHandCursor)
        self._you.setAttribute(Qt.WA_StyledBackground, True)
        you_row = QHBoxLayout(self._you)
        you_row.setContentsMargins(10, 8, 10, 8)
        you_row.setSpacing(10)
        self._you_avatar = Avatar(me.initials, me.accent, 40, image_url=me.avatar_url)
        you_row.addWidget(self._you_avatar)
        you_meta = QVBoxLayout()
        you_meta.setSpacing(0)
        you_name = QLabel("You")
        you_name.setObjectName("YouName")
        self._you_status = QLabel(me.status)
        self._you_status.setObjectName("YouStatus")
        you_meta.addWidget(you_name)
        you_meta.addWidget(self._you_status)
        you_row.addLayout(you_meta, stretch=1)
        self._you.installEventFilter(self)
        root.addWidget(self._you)

        self._mascot.lower()
        self._select("chats")
        QTimer.singleShot(0, self._position_mascot)

    @staticmethod
    def _load_mascot_source() -> QPixmap:
        for path in (PIGEON_PATH, MASCOT_PATH):
            if path.exists():
                pix = QPixmap(str(path))
                if not pix.isNull():
                    return pix
        return QPixmap()

    def _position_mascot(self) -> None:
        """Keep the pigeon unclipped: responsive size, layered behind nav items."""
        if self._mascot_source.isNull() or self.width() <= 0 or self.height() <= 0:
            self._mascot.hide()
            return

        you_top = self._you.y() if self._you.y() > 0 else max(0, self.height() - 72)
        nav_bottom = (
            self._last_nav_item.geometry().bottom()
            if self._last_nav_item.height() > 0
            else 0
        )
        avail_h = max(0, you_top - nav_bottom - 10)

        max_w = min(168, NAV_WIDTH - 48)
        aspect = self._mascot_source.height() / max(1, self._mascot_source.width())

        if avail_h >= int(max_w * aspect):
            target_w = max_w
        else:
            # Responsive scale on shorter windows; overlaps behind nav texts cleanly.
            target_w = max(124, min(max_w, int(self.height() * 0.23)))

        target_h = max(1, int(round(target_w * aspect)))
        y = max(0, you_top - target_h - 4)
        overlaps_nav = nav_bottom > 0 and y < nav_bottom + 4
        opacity = 0.42 if overlaps_nav else 1.0

        dpr = max(1.0, self.devicePixelRatioF())
        pw = max(1, int(round(target_w * dpr)))
        ph = max(1, int(round(target_h * dpr)))
        scaled = self._mascot_source.scaled(
            pw, ph, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        if opacity < 1.0:
            faded = QImage(scaled.size(), QImage.Format_ARGB32_Premultiplied)
            faded.fill(Qt.transparent)
            painter = QPainter(faded)
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            pix = QPixmap.fromImage(faded)
        else:
            pix = scaled
        pix.setDevicePixelRatio(dpr)

        x = (self.width() - target_w) // 2
        self._mascot.setPixmap(pix)
        self._mascot.setGeometry(x, y, target_w, target_h)
        self._mascot.lower()
        self._mascot.show()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_mascot()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._position_mascot()

    def refresh_you(self) -> None:
        """Reload current-user avatar/status after a profile photo change."""
        from payra.models.demo_data import current_user
        from payra.ui.avatar_cache import avatar_cache

        me = current_user()
        avatar_cache().invalidate(me.avatar_url)
        self._you_avatar.set_identity(me.initials, me.accent, image_url=me.avatar_url)
        self._you_status.setText(me.status or "Online")

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._you and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.you_clicked.emit()
                return True
        return super().eventFilter(obj, event)

    def _select(self, key: str) -> None:
        for k, item in self._items.items():
            item.set_active(k == key)
        self.section_changed.emit(key)
