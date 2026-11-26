"""Profile-related dialogs: media gallery, members, add member."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
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
    """Group members list with admin role settings (promote / demote / remove).

    Read ``pending_action()`` after ``exec()`` returns Accepted:
      ("promote"|"demote"|"remove", ContactPerson) or ("leave", None)
    """

    def __init__(
        self,
        members: list[ContactPerson],
        title: str = "Members",
        parent: QWidget | None = None,
        *,
        my_user_id: str = "",
        my_role: str = "",
        can_manage: bool | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 480)
        self._members = list(members)
        self._my_user_id = my_user_id
        self._my_role = (my_role or "").lower()
        self._can_manage = (
            self._my_role == "admin" if can_manage is None else bool(can_manage)
        )
        self._pending: tuple[str, ContactPerson | None] | None = None
        admin_count = sum(1 for m in members if (m.member_role or "").lower() == "admin")
        self._sole_admin = (
            self._my_role == "admin"
            and admin_count <= 1
            and bool(self._my_user_id)
            and any(m.id == self._my_user_id for m in members)
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        hint = QLabel(
            "Admins can promote, demote, or remove members."
            if self._can_manage
            else f"{len(members)} people in this group."
        )
        hint.setObjectName("DialogMuted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("DialogScroll")
        host = QWidget()
        host.setObjectName("DialogBody")
        layout = QVBoxLayout(host)
        layout.setSpacing(8)
        for member in members:
            layout.addWidget(self._row(member, admin_count=admin_count))
        layout.addStretch()
        scroll.setWidget(host)
        root.addWidget(scroll, stretch=1)

        if self._my_user_id and any(m.id == self._my_user_id for m in members):
            leave = QPushButton("Leave group")
            leave.setObjectName("DialogDangerButton")
            leave.setCursor(Qt.PointingHandCursor)
            if self._sole_admin:
                leave.setEnabled(False)
                leave.setToolTip("Promote another admin before leaving.")
            else:
                leave.clicked.connect(self._on_leave)
            root.addWidget(leave)

        buttons = _dialog_buttons()
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def pending_action(self) -> tuple[str, ContactPerson | None] | None:
        return self._pending

    def _on_leave(self) -> None:
        self._pending = ("leave", None)
        self.accept()

    def _row(self, member: ContactPerson, *, admin_count: int) -> QWidget:
        row = QFrame()
        row.setObjectName("DialogListRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(12)
        h.addWidget(Avatar(member.initials, member.accent, 40, image_url=member.avatar_url))
        meta = QVBoxLayout()
        meta.setSpacing(2)
        name_text = member.name
        if self._my_user_id and member.id == self._my_user_id:
            name_text = f"{member.name} (you)"
        name = QLabel(name_text)
        name.setObjectName("DialogRowTitle")
        member_role = (member.member_role or "").lower()
        role_label = "Admin" if member_role == "admin" else (member.role or "Member")
        role = QLabel(role_label)
        role.setObjectName("DialogMuted")
        meta.addWidget(name)
        meta.addWidget(role)
        h.addLayout(meta, stretch=1)

        is_self = bool(self._my_user_id and member.id == self._my_user_id)
        show_menu = self._can_manage and not is_self
        if show_menu:
            more = QToolButton()
            more.setText("⋮")
            more.setObjectName("DialogGhostButton")
            more.setCursor(QCursor(Qt.PointingHandCursor))
            more.setPopupMode(QToolButton.InstantPopup)
            menu = QMenu(more)
            is_admin = member_role == "admin"
            if is_admin:
                demote = QAction("Dismiss as admin", more)
                demote.setEnabled(admin_count > 1)
                demote.triggered.connect(
                    lambda _=False, m=member: self._queue("demote", m)
                )
                menu.addAction(demote)
            else:
                promote = QAction("Make group admin", more)
                promote.triggered.connect(
                    lambda _=False, m=member: self._queue("promote", m)
                )
                menu.addAction(promote)
            remove = QAction("Remove from group", more)
            if is_admin and admin_count <= 1:
                remove.setEnabled(False)
            remove.triggered.connect(lambda _=False, m=member: self._queue("remove", m))
            menu.addAction(remove)
            more.setMenu(menu)
            h.addWidget(more)
        return row

    def _queue(self, action: str, member: ContactPerson) -> None:
        self._pending = (action, member)
        self.accept()


class AddMemberDialog(PayraDialog):
    """Search + multi-select contacts to add into a group conversation.

    Selection is read via ``selected_members()`` *after* ``exec()`` returns
    Accepted — avoids nested modals / macOS Cocoa crashes from signal handlers
    that open another QMessageBox while this dialog is still accepting.
    """

    members_selected = Signal(list)  # retained for callers that prefer signals

    def __init__(
        self,
        candidates: list[ContactPerson],
        parent: QWidget | None = None,
        *,
        group_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add members")
        self.setMinimumSize(400, 500)
        self._candidates = list(candidates)
        self._checks: dict[str, QCheckBox] = {}
        self._selected: list[ContactPerson] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        heading = QLabel("Add members")
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        subtitle = (
            f"Choose people to invite to “{group_name}”."
            if group_name
            else "Choose people to invite to this group."
        )
        hint = QLabel(subtitle)
        hint.setObjectName("DialogMuted")
        hint.setWordWrap(True)
        root.addWidget(hint)

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

        if not candidates:
            empty = QLabel("Everyone in your directory is already in this group.")
            empty.setObjectName("DialogMuted")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            self._list.addWidget(empty)
        else:
            for person in candidates:
                self._list.addWidget(self._make_row(person))
        self._list.addStretch()
        scroll.setWidget(self._host)
        root.addWidget(scroll, stretch=1)

        self._count = QLabel("")
        self._count.setObjectName("DialogMuted")
        self._update_count()
        root.addWidget(self._count)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.hide()
        root.addWidget(self.error)

        buttons = _dialog_buttons("Add")
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        if self._ok_button is not None:
            self._ok_button.setEnabled(bool(candidates))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)

    def selected_members(self) -> list[ContactPerson]:
        return list(self._selected)

    def _make_row(self, person: ContactPerson) -> QWidget:
        row = QFrame()
        row.setObjectName("DialogListRow")
        row.setProperty("person_id", person.id)
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)

        check = QCheckBox()
        check.setObjectName("DialogCheck")
        check.toggled.connect(lambda _checked: self._update_count())
        self._checks[person.id] = check
        h.addWidget(check)
        h.addWidget(Avatar(person.initials, person.accent, 36, image_url=person.avatar_url))

        meta = QVBoxLayout()
        meta.setSpacing(2)
        name = QLabel(person.name)
        name.setObjectName("DialogRowTitle")
        sub_bits = []
        if person.username:
            sub_bits.append(f"@{person.username}")
        if person.email:
            sub_bits.append(person.email)
        sub = QLabel("  ·  ".join(sub_bits) if sub_bits else (person.role or "Member"))
        sub.setObjectName("DialogMuted")
        meta.addWidget(name)
        meta.addWidget(sub)
        h.addLayout(meta, stretch=1)
        return row

    def _checked_people(self) -> list[ContactPerson]:
        return [p for p in self._candidates if self._checks.get(p.id) and self._checks[p.id].isChecked()]

    def _update_count(self) -> None:
        n = len(self._checked_people())
        if not self._candidates:
            self._count.setText("No one left to add.")
        elif n == 0:
            self._count.setText("Select at least one person.")
        elif n == 1:
            self._count.setText("1 person selected.")
        else:
            self._count.setText(f"{n} people selected.")

    def _filter(self, text: str) -> None:
        q = text.strip().lower().lstrip("@")
        for i in range(self._list.count() - 1):
            item = self._list.itemAt(i)
            w = item.widget() if item else None
            if not w:
                continue
            pid = w.property("person_id")
            if not pid:
                continue
            person = next((p for p in self._candidates if p.id == pid), None)
            if not person:
                continue
            hay = f"{person.name} {person.username} {person.email}".lower()
            w.setVisible(not q or q in hay)

    def _accept(self) -> None:
        if not self._candidates:
            self.reject()
            return
        selected = self._checked_people()
        if not selected:
            self.error.setText("Select at least one person to add.")
            self.error.show()
            return
        # Close first — callers read selected_members() after exec().
        # Do not emit here (nested modal handlers cause macOS Cocoa crashes).
        self._selected = selected
        self.accept()


class _ContactPickRow(QFrame):
    """Contact row with painted selection (no child-label border artifacts)."""

    clicked = Signal(object)  # ContactPerson

    def __init__(self, person: ContactPerson, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.person = person
        self._selected = False
        self.setObjectName("DialogListRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(False)

        h = QHBoxLayout(self)
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
        name.setStyleSheet("border: none; background: transparent;")
        sub = QLabel(f"@{person.username}  ·  {person.email}")
        sub.setObjectName("DialogMuted")
        sub.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sub.setStyleSheet("border: none; background: transparent;")
        meta.addWidget(name)
        meta.addWidget(sub)
        h.addLayout(meta, stretch=1)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.person)
        super().mousePressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self._selected:
            painter.setBrush(QColor("#EDE8FF"))
            painter.setPen(QPen(QColor("#7B61FF"), 2))
        else:
            painter.setBrush(QColor("#F7F5FB"))
            painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 14, 14)


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
        self._rows: dict[str, _ContactPickRow] = {}
        self._pending: tuple[ContactPerson, str] | None = None

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
            row = _ContactPickRow(person)
            row.clicked.connect(self._select_person)
            self._rows[person.id] = row
            self._list.addWidget(row)
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
        self.finished.connect(self._emit_pending)
        self._filter("")

    def _select_person(self, person: ContactPerson) -> None:
        self._selected = person
        for pid, row in self._rows.items():
            row.set_selected(pid == person.id)

    def _filter(self, text: str) -> None:
        q = text.strip().lower().lstrip("@")
        for person in self._directory:
            row = self._rows[person.id]
            hay = f"{person.name} {person.username} {person.email}".lower()
            row.setVisible(not q or q in hay)

    def _accept(self) -> None:
        if not self._selected:
            visible = [p for p in self._directory if self._rows[p.id].isVisible()]
            if len(visible) == 1:
                self._selected = visible[0]
            else:
                return
        # Close first, then emit — avoids macOS crash from nested work while dialog dies.
        self._pending = (self._selected, self.message.text().strip())
        self.accept()

    def _emit_pending(self, result: int) -> None:
        from PySide6.QtWidgets import QDialog

        if result != QDialog.DialogCode.Accepted or self._pending is None:
            return
        person, message = self._pending
        self._pending = None
        self.chat_requested.emit(person, message)


class NewGroupDialog(PayraDialog):
    """Create a group with title + selected members.

    Emits ``group_requested`` only after the dialog has closed (via ``finished``),
    matching NewChatDialog — avoids macOS crashes from work during accept().
    """

    group_requested = Signal(str, list)  # title, list[ContactPerson]

    def __init__(
        self,
        directory: list[ContactPerson],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Group")
        self.setMinimumSize(440, 560)
        self._directory = directory
        self._checks: dict[str, QCheckBox] = {}
        self._pending: tuple[str, list[ContactPerson]] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        heading = QLabel("New Group")
        heading.setObjectName("DialogTitle")
        root.addWidget(heading)

        hint = QLabel("Name the group and pick at least one member.")
        hint.setObjectName("DialogMuted")
        root.addWidget(hint)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("DialogSearch")
        self.title_input.setPlaceholderText("Group name (e.g. SDP-2 Team)")
        root.addWidget(self.title_input)

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
        for person in directory:
            self._list.addWidget(self._make_row(person))
        self._list.addStretch()
        scroll.setWidget(self._host)
        root.addWidget(scroll, stretch=1)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.hide()
        root.addWidget(self.error)

        buttons = _dialog_buttons("Create group")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self._accept)
        root.addWidget(buttons)
        self.finished.connect(self._emit_pending)

    def selected_group(self) -> tuple[str, list[ContactPerson]] | None:
        return self._pending

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
        name = QLabel(f"{person.name}  ·  @{person.username}")
        name.setObjectName("DialogRowTitle")
        h.addWidget(name, stretch=1)
        return row

    def _filter(self, text: str) -> None:
        q = text.strip().lower().lstrip("@")
        for i in range(self._list.count() - 1):
            item = self._list.itemAt(i)
            w = item.widget() if item else None
            if not w:
                continue
            pid = w.property("person_id")
            person = next((p for p in self._directory if p.id == pid), None)
            if not person:
                continue
            hay = f"{person.name} {person.username} {person.email}".lower()
            w.setVisible(not q or q in hay)

    def _accept(self) -> None:
        title = self.title_input.text().strip()
        selected = [p for p in self._directory if self._checks[p.id].isChecked()]
        if len(title) < 2:
            self.error.setText("Enter a group name (at least 2 characters).")
            self.error.show()
            return
        if not selected:
            self.error.setText("Select at least one member.")
            self.error.show()
            return
        self._pending = (title, selected)
        self.accept()

    def _emit_pending(self, result: int) -> None:
        from PySide6.QtWidgets import QDialog as _QDialog

        if result != _QDialog.DialogCode.Accepted or self._pending is None:
            return
        title, people = self._pending
        self._pending = None
        self.group_requested.emit(title, people)


class MyProfileDialog(PayraDialog):
    """Current user profile (nav You row)."""

    logout_requested = Signal()
    profile_updated = Signal()

    def __init__(self, user=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from payra.models.demo_data import current_user
        from payra.services.auth import supabase_ready

        user = user or current_user()
        self._user = user
        self.setWindowTitle("My Profile")
        self.setMinimumSize(380, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("My Profile")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        avatar_wrap = QHBoxLayout()
        avatar_wrap.addStretch()
        self._avatar = Avatar(
            user.initials, user.accent, 96, image_url=user.avatar_url, clickable=True
        )
        self._avatar.setToolTip("Change profile photo")
        self._avatar.clicked.connect(self._on_change_photo)
        avatar_wrap.addWidget(self._avatar)
        avatar_wrap.addStretch()
        root.addLayout(avatar_wrap)

        change_photo = QPushButton("Change photo")
        change_photo.setObjectName("DialogGhostButton")
        change_photo.setCursor(Qt.PointingHandCursor)
        change_photo.clicked.connect(self._on_change_photo)
        root.addWidget(change_photo, 0, Qt.AlignHCenter)

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

        note = QLabel(
            "Photos are compressed before upload to Supabase Storage"
            if supabase_ready()
            else "Local profile · connect Supabase via .env to sync photos"
        )
        note.setObjectName("DialogMuted")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
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

    def _on_change_photo(self) -> None:
        from payra.services import auth as auth_service
        from payra.services import storage as storage_service
        from payra.ui.widgets.loading import run_busy

        if not auth_service.supabase_ready():
            QMessageBox.information(
                self,
                "Profile photo",
                "Connect Supabase (.env) to upload profile photos.",
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose profile photo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)",
        )
        if not path:
            return

        def work():
            url = storage_service.upload_avatar(path)
            return auth_service.update_avatar_url(url)

        def ok(user) -> None:
            old_url = getattr(self._user, "avatar_url", None)
            self._user = user
            avatar_cache().invalidate(old_url)
            avatar_cache().invalidate(getattr(user, "avatar_url", None))
            self._avatar.set_identity(
                user.initials, user.accent, image_url=user.avatar_url
            )
            self.profile_updated.emit()
            QMessageBox.information(self, "Profile photo", "Photo updated.")

        run_busy(
            self,
            "Optimizing & uploading photo…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(self, "Upload failed", err),
        )

    def _on_logout(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        from payra.services import auth as auth_service
        from payra.ui.widgets.loading import run_busy

        reply = QMessageBox.question(
            self,
            "Log out",
            "Log out of Payra on this device?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        def work():
            auth_service.logout()
            return True

        def ok(_result) -> None:
            self.logout_requested.emit()
            self.accept()

        run_busy(
            self,
            "Signing out…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(self, "Log out", err),
        )

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
