"""Main application shell — separate floating cards + slide-in profile."""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QWidget

from payra.models.demo_data import (
    ContactPerson,
    Conversation,
    Message,
    demo_conversations,
    demo_directory,
)
from payra.resources import load_app_icon
from payra.ui.effects import apply_card_shadow
from payra.ui.theme import DETAIL_WIDTH
from payra.ui.widgets.chat_list import ChatListPanel
from payra.ui.widgets.chat_pane import ChatPane
from payra.ui.widgets.detail_panel import DetailPanel
from payra.ui.widgets.dialogs import MyProfileDialog, NewChatDialog
from payra.ui.widgets.nav_sidebar import NavSidebar


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Payra")
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(1180, 720)
        self.resize(1360, 860)

        self._conversations: dict[str, Conversation] = {
            c.id: c for c in demo_conversations()
        }
        self._active_id: str | None = None
        self._detail_open = False

        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
        # Gaps between cards so each panel reads as a separate floating card
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        self.nav = NavSidebar()
        self.chat_list = ChatListPanel()
        self.chat_pane = ChatPane()
        self.detail = DetailPanel()

        for card in (self.nav, self.chat_list, self.chat_pane):
            apply_card_shadow(card)

        self._detail_shadow = apply_card_shadow(self.detail)
        self._detail_shadow.setEnabled(False)

        layout.addWidget(self.nav)
        layout.addWidget(self.chat_list)
        layout.addWidget(self.chat_pane, stretch=1)
        layout.addWidget(self.detail)

        self.setCentralWidget(root)
        self._setup_detail_animation()

        self.chat_list.set_conversations(list(self._conversations.values()))
        self.chat_list.conversation_selected.connect(self._open_conversation)
        self.chat_pane.send_requested.connect(self._on_send)
        self.chat_pane.attach_requested.connect(self._on_attach)
        self.chat_pane.profile_clicked.connect(self.toggle_detail_panel)
        self.chat_pane.star_requested.connect(self._on_star)
        self.detail.close_requested.connect(self.close_detail_panel)
        self.nav.new_chat_clicked.connect(self._on_new_chat)
        self.nav.section_changed.connect(self._on_section)
        self.nav.you_clicked.connect(self._on_you_profile)

        first = next(iter(self._conversations))
        self.chat_list.select(first)
        self._open_conversation(first)

    def _setup_detail_animation(self) -> None:
        self._anim_min = QPropertyAnimation(self.detail, b"minimumWidth", self)
        self._anim_max = QPropertyAnimation(self.detail, b"maximumWidth", self)
        for anim in (self._anim_min, self._anim_max):
            anim.setDuration(260)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._detail_anim = QParallelAnimationGroup(self)
        self._detail_anim.addAnimation(self._anim_min)
        self._detail_anim.addAnimation(self._anim_max)
        self._detail_anim.finished.connect(self._on_detail_anim_finished)

    def toggle_detail_panel(self) -> None:
        if self._detail_open:
            self.close_detail_panel()
        else:
            self.open_detail_panel()

    def open_detail_panel(self) -> None:
        if self._detail_open and self._detail_anim.state() != QAbstractAnimation.State.Running:
            return
        self._detail_open = True
        self._detail_shadow.setEnabled(True)
        self._animate_detail(DETAIL_WIDTH)

    def close_detail_panel(self) -> None:
        if not self._detail_open and self.detail.maximumWidth() == 0:
            return
        self._detail_open = False
        self._animate_detail(0)

    def _animate_detail(self, width: int) -> None:
        self._detail_anim.stop()
        current = self.detail.width()
        for anim in (self._anim_min, self._anim_max):
            anim.setStartValue(current)
            anim.setEndValue(width)
        self._detail_anim.start()

    def _on_detail_anim_finished(self) -> None:
        if not self._detail_open:
            self._detail_shadow.setEnabled(False)

    def _open_conversation(self, conversation_id: str) -> None:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return
        self._active_id = conversation_id
        self.chat_pane.show_conversation(conversation)
        self.detail.show_conversation(conversation)

    def _on_send(self, text: str) -> None:
        if not self._active_id:
            return
        conversation = self._conversations[self._active_id]
        conversation.messages.append(
            Message(text=text, outgoing=True, time="Now", seen=False)
        )
        conversation.preview = text
        conversation.time = "Now"
        self.chat_pane.append_outgoing(text)
        self.chat_list.set_conversations(list(self._conversations.values()))
        self.chat_list.select(self._active_id)

    def _on_attach(self) -> None:
        QMessageBox.information(
            self,
            "Attach image",
            "Image attach will connect to Supabase Storage in the next phase.",
        )

    def _on_star(self) -> None:
        QMessageBox.information(
            self,
            "Starred",
            "This chat will appear under Starred once Supabase is connected.",
        )

    def _on_new_chat(self) -> None:
        dialog = NewChatDialog(demo_directory(), self)
        dialog.chat_requested.connect(self._start_chat_with)
        dialog.exec()

    def _start_chat_with(self, person: ContactPerson, first_message: str) -> None:
        # Reuse existing 1:1 chat if present
        for conv in self._conversations.values():
            if not conv.is_group and conv.name == person.name:
                self.chat_list.set_conversations(list(self._conversations.values()))
                self.chat_list.select(conv.id)
                self._open_conversation(conv.id)
                if first_message:
                    self._on_send(first_message)
                return

        new_id = f"c-{person.id}"
        messages: list[Message] = []
        preview = "Start of conversation"
        if first_message:
            messages.append(
                Message(text=first_message, outgoing=True, time="Now", seen=False)
            )
            preview = first_message

        conversation = Conversation(
            id=new_id,
            name=person.name,
            preview=preview,
            time="Now",
            online=True,
            about=person.role,
            initials=person.initials,
            accent=person.accent,
            avatar_url=person.avatar_url,
            messages=messages,
            media_urls=[],
        )
        self._conversations[new_id] = conversation
        self.chat_list.set_conversations(list(self._conversations.values()))
        self.chat_list.select(new_id)
        self._open_conversation(new_id)

    def _on_you_profile(self) -> None:
        dialog = MyProfileDialog(parent=self)
        dialog.logout_requested.connect(self.logout_requested.emit)
        dialog.exec()

    def _on_section(self, key: str) -> None:
        if key == "groups":
            items = [c for c in self._conversations.values() if c.is_group]
        elif key == "ai":
            # Placeholder until AI phase — keep list empty-ish friendly
            items = list(self._conversations.values())[:1]
        elif key == "starred":
            items = [c for c in self._conversations.values() if c.unread > 0]
        else:
            items = list(self._conversations.values())
        self.chat_list.set_conversations(items)
        if items:
            self.chat_list.select(items[0].id)
            self._open_conversation(items[0].id)
        self.close_detail_panel()
