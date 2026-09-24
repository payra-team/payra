"""Profile-related dialogs: media gallery, members, add member."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from payra.models.demo_data import ContactPerson
from payra.ui.avatar_cache import avatar_cache
from payra.ui.theme_app import PayraDialog
from payra.ui.widgets.avatar import Avatar


class _NetworkImage(QLabel):
    """Square tile that loads a remote image."""

    def __init__(self, url: str, size: int = 96, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "background: #EDE8FF; border-radius: 14px; border: 1px solid #EEEAF5;"
        )
        cached = avatar_cache().get(url, self._on_loaded)
        if cached is not None:
            self._apply(cached)

    def _on_loaded(self, url: str, pixmap: QPixmap) -> None:
        if url == self._url:
            self._apply(pixmap)

    def _apply(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            self.width(),
            self.height(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setStyleSheet("border-radius: 14px;")


def _dialog_buttons(ok_text: str | None = None) -> QDialogButtonBox:
    if ok_text:
        box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        box.button(QDialogButtonBox.Ok).setText(ok_text)
        box.button(QDialogButtonBox.Ok).setObjectName("DialogPrimaryButton")
        box.button(QDialogButtonBox.Cancel).setObjectName("DialogGhostButton")
    else:
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.button(QDialogButtonBox.Close).setObjectName("DialogGhostButton")
    return box


class MediaGalleryDialog(PayraDialog):
    def __init__(self, urls: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Shared Media")
        self.setMinimumSize(500, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("Shared Media")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DialogScroll")
        host = QWidget()
        host.setObjectName("DialogBody")
        grid = QGridLayout(host)
        grid.setSpacing(12)
        cols = 3
        if not urls:
            empty = QLabel("No shared media yet.")
            empty.setObjectName("DialogMuted")
            grid.addWidget(empty, 0, 0)
        else:
            for i, url in enumerate(urls):
                grid.addWidget(_NetworkImage(url, 136), i // cols, i % cols)
        scroll.setWidget(host)
        root.addWidget(scroll, stretch=1)

        buttons = _dialog_buttons()
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class MembersListDialog(PayraDialog):
    def __init__(
        self,
        members: list[ContactPerson],
        title: str = "Members",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 460)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DialogScroll")
        host = QWidget()
        host.setObjectName("DialogBody")
        layout = QVBoxLayout(host)
        layout.setSpacing(8)
        for member in members:
            layout.addWidget(self._row(member))
        layout.addStretch()
        scroll.setWidget(host)
        root.addWidget(scroll, stretch=1)

        buttons = _dialog_buttons()
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _row(member: ContactPerson) -> QWidget:
        row = QFrame()
        row.setObjectName("DialogListRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(12)
        h.addWidget(Avatar(member.initials, member.accent, 40, image_url=member.avatar_url))
        meta = QVBoxLayout()
        meta.setSpacing(2)
        name = QLabel(member.name)
        name.setObjectName("DialogRowTitle")
        role = QLabel(member.role or "Member")
        role.setObjectName("DialogMuted")
        meta.addWidget(name)
        meta.addWidget(role)
        h.addLayout(meta, stretch=1)
        return row


class AddMemberDialog(PayraDialog):
    """Search + multi-select contacts to add into a group conversation."""

    members_selected = Signal(list)

    def __init__(
        self,
        candidates: list[ContactPerson],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Member")
        self.setMinimumSize(400, 500)
        self._candidates = candidates
        self._checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        heading = QLabel("Add Member")
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        self.search = QLineEdit()
        self.search.setObjectName("DialogSearch")
        self.search.setPlaceholderText("Search people…")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DialogScroll")
        self._host = QWidget()
        self._host.setObjectName("DialogBody")
        self._list = QVBoxLayout(self._host)
        self._list.setSpacing(6)
        for person in candidates:
            self._list.addWidget(self._make_row(person))
        self._list.addStretch()
        scroll.setWidget(self._host)
        root.addWidget(scroll, stretch=1)

        buttons = _dialog_buttons("Add")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)

    def _make_row(self, person: ContactPerson) -> QWidget:
        row = QFrame()
        row.setObjectName("DialogListRow")
        row.setProperty("person_id", person.id)
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)

        check = QCheckBox()
        check.setObjectName("DialogCheck")
        self._checks[person.id] = check
        h.addWidget(check)
        h.addWidget(Avatar(person.initials, person.accent, 36, image_url=person.avatar_url))

        name = QLabel(person.name)
        name.setObjectName("DialogRowTitle")
        h.addWidget(name, stretch=1)
        return row

    def _filter(self, text: str) -> None:
        q = text.strip().lower()
        for i in range(self._list.count() - 1):
            item = self._list.itemAt(i)
            w = item.widget()
            if not w:
                continue
            pid = w.property("person_id")
            person = next((p for p in self._candidates if p.id == pid), None)
            if not person:
                continue
            w.setVisible(not q or q in person.name.lower())

    def _accept(self) -> None:
        selected = [p for p in self._candidates if self._checks[p.id].isChecked()]
        self.members_selected.emit(selected)
        self.accept()


class NewChatDialog(PayraDialog):
    """Search users by name, username, or email and start a chat."""

    chat_requested = Signal(object, str)  # ContactPerson, first_message

    def __init__(
        self,
        directory: list[ContactPerson],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Chat")
        self.setMinimumSize(440, 540)
        self._directory = directory
        self._selected: ContactPerson | None = None
        self._rows: dict[str, QFrame] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        heading = QLabel("New Chat")
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        hint = QLabel("Search by name, @username, or email")
        hint.setObjectName("DialogMuted")
        root.addWidget(hint)

        self.search = QLineEdit()
        self.search.setObjectName("DialogSearch")
        self.search.setPlaceholderText("e.g. alex@payra.app or @alexj")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DialogScroll")
        host = QWidget()
        host.setObjectName("DialogBody")
        self._list = QVBoxLayout(host)
        self._list.setSpacing(6)
        for person in directory:
            self._list.addWidget(self._make_row(person))
        self._list.addStretch()
        scroll.setWidget(host)
        root.addWidget(scroll, stretch=1)

        msg_label = QLabel("First message (optional)")
        msg_label.setObjectName("DialogRowTitle")
        root.addWidget(msg_label)
        self.message = QLineEdit()
        self.message.setObjectName("DialogSearch")
        self.message.setPlaceholderText("Say hello…")
        root.addWidget(self.message)

        buttons = _dialog_buttons("Message")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)
        self._filter("")

    def _make_row(self, person: ContactPerson) -> QFrame:
        row = QFrame()
        row.setObjectName("DialogListRow")
        row.setProperty("person_id", person.id)
        row.setProperty("selected", "false")
        row.setCursor(Qt.PointingHandCursor)
        row.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)
        avatar = Avatar(person.initials, person.accent, 40, image_url=person.avatar_url)
        avatar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        h.addWidget(avatar)

        meta = QVBoxLayout()
        meta.setSpacing(2)
        name = QLabel(person.name)
        name.setObjectName("DialogRowTitle")
        name.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sub = QLabel(f"@{person.username}  ·  {person.email}")
        sub.setObjectName("DialogMuted")
        sub.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        meta.addWidget(name)
        meta.addWidget(sub)
        h.addLayout(meta, stretch=1)

        self._rows[person.id] = row
        row.mousePressEvent = (  # type: ignore[method-assign]
            lambda event, p=person, r=row: self._on_row_press(event, p, r)
        )
        return row

    def _on_row_press(self, event, person: ContactPerson, row: QFrame) -> None:
        if event.button() == Qt.LeftButton:
            self._select_person(person, row)

    def _select_person(self, person: ContactPerson, row: QFrame) -> None:
        self._selected = person
        for r in self._rows.values():
            r.setProperty("selected", "false")
            r.style().unpolish(r)
            r.style().polish(r)
        row.setProperty("selected", "true")
        row.style().unpolish(row)
        row.style().polish(row)

    def _filter(self, text: str) -> None:
        q = text.strip().lower().lstrip("@")
        for person in self._directory:
            row = self._rows[person.id]
            hay = f"{person.name} {person.username} {person.email}".lower()
            row.setVisible(not q or q in hay)

    def _accept(self) -> None:
        if not self._selected:
            # If exactly one visible row, use it
            visible = [p for p in self._directory if self._rows[p.id].isVisible()]
            if len(visible) == 1:
                self._selected = visible[0]
            else:
                return
        self.chat_requested.emit(self._selected, self.message.text().strip())
        self.accept()


class MyProfileDialog(PayraDialog):
    """Current user profile (nav You row)."""

    logout_requested = Signal()

    def __init__(self, user=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from payra.models.demo_data import current_user

        user = user or current_user()
        self.setWindowTitle("My Profile")
        self.setMinimumSize(380, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("My Profile")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        avatar_wrap = QHBoxLayout()
        avatar_wrap.addStretch()
        avatar_wrap.addWidget(
            Avatar(user.initials, user.accent, 96, image_url=user.avatar_url)
        )
        avatar_wrap.addStretch()
        root.addLayout(avatar_wrap)

        name = QLabel(user.display_name)
        name.setObjectName("DialogTitle")
        name.setAlignment(Qt.AlignCenter)
        root.addWidget(name)

        status = QLabel(user.status)
        status.setObjectName("ChatHeaderStatus")
        status.setAlignment(Qt.AlignCenter)
        root.addWidget(status)

        root.addWidget(self._field("Username", f"@{user.username}"))
        root.addWidget(self._field("Email", user.email))
        root.addWidget(self._field("About", user.about))
        root.addWidget(self._field("User ID", user.id))
        root.addStretch()

        note = QLabel("Demo profile · Will sync from Supabase Auth later")
        note.setObjectName("DialogMuted")
        note.setAlignment(Qt.AlignCenter)
        root.addWidget(note)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        logout = QPushButton("Log out")
        logout.setObjectName("DialogDangerButton")
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self._on_logout)
        close = QPushButton("Close")
        close.setObjectName("DialogGhostButton")
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.reject)
        buttons.addWidget(logout)
        buttons.addStretch()
        buttons.addWidget(close)
        root.addLayout(buttons)

    def _on_logout(self) -> None:
        self.logout_requested.emit()
        self.accept()

    @staticmethod
    def _field(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("DialogListRow")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)
        k = QLabel(label)
        k.setObjectName("DialogMuted")
        v = QLabel(value)
        v.setObjectName("DialogRowTitle")
        v.setWordWrap(True)
        lay.addWidget(k)
        lay.addWidget(v)
        return card
