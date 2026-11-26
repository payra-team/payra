"""Right-hand profile details — media, members, white-card actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from payra.models.demo_data import Conversation, ContactPerson, demo_directory
from payra.ui.theme import DETAIL_WIDTH
from payra.ui.widgets.avatar import Avatar, OnlineDot
from payra.ui.widgets.card_button import WhiteCardButton
from payra.ui.widgets.dialogs import AddMemberDialog, MediaGalleryDialog, MembersListDialog


class _ClickLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DetailPanel(QWidget):
    close_requested = Signal()
    delete_contact_requested = Signal()
    block_contact_requested = Signal()
    star_requested = Signal()
    conversation_updated = Signal(object)  # Conversation after local/live mutation
    left_group = Signal(str)  # conversation_id after leaving a group

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailPanel")
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self._conversation: Conversation | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)

        # Header
        top = QHBoxLayout()
        top_title = QLabel("Profile")
        top_title.setObjectName("SectionTitle")
        top.addWidget(top_title)
        top.addStretch()
        self._close_btn = WhiteCardButton("✕", tooltip="Close", size=40)
        self._close_btn.clicked.connect(self.close_requested.emit)
        top.addWidget(self._close_btn)
        root.addLayout(top)

        # Identity
        avatar_wrap = QHBoxLayout()
        avatar_wrap.addStretch()
        self._avatar = Avatar("?", size=96, clickable=True)
        self._avatar.clicked.connect(self._on_change_group_photo)
        avatar_wrap.addWidget(self._avatar)
        avatar_wrap.addStretch()
        root.addLayout(avatar_wrap)

        self._change_photo_btn = QPushButton("Change group photo")
        self._change_photo_btn.setObjectName("DialogGhostButton")
        self._change_photo_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._change_photo_btn.clicked.connect(self._on_change_group_photo)
        self._change_photo_btn.hide()
        root.addWidget(self._change_photo_btn, 0, Qt.AlignHCenter)

        self._name = QLabel("—")
        self._name.setObjectName("DetailName")
        self._name.setAlignment(Qt.AlignCenter)
        root.addWidget(self._name)

        status_row = QHBoxLayout()
        status_row.addStretch()
        self._dot = OnlineDot(8)
        self._status = QLabel("")
        self._status.setObjectName("ChatHeaderStatus")
        status_row.addWidget(self._dot)
        status_row.addWidget(self._status)
        status_row.addStretch()
        root.addLayout(status_row)

        self._role_chip = QLabel("")
        self._role_chip.setObjectName("DialogMuted")
        self._role_chip.setAlignment(Qt.AlignCenter)
        self._role_chip.hide()
        root.addWidget(self._role_chip)

        # Actions: star · add member · more
        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addStretch()

        self._star_btn = WhiteCardButton("★", tooltip="Starred")
        self._star_btn.clicked.connect(self._on_star)
        actions.addWidget(self._star_btn)

        self._add_btn = WhiteCardButton("＋", tooltip="Add member")
        self._add_btn.clicked.connect(self._on_add_member)
        actions.addWidget(self._add_btn)

        self._more_btn = WhiteCardButton("⋮", tooltip="More")
        self._more_menu = QMenu(self)
        self._more_menu.setObjectName("ChatHeaderMenu")
        self._delete_action = QAction("🗑️   Delete contact", self)
        self._block_action = QAction("🚫   Block contact", self)
        self._leave_action = QAction("🚪   Leave group", self)
        self._delete_action.triggered.connect(self._on_delete)
        self._block_action.triggered.connect(self._on_block)
        self._leave_action.triggered.connect(self._on_leave_group)
        self._more_menu.addAction(self._delete_action)
        self._more_menu.addAction(self._block_action)
        self._more_menu.addAction(self._leave_action)
        self._more_btn.setMenu(self._more_menu)
        self._more_btn.setPopupMode(QToolButton.InstantPopup)
        actions.addWidget(self._more_btn)

        actions.addStretch()
        root.addLayout(actions)
        root.addSpacing(6)

        # About
        about_title = QLabel("About")
        about_title.setObjectName("SectionTitle")
        root.addWidget(about_title)
        self._about = QLabel("")
        self._about.setObjectName("DetailAbout")
        self._about.setWordWrap(True)
        root.addWidget(self._about)

        # Shared media
        media_header = QHBoxLayout()
        media_title = QLabel("Shared Media")
        media_title.setObjectName("SectionTitle")
        self._media_see_all = _ClickLabel("See All")
        self._media_see_all.setObjectName("LinkAccent")
        self._media_see_all.setCursor(QCursor(Qt.PointingHandCursor))
        self._media_see_all.clicked.connect(self._open_all_media)
        media_header.addWidget(media_title)
        media_header.addStretch()
        media_header.addWidget(self._media_see_all)
        root.addLayout(media_header)

        self._media_row = QHBoxLayout()
        self._media_row.setSpacing(10)
        root.addLayout(self._media_row)

        # Members (groups)
        self._members_block = QWidget()
        members_layout = QVBoxLayout(self._members_block)
        members_layout.setContentsMargins(0, 8, 0, 0)
        members_layout.setSpacing(10)

        members_header = QHBoxLayout()
        members_title = QLabel("Members")
        members_title.setObjectName("SectionTitle")
        self._members_see_all = _ClickLabel("See All")
        self._members_see_all.setObjectName("LinkAccent")
        self._members_see_all.setCursor(QCursor(Qt.PointingHandCursor))
        self._members_see_all.clicked.connect(self._open_all_members)
        members_header.addWidget(members_title)
        members_header.addStretch()
        members_header.addWidget(self._members_see_all)
        members_layout.addLayout(members_header)

        self._members_row = QHBoxLayout()
        self._members_row.setSpacing(8)
        members_layout.addLayout(self._members_row)
        root.addWidget(self._members_block)

        root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    @property
    def expanded_width(self) -> int:
        return DETAIL_WIDTH

    def show_conversation(self, conversation: Conversation) -> None:
        self._conversation = conversation
        self._avatar.set_identity(
            conversation.initials,
            conversation.accent,
            image_url=conversation.avatar_url,
        )
        if conversation.is_group:
            self._avatar.setToolTip("Change group photo")
            self._avatar.setCursor(Qt.PointingHandCursor)
            self._change_photo_btn.show()
        else:
            self._avatar.setToolTip("")
            self._avatar.setCursor(Qt.ArrowCursor)
            self._change_photo_btn.hide()

        self._name.setText(conversation.name)
        self._about.setText(conversation.about or "No bio yet.")

        if conversation.online:
            self._dot.show()
            self._status.setText("Online")
            self._status.setStyleSheet("")
        else:
            self._dot.hide()
            label = "Group" if conversation.is_group else "Offline"
            self._status.setText(label)
            self._status.setStyleSheet("color: #8B849C; font-size: 12px;")

        if conversation.is_group and conversation.my_role:
            role = "Admin" if conversation.my_role == "admin" else "Member"
            self._role_chip.setText(f"Your role · {role}")
            self._role_chip.show()
        else:
            self._role_chip.hide()

        self._add_btn.setVisible(conversation.is_group)
        self._leave_action.setVisible(conversation.is_group)
        self._delete_action.setVisible(not conversation.is_group)
        self._block_action.setVisible(not conversation.is_group)
        self._fill_media(conversation.media_urls[:3])
        self._fill_members(conversation.members[:4] if conversation.is_group else [])
        self._members_block.setVisible(conversation.is_group)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _fill_media(self, urls: list[str]) -> None:
        from payra.ui.widgets.dialogs import _NetworkImage

        self._clear_layout(self._media_row)
        if not urls:
            empty = QLabel("No media yet")
            empty.setObjectName("DetailAbout")
            self._media_row.addWidget(empty)
            self._media_row.addStretch()
            return
        for url in urls:
            self._media_row.addWidget(_NetworkImage(url, 68))
        self._media_row.addStretch()

    def _fill_members(self, members: list[ContactPerson]) -> None:
        self._clear_layout(self._members_row)
        for member in members:
            self._members_row.addWidget(
                Avatar(member.initials, member.accent, 40, image_url=member.avatar_url)
            )
        if members:
            more = QLabel(f"+{max(0, len(self._conversation.members) - len(members))}"
                          if self._conversation and len(self._conversation.members) > len(members)
                          else "")
            if more.text():
                more.setObjectName("MemberMoreChip")
                more.setAlignment(Qt.AlignCenter)
                more.setFixedSize(40, 40)
                self._members_row.addWidget(more)
        self._members_row.addStretch()

    def _open_all_media(self) -> None:
        if not self._conversation:
            return
        urls = self._conversation.media_urls or []
        MediaGalleryDialog(urls, self.window()).exec()

    def _open_all_members(self) -> None:
        if not self._conversation:
            return
        host = self.window() or self
        my_id = self._current_user_id()
        dialog = MembersListDialog(
            self._conversation.members,
            "Members",
            host,
            my_user_id=my_id,
            my_role=self._conversation.my_role,
        )
        if not dialog.exec():
            return
        pending = dialog.pending_action()
        if not pending:
            return
        action, person = pending
        if action == "leave":
            self._on_leave_group()
        elif action == "promote" and person is not None:
            self._set_member_role(person, "admin")
        elif action == "demote" and person is not None:
            self._set_member_role(person, "member")
        elif action == "remove" and person is not None:
            self._remove_member(person)

    def _current_user_id(self) -> str:
        try:
            from payra.models.demo_data import current_user

            return current_user().id
        except Exception:
            return ""

    def _on_change_group_photo(self) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        host = self.window() or self
        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.services import storage as storage_service
        from payra.ui.avatar_cache import avatar_cache
        from payra.ui.widgets.loading import run_busy

        path, _ = QFileDialog.getOpenFileName(
            host,
            "Choose group photo",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif *.bmp)",
        )
        if not path:
            return

        if not auth_service.supabase_ready():
            # Demo: store as file URL locally for this session.
            from PySide6.QtCore import QUrl

            url = QUrl.fromLocalFile(path).toString()
            self._conversation.avatar_url = url
            self._avatar.set_identity(
                self._conversation.initials,
                self._conversation.accent,
                image_url=url,
            )
            self.conversation_updated.emit(self._conversation)
            QMessageBox.information(host, "Group photo", "Group photo updated locally.")
            return

        cid = self._conversation.id

        def work():
            url = storage_service.upload_group_avatar(cid, path)
            return chat_service.set_group_avatar(cid, url)

        def ok(updated: Conversation) -> None:
            old = getattr(self._conversation, "avatar_url", None)
            self._conversation = updated
            avatar_cache().invalidate(old)
            avatar_cache().invalidate(updated.avatar_url)
            self.show_conversation(updated)
            self.conversation_updated.emit(updated)
            QMessageBox.information(host, "Group photo", "Group photo updated.")

        run_busy(
            host,
            "Uploading group photo…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(host, "Group photo", err),
        )

    def _set_member_role(self, person: ContactPerson, role: str) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        host = self.window() or self
        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.ui.widgets.loading import run_busy

        label = "admin" if role == "admin" else "member"
        reply = QMessageBox.question(
            host,
            "Change role",
            f"Make {person.name} a group {label}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        if not auth_service.supabase_ready():
            person.member_role = role
            person.role = "Admin" if role == "admin" else "Member"
            self._apply_members_refresh()
            self.conversation_updated.emit(self._conversation)
            return

        cid = self._conversation.id

        def work():
            return chat_service.set_member_role(cid, person.id, role)

        def ok(updated: Conversation) -> None:
            self._conversation = updated
            self.show_conversation(updated)
            self.conversation_updated.emit(updated)

        run_busy(
            host,
            "Updating role…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(host, "Role", err),
        )

    def _remove_member(self, person: ContactPerson) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        host = self.window() or self
        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.ui.widgets.loading import run_busy

        reply = QMessageBox.question(
            host,
            "Remove member",
            f"Remove {person.name} from “{self._conversation.name}”?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if not auth_service.supabase_ready():
            self._conversation.members = [
                m for m in self._conversation.members if m.id != person.id
            ]
            self._apply_members_refresh()
            self.conversation_updated.emit(self._conversation)
            return

        cid = self._conversation.id

        def work():
            return chat_service.remove_member(cid, person.id)

        def ok(updated: Conversation | None) -> None:
            if updated is None:
                self.left_group.emit(cid)
                self.close_requested.emit()
                return
            self._conversation = updated
            self.show_conversation(updated)
            self.conversation_updated.emit(updated)

        run_busy(
            host,
            "Removing member…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(host, "Remove member", err),
        )

    def _on_leave_group(self) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        host = self.window() or self
        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.ui.widgets.loading import run_busy

        reply = QMessageBox.question(
            host,
            "Leave group",
            f"Leave “{self._conversation.name}”?\n\n"
            "You will lose access until someone adds you again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        cid = self._conversation.id
        my_id = self._current_user_id()

        if not auth_service.supabase_ready():
            self.left_group.emit(cid)
            self.close_requested.emit()
            return

        def work():
            return chat_service.remove_member(cid, my_id)

        def ok(_result) -> None:
            self.left_group.emit(cid)
            self.close_requested.emit()

        run_busy(
            host,
            "Leaving group…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(host, "Leave group", err),
        )

    def _on_add_member(self) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        # Disable while loading to prevent double-tap races / nested busy scopes.
        self._add_btn.setEnabled(False)
        existing = {m.id for m in self._conversation.members}
        group_name = self._conversation.name
        host = self.window() or self

        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.ui.widgets.loading import run_busy

        def restore_btn() -> None:
            self._add_btn.setEnabled(True)

        def open_picker(candidates: list[ContactPerson]) -> None:
            restore_btn()
            if self._conversation is None or not self._conversation.is_group:
                return
            dialog = AddMemberDialog(
                candidates,
                host,
                group_name=group_name,
            )
            # Critical: do NOT open another modal from a signal during accept().
            # Read selection after exec() returns — avoids macOS Cocoa segfaults.
            accepted = dialog.exec()
            if not accepted:
                return
            people = dialog.selected_members()
            if not people:
                return
            self._confirm_and_add_members(host, people)

        if not auth_service.supabase_ready():
            open_picker([p for p in demo_directory() if p.id not in existing])
            return

        def work():
            return [p for p in chat_service.list_directory() if p.id not in existing]

        def on_dir_error(err: str) -> None:
            restore_btn()
            QMessageBox.warning(host, "Directory", err)

        run_busy(
            host,
            "Loading contacts…",
            work,
            on_success=lambda people: open_picker(people or []),
            on_error=on_dir_error,
        )

    def _confirm_and_add_members(
        self, host: QWidget, people: list[ContactPerson]
    ) -> None:
        if self._conversation is None or not people:
            return

        from payra.services import auth as auth_service
        from payra.services import chat as chat_service
        from payra.ui.widgets.loading import run_busy

        names = ", ".join(p.name for p in people[:3])
        if len(people) > 3:
            names += f" (+{len(people) - 3} more)"
        reply = QMessageBox.question(
            host,
            "Add members",
            f"Add {names} to “{self._conversation.name}”?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        if not auth_service.supabase_ready():
            known = {m.id for m in self._conversation.members}
            for person in people:
                if person.id not in known:
                    person.member_role = person.member_role or "member"
                    person.role = "Admin" if person.member_role == "admin" else "Member"
                    self._conversation.members.append(person)
                    known.add(person.id)
            self._apply_members_refresh()
            self.conversation_updated.emit(self._conversation)
            QMessageBox.information(
                host,
                "Members added",
                f"Added {len(people)} member(s) to {self._conversation.name}.",
            )
            return

        cid = self._conversation.id
        ids = [p.id for p in people]

        def work():
            return chat_service.add_members(cid, ids)

        def ok(updated: Conversation) -> None:
            self._conversation = updated
            self.show_conversation(updated)
            self.conversation_updated.emit(updated)
            QMessageBox.information(
                host,
                "Members added",
                f"Added {len(people)} member(s) to {updated.name}.",
            )

        run_busy(
            host,
            "Adding members…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(host, "Add members", err),
        )

    def _apply_members_refresh(self) -> None:
        if self._conversation is None:
            return
        count = len(self._conversation.members)
        if self._conversation.is_group and (
            not self._conversation.about or "member" in self._conversation.about.lower()
        ):
            self._conversation.about = f"{count} members"
            self._about.setText(self._conversation.about)
        self._fill_members(self._conversation.members[:4])

    def _on_star(self) -> None:
        self.star_requested.emit()

    def _on_delete(self) -> None:
        name = self._conversation.name if self._conversation else "chat"
        reply = QMessageBox.warning(
            self.window(),
            "Delete chat",
            f"Remove “{name}” from your chat list?\n\n"
            "This cannot be undone on this device.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.delete_contact_requested.emit()
            self.close_requested.emit()

    def _on_block(self) -> None:
        name = self._conversation.name if self._conversation else "contact"
        reply = QMessageBox.warning(
            self.window(),
            "Block contact",
            f"Block “{name}”?\n\n"
            "You won’t receive new messages from them in this app session.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.block_contact_requested.emit()
            self.close_requested.emit()
