"""Right-hand profile details — media, members, white-card actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
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
        self._avatar = Avatar("?", size=96)
        avatar_wrap.addWidget(self._avatar)
        avatar_wrap.addStretch()
        root.addLayout(avatar_wrap)

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
        delete_action = QAction("🗑️   Delete contact", self)
        block_action = QAction("🚫   Block contact", self)
        delete_action.triggered.connect(self._on_delete)
        block_action.triggered.connect(self._on_block)
        self._more_menu.addAction(delete_action)
        self._more_menu.addAction(block_action)
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

        self._add_btn.setVisible(conversation.is_group)
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
        MembersListDialog(self._conversation.members, "Members", self.window()).exec()

    def _on_add_member(self) -> None:
        if not self._conversation or not self._conversation.is_group:
            return
        existing = {m.id for m in self._conversation.members}
        candidates = [p for p in demo_directory() if p.id not in existing]
        dialog = AddMemberDialog(candidates, self.window())

        def on_selected(people: list[ContactPerson]) -> None:
            assert self._conversation is not None
            self._conversation.members.extend(people)
            self._fill_members(self._conversation.members[:4])
            QMessageBox.information(
                self.window(),
                "Members added",
                f"Added {len(people)} member(s) to {self._conversation.name}.",
            )

        dialog.members_selected.connect(on_selected)
        dialog.exec()

    def _on_star(self) -> None:
        QMessageBox.information(
            self.window(),
            "Starred",
            "Chat starred (demo). Will sync with Supabase later.",
        )

    def _on_delete(self) -> None:
        name = self._conversation.name if self._conversation else "contact"
        reply = QMessageBox.question(
            self.window(),
            "Delete contact",
            f"Delete {name}? (demo only)",
        )
        if reply == QMessageBox.Yes:
            self.delete_contact_requested.emit()
            self.close_requested.emit()

    def _on_block(self) -> None:
        name = self._conversation.name if self._conversation else "contact"
        reply = QMessageBox.warning(
            self.window(),
            "Block contact",
            f"Block {name}? (demo only)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.block_contact_requested.emit()
            self.close_requested.emit()
