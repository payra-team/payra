"""Main application shell — Supabase-backed when configured, else demo data."""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QWidget

from payra.models.demo_data import (
    ContactPerson,
    Conversation,
    Message,
    demo_conversations,
    demo_directory,
)
from payra.resources import load_app_icon
from payra.services import auth as auth_service
from payra.services import chat as chat_service
from payra.services import realtime as realtime_service
from payra.services import storage as storage_service
from payra.ui.effects import apply_card_shadow
from payra.ui.theme import DETAIL_WIDTH, NAV_COLLAPSED_WIDTH, NAV_WIDTH
from payra.ui.widgets.chat_list import ChatListPanel
from payra.ui.widgets.chat_pane import ChatPane
from payra.ui.widgets.detail_panel import DetailPanel
from payra.ui.widgets.dialogs import MyProfileDialog, NewChatDialog, NewGroupDialog
from payra.ui.widgets.image_compose import ImageComposeDialog
from payra.ui.widgets.loading import run_busy
from payra.ui.widgets.nav_sidebar import NavSidebar


class MainWindow(QMainWindow):
    logout_requested = Signal()
    _realtime_message = Signal(dict)
    _realtime_change = Signal(str, str, dict, dict)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Payra")
        self.setWindowIcon(load_app_icon())
        self.setMinimumSize(1180, 720)
        self.resize(1360, 860)

        self._live = auth_service.supabase_ready()
        self._conversations: dict[str, Conversation] = {}
        self._active_id: str | None = None
        self._nav_open = True
        self._detail_open = False
        self._section = "chats"
        self._opening_chat = False
        self._sending = False
        self._realtime_workers: list = []
        self._realtime_refresh_timer = QTimer(self)
        self._realtime_refresh_timer.setSingleShot(True)
        self._realtime_refresh_timer.setInterval(180)
        self._realtime_refresh_timer.timeout.connect(self._run_quiet_conversations_refresh)
        self._pending_active_reload = False

        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
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
        self._setup_nav_animation()
        self._setup_detail_animation()

        self.chat_list.conversation_selected.connect(self._open_conversation)
        self.chat_pane.send_requested.connect(self._on_send)
        self.chat_pane.attach_requested.connect(self._on_attach)
        self.chat_pane.profile_clicked.connect(self.toggle_detail_panel)
        self.chat_pane.star_requested.connect(self._on_star)
        self.chat_pane.load_older_requested.connect(self._load_older_messages)
        self.detail.close_requested.connect(self.close_detail_panel)
        self.detail.star_requested.connect(self._on_star)
        self.detail.delete_contact_requested.connect(self._on_delete_chat)
        self.detail.block_contact_requested.connect(self._on_block_chat)
        self.detail.conversation_updated.connect(self._on_detail_conversation_updated)
        self.detail.left_group.connect(self._on_left_group)
        self.nav.new_chat_clicked.connect(self._on_new_chat)
        self.nav.new_group_clicked.connect(self._on_new_group)
        self.nav.section_changed.connect(self._on_section)
        self.nav.you_clicked.connect(self._on_you_profile)
        self.nav.toggle_requested.connect(self.toggle_nav_panel)
        self._realtime_message.connect(self._on_realtime_message)
        self._realtime_change.connect(self._on_realtime_change)

        self._reload_conversations(select_first=True)

        if self._live:
            realtime_service.add_change_handler(self._enqueue_realtime_change)
            realtime_service.start_messages_listener()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._live:
            self._realtime_refresh_timer.stop()
            realtime_service.remove_change_handler(self._enqueue_realtime_change)
            realtime_service.stop_messages_listener()
        super().closeEvent(event)

    def _enqueue_realtime(self, record: dict) -> None:
        # Marshal onto Qt thread
        self._realtime_message.emit(record)

    def _enqueue_realtime_change(
        self, table: str, event_type: str, record: dict, old_record: dict
    ) -> None:
        # Marshal onto Qt thread
        self._realtime_change.emit(table, event_type, record, old_record)

    def _run_background(self, work, on_ok) -> None:
        from PySide6.QtCore import QThreadPool

        from payra.ui.widgets.loading import _Worker

        worker = _Worker(work)
        self._realtime_workers.append(worker)

        def _cleanup_and_ok(res) -> None:
            try:
                self._realtime_workers.remove(worker)
            except ValueError:
                pass
            on_ok(res)

        def _cleanup_err(_err) -> None:
            try:
                self._realtime_workers.remove(worker)
            except ValueError:
                pass

        worker.signals.finished.connect(_cleanup_and_ok)
        worker.signals.error.connect(_cleanup_err)
        QThreadPool.globalInstance().start(worker)

    def _move_conversation_to_top(self, cid: str) -> None:
        conv = self._conversations.pop(cid, None)
        if conv is not None:
            self._conversations = {cid: conv, **self._conversations}

    def _merge_conversation_list(self, items: list[Conversation]) -> None:
        merged: dict[str, Conversation] = {}
        for item in items:
            prev = self._conversations.get(item.id)
            if prev is not None and prev.messages:
                item.messages = list(prev.messages)
                item.has_more_messages = prev.has_more_messages
                if prev.media_urls:
                    seen_urls = set(item.media_urls)
                    for u in prev.media_urls:
                        if u not in seen_urls:
                            item.media_urls.append(u)
                            seen_urls.add(u)
            merged[item.id] = item
        self._conversations = merged

    def _schedule_quiet_refresh(self, *, reload_active: bool = False) -> None:
        if reload_active:
            self._pending_active_reload = True
        self._realtime_refresh_timer.start()

    def _run_quiet_conversations_refresh(self) -> None:
        if not self._live:
            return
        active_cid = self._active_id
        reload_active = self._pending_active_reload and bool(active_cid)
        self._pending_active_reload = False

        def work():
            items = chat_service.list_conversations()
            loaded = (
                chat_service.get_conversation(active_cid)
                if reload_active and active_cid
                else None
            )
            if loaded and active_cid:
                chat_service.mark_read(active_cid)
            return items, loaded

        def ok(result) -> None:
            items, loaded = result
            self._merge_conversation_list(items or [])
            self._apply_section(select_first=self._active_id is None)
            if self._active_id and self._active_id in self._conversations:
                self.chat_list.select(self._active_id)
            if loaded and self._active_id == loaded.id:
                self._conversations[loaded.id] = loaded
                self.chat_pane.show_conversation(loaded)
                self.detail.show_conversation(loaded)
            elif self._active_id and self._active_id in self._conversations:
                current = self._conversations[self._active_id]
                self.chat_pane.update_header(current)
                self.detail.show_conversation(current)

        self._run_background(work, ok)

    @Slot(dict)
    def _on_realtime_message(self, record: dict) -> None:
        self._on_realtime_change("messages", "INSERT", record, {})

    @Slot(str, str, dict, dict)
    def _on_realtime_change(
        self, table: str, event_type: str, record: dict, old_record: dict
    ) -> None:
        if not self._live:
            return

        if table == "messages":
            self._handle_realtime_message(event_type, record, old_record)
        elif table == "conversations":
            self._handle_realtime_conversation(event_type, record, old_record)
        elif table == "conversation_members":
            cid = str(record.get("conversation_id") or old_record.get("conversation_id") or "")
            reload_active = bool(cid and cid == self._active_id)
            self._schedule_quiet_refresh(reload_active=reload_active)

    def _handle_realtime_message(
        self, event_type: str, record: dict, old_record: dict
    ) -> None:
        cid = str(record.get("conversation_id") or old_record.get("conversation_id") or "")
        if not cid:
            return

        if event_type in ("UPDATE", "DELETE"):
            self._schedule_quiet_refresh(reload_active=(cid == self._active_id))
            return

        me = auth_service.current_session()
        me_id = me.id if me else ""
        sender_id = str(record.get("sender_id") or "")
        conv = self._conversations.get(cid)
        if conv is None:
            # New conversation we don't have locally yet — fetch full list.
            if sender_id and sender_id != me_id:
                from payra.ui.sound import play_message_sound

                play_message_sound()
            self._schedule_quiet_refresh(reload_active=False)
            return

        msg = chat_service.row_to_message(record, me_id)
        if msg.id and any(m.id == msg.id for m in conv.messages):
            return

        conv.preview = msg.text or conv.preview
        conv.time = msg.time or conv.time
        self._move_conversation_to_top(cid)

        is_active = self._active_id == cid
        if is_active:
            conv.unread = 0
            conv.messages.append(msg)
            if msg.image_path and msg.image_path not in conv.media_urls:
                conv.media_urls.append(msg.image_path)
            self.chat_pane.append_message(msg)
            if msg.image_path:
                self.detail.show_conversation(conv)
            if not msg.outgoing:
                self._run_background(lambda: chat_service.mark_read(cid), lambda _r: None)
        elif not msg.outgoing:
            conv.unread = (conv.unread or 0) + 1

        if not msg.outgoing:
            from payra.ui.sound import play_message_sound

            play_message_sound()

        self.chat_list.set_conversations(self._filtered())
        if self._active_id:
            self.chat_list.select(self._active_id)

    def _handle_realtime_conversation(
        self, event_type: str, record: dict, old_record: dict
    ) -> None:
        from payra.resources import normalize_avatar_url

        cid = str(record.get("id") or old_record.get("id") or "")
        if not cid:
            return

        if event_type == "DELETE":
            if cid in self._conversations:
                self._conversations.pop(cid, None)
                if self._active_id == cid:
                    self._active_id = None
                self._apply_section(select_first=True)
            return

        conv = self._conversations.get(cid)
        if conv is None:
            # New conversation created — refresh list to see if we're a member.
            self._schedule_quiet_refresh(reload_active=False)
            return

        if event_type == "UPDATE":
            if conv.is_group:
                if record.get("title"):
                    conv.name = str(record["title"])
                if record.get("about") is not None and str(record.get("about") or ""):
                    conv.about = str(record["about"])
                if "avatar_url" in record:
                    conv.avatar_url = normalize_avatar_url(record.get("avatar_url"))
                if record.get("accent"):
                    conv.accent = str(record["accent"])
            self._move_conversation_to_top(cid)
            self.chat_list.set_conversations(self._filtered())
            if self._active_id:
                self.chat_list.select(self._active_id)
            if self._active_id == cid:
                self.chat_pane.update_header(conv)
                self.detail.show_conversation(conv)
        else:
            self._schedule_quiet_refresh(reload_active=False)

    def _setup_nav_animation(self) -> None:
        self._nav_anim_min = QPropertyAnimation(self.nav, b"minimumWidth", self)
        self._nav_anim_max = QPropertyAnimation(self.nav, b"maximumWidth", self)
        for anim in (self._nav_anim_min, self._nav_anim_max):
            anim.setDuration(240)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._nav_anim = QParallelAnimationGroup(self)
        self._nav_anim.addAnimation(self._nav_anim_min)
        self._nav_anim.addAnimation(self._nav_anim_max)
        self._nav_anim.finished.connect(self._on_nav_anim_finished)

    def toggle_nav_panel(self) -> None:
        if self._nav_open:
            self.close_nav_panel()
        else:
            self.open_nav_panel()

    def open_nav_panel(self) -> None:
        if self._nav_open and self._nav_anim.state() != QAbstractAnimation.State.Running:
            return
        self._nav_open = True
        self._animate_nav(NAV_WIDTH)

    def close_nav_panel(self) -> None:
        if not self._nav_open and self.nav.maximumWidth() == NAV_COLLAPSED_WIDTH:
            return
        self._nav_open = False
        self.nav.set_collapsed(True)
        self._animate_nav(NAV_COLLAPSED_WIDTH)

    def _animate_nav(self, width: int) -> None:
        self._nav_anim.stop()
        current = self.nav.width()
        for anim in (self._nav_anim_min, self._nav_anim_max):
            anim.setStartValue(current)
            anim.setEndValue(width)
        self._nav_anim.start()

    def _on_nav_anim_finished(self) -> None:
        if self._nav_open:
            self.nav.set_collapsed(False)

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

    def _busy_host(self) -> QWidget:
        return self.centralWidget() or self

    def _reload_conversations(
        self, *, select_first: bool = False, async_load: bool = True
    ) -> None:
        if not self._live:
            items = demo_conversations()
            self._conversations = {c.id: c for c in items}
            self._apply_section(select_first=select_first)
            return

        if not async_load:
            try:
                items = chat_service.list_conversations()
            except Exception as exc:
                QMessageBox.warning(self, "Payra", f"Could not load chats:\n{exc}")
                items = []
            self._conversations = {c.id: c for c in items}
            self._apply_section(select_first=select_first)
            return

        self.chat_list.set_loading(True)

        def work():
            return chat_service.list_conversations()

        def ok(items) -> None:
            self._conversations = {c.id: c for c in (items or [])}
            self._apply_section(select_first=select_first)

        def fail(msg: str) -> None:
            self.chat_list.set_loading(False)
            QMessageBox.warning(self, "Payra", f"Could not load chats:\n{msg}")
            self._conversations = {}
            self._apply_section(select_first=True)

        run_busy(
            self._busy_host(),
            "Loading conversations…",
            work,
            on_success=ok,
            on_error=fail,
            wait_cursor=False,
        )

    def _refresh_list_preserving_selection(
        self, prefer: str | None = None, *, reopen: bool = True
    ) -> None:
        active = prefer or self._active_id

        def work():
            return chat_service.list_conversations() if self._live else demo_conversations()

        def ok(items) -> None:
            self._conversations = {c.id: c for c in (items or [])}
            self._apply_section(select_first=False)
            target = active if active in self._conversations else None
            if target:
                self.chat_list.select(target)
                if reopen:
                    self._open_conversation(target)

        def fail(msg: str) -> None:
            QMessageBox.warning(self, "Payra", f"Could not refresh chats:\n{msg}")

        if self._live:
            run_busy(
                self._busy_host(),
                "Refreshing…",
                work,
                on_success=ok,
                on_error=fail,
            )
        else:
            ok(demo_conversations())

    def _filtered(self) -> list[Conversation]:
        items = list(self._conversations.values())
        key = self._section
        if key == "groups":
            return [c for c in items if c.is_group]
        if key == "starred":
            return [
                c
                for c in items
                if getattr(c, "starred", False) or c.id in chat_service.starred_ids()
            ]
        if key == "ai":
            return []
        if key == "contacts":
            return items
        return items

    def _apply_section(self, *, select_first: bool) -> None:
        items = self._filtered()
        self.chat_list.set_conversations(items)
        if not items:
            self._active_id = None
            self.chat_pane.show_conversation(
                Conversation(
                    id="",
                    name="No conversations",
                    preview="",
                    time="",
                    about="Start a new chat to begin messaging.",
                    initials="PR",
                )
            )
            return
        target = self._active_id if self._active_id in {c.id for c in items} else items[0].id
        if select_first or self._active_id not in {c.id for c in items}:
            self.chat_list.select(target)
            self._open_conversation(target)

    def _open_conversation(self, conversation_id: str) -> None:
        if not conversation_id or self._opening_chat:
            return
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return
        self._active_id = conversation_id
        if not self._live:
            self.chat_pane.show_conversation(conversation)
            self.detail.show_conversation(conversation)
            return

        self._opening_chat = True
        self.chat_pane.set_loading(True, "Loading messages…")
        self.detail.show_conversation(conversation)
        cid = conversation_id
        fallback = conversation

        def work():
            loaded = chat_service.get_conversation(cid)
            if loaded:
                chat_service.mark_read(cid)
            return loaded

        def ok(loaded) -> None:
            self._opening_chat = False
            if loaded:
                loaded.unread = 0
                self._conversations[cid] = loaded
                self.chat_list.set_conversations(self._filtered())
                if self._active_id:
                    self.chat_list.select(self._active_id)
                if self._active_id == cid:
                    self.chat_pane.show_conversation(loaded)
                    self.detail.show_conversation(loaded)
            elif self._active_id == cid:
                self.chat_pane.show_conversation(fallback)
                self.detail.show_conversation(fallback)

        def fail(msg: str) -> None:
            self._opening_chat = False
            self.chat_pane.show_conversation(fallback)
            self.detail.show_conversation(fallback)
            QMessageBox.warning(self, "Payra", f"Could not open chat:\n{msg}")

        run_busy(
            self._busy_host(),
            "Opening chat…",
            work,
            on_success=ok,
            on_error=fail,
            wait_cursor=False,
        )

    def _load_older_messages(self) -> None:
        if not self._live or not self._active_id:
            self.chat_pane.prepend_messages([], False)
            return
        cid = self._active_id
        conversation = self._conversations.get(cid)
        if conversation is None or not conversation.messages:
            self.chat_pane.prepend_messages([], False)
            return
        before = conversation.messages[0].created_at
        if not before:
            self.chat_pane.prepend_messages([], False)
            return

        def work():
            return chat_service.load_older_messages(cid, before=before)

        def ok(result) -> None:
            older, has_more = result
            conv = self._conversations.get(cid)
            if conv is None or self._active_id != cid:
                return
            conv.messages = list(older) + list(conv.messages)
            conv.has_more_messages = has_more
            self.chat_pane.prepend_messages(older, has_more)

        def fail(_err: str) -> None:
            self.chat_pane.prepend_messages([], getattr(conversation, "has_more_messages", False))

        run_busy(
            self._busy_host(),
            "Loading earlier messages…",
            work,
            on_success=ok,
            on_error=fail,
            wait_cursor=False,
        )

    def _on_send(self, text: str) -> None:
        if not self._active_id or self._sending:
            return
        if self._live:
            cid = self._active_id
            self._sending = True
            self.chat_pane.set_sending(True)

            def work():
                return chat_service.send_message(cid, text)

            def ok(msg) -> None:
                self._sending = False
                self.chat_pane.set_sending(False)
                conversation = self._conversations.get(cid)
                if conversation is None:
                    return
                already = bool(msg.id and any(m.id == msg.id for m in conversation.messages))
                if not already:
                    conversation.messages.append(msg)
                    if self._active_id == cid:
                        self.chat_pane.append_message(msg)
                conversation.preview = msg.text
                conversation.time = msg.time or "Now"
                self._move_conversation_to_top(cid)
                self.chat_list.set_conversations(self._filtered())
                self.chat_list.select(cid)

            def fail(err: str) -> None:
                self._sending = False
                self.chat_pane.set_sending(False)
                QMessageBox.warning(self, "Send failed", err)

            run_busy(
                self._busy_host(),
                "Sending message…",
                work,
                on_success=ok,
                on_error=fail,
                wait_cursor=False,
            )
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
        if not self._live:
            QMessageBox.information(
                self,
                "Attach image",
                "Connect Supabase (.env) to upload images.",
            )
            return
        if not self._active_id or self._sending:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Attach image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if not path:
            return
        dialog = ImageComposeDialog(path, self)
        dialog.send_requested.connect(self._send_image_with_caption)
        dialog.exec()

    def _send_image_with_caption(self, path: str, caption: str) -> None:
        if not self._active_id or self._sending:
            return
        cid = self._active_id
        self._sending = True
        self.chat_pane.set_sending(True)

        def work():
            url = storage_service.upload_chat_image(path)
            msg = chat_service.send_message(cid, caption, image_path=url)
            return msg, url

        def ok(result) -> None:
            self._sending = False
            self.chat_pane.set_sending(False)
            msg, url = result
            conversation = self._conversations.get(cid)
            if conversation is None:
                return
            already = bool(msg.id and any(m.id == msg.id for m in conversation.messages))
            if not already:
                conversation.messages.append(msg)
                if self._active_id == cid:
                    self.chat_pane.append_message(msg)
            conversation.preview = msg.text
            conversation.time = msg.time or "Now"
            if url not in conversation.media_urls:
                conversation.media_urls.append(url)
            self._move_conversation_to_top(cid)
            self.chat_list.set_conversations(self._filtered())
            self.chat_list.select(cid)

        def fail(err: str) -> None:
            self._sending = False
            self.chat_pane.set_sending(False)
            QMessageBox.warning(self, "Upload failed", err)

        run_busy(
            self._busy_host(),
            "Uploading image…",
            work,
            on_success=ok,
            on_error=fail,
            wait_cursor=False,
        )

    def _on_star(self) -> None:
        if not self._active_id:
            return
        conv = self._conversations.get(self._active_id)
        name = conv.name if conv else "this chat"
        currently = bool(getattr(conv, "starred", False)) or (
            self._active_id in chat_service.starred_ids()
        )
        action = "Remove star from" if currently else "Star"
        reply = QMessageBox.question(
            self,
            "Star chat",
            f"{action} “{name}”?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if not self._live:
            if conv:
                setattr(conv, "starred", not currently)
            QMessageBox.information(self, "Starred", "Updated locally.")
            self._apply_section(select_first=False)
            return
        cid = self._active_id
        new_state = not currently

        def work():
            chat_service.set_starred(cid, new_state)
            return new_state

        def ok(starred: bool) -> None:
            c = self._conversations.get(cid)
            if c:
                setattr(c, "starred", starred)
            state = "starred" if starred else "unstarred"
            QMessageBox.information(self, "Starred", f"Chat {state}.")
            self._apply_section(select_first=False)

        run_busy(
            self._busy_host(),
            "Updating star…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(self, "Star failed", err),
            wait_cursor=False,
        )

    def _on_detail_conversation_updated(self, conversation) -> None:
        """Keep chat list / pane in sync after DetailPanel mutations (e.g. add members)."""
        if conversation is None or not getattr(conversation, "id", None):
            return
        existing = self._conversations.get(conversation.id)
        if existing and not conversation.messages and existing.messages:
            conversation.messages = list(existing.messages)
        self._conversations[conversation.id] = conversation
        if self._active_id == conversation.id:
            self.chat_pane.show_conversation(conversation)
        self._refresh_list_preserving_selection(prefer=conversation.id)

    def _on_left_group(self, conversation_id: str) -> None:
        if not conversation_id:
            return
        self._conversations.pop(conversation_id, None)
        if self._active_id == conversation_id:
            self._active_id = None
        self._apply_section(select_first=True)
        # Defer toast until after detail-panel close animation finishes.
        QTimer.singleShot(
            280,
            lambda: QMessageBox.information(self, "Left group", "You left the group."),
        )

    def _on_delete_chat(self) -> None:
        if not self._active_id:
            return
        cid = self._active_id
        self._conversations.pop(cid, None)
        self._active_id = None
        self._apply_section(select_first=True)
        QMessageBox.information(self, "Deleted", "Chat removed from your list.")

    def _on_block_chat(self) -> None:
        if not self._active_id:
            return
        cid = self._active_id
        self._conversations.pop(cid, None)
        self._active_id = None
        self._apply_section(select_first=True)
        QMessageBox.information(self, "Blocked", "Contact blocked for this session.")

    def _open_new_chat_dialog(self, people: list[ContactPerson]) -> None:
        dialog = NewChatDialog(people, self)
        dialog.chat_requested.connect(self._start_chat_with)
        dialog.exec()

    def _on_new_chat(self) -> None:
        if not self._live:
            self._open_new_chat_dialog(demo_directory())
            return

        def work():
            return chat_service.list_directory()

        def ok(people) -> None:
            # Defer past busy teardown so dialog.exec isn't nested in a crashy way.
            QTimer.singleShot(
                0, lambda: self._open_new_chat_dialog(people or [])
            )

        run_busy(
            self._busy_host(),
            "Loading contacts…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(self, "Directory", err),
            wait_cursor=False,
        )

    def _open_new_group_dialog(self, people: list[ContactPerson]) -> None:
        dialog = NewGroupDialog(people, self)
        dialog.group_requested.connect(self._create_group)
        dialog.exec()

    def _on_new_group(self) -> None:
        if not self._live:
            self._open_new_group_dialog(demo_directory())
            return

        def work():
            return chat_service.list_directory()

        def ok(people) -> None:
            QTimer.singleShot(
                0, lambda: self._open_new_group_dialog(people or [])
            )

        run_busy(
            self._busy_host(),
            "Loading contacts…",
            work,
            on_success=ok,
            on_error=lambda err: QMessageBox.warning(self, "Directory", err),
            wait_cursor=False,
        )

    def _create_group(self, title: str, people: list[ContactPerson]) -> None:
        # Defer past dialog teardown (group_requested fires from finished).
        QTimer.singleShot(0, lambda: self._create_group_now(title, people))

    def _create_group_now(self, title: str, people: list[ContactPerson]) -> None:
        if self._live:
            ids = [p.id for p in people]

            def work():
                return chat_service.create_group(title, ids)

            def ok(conversation) -> None:
                self._conversations[conversation.id] = conversation
                self._section = "groups"
                self.nav._select("groups")
                self._refresh_list_preserving_selection(prefer=conversation.id)

            run_busy(
                self._busy_host(),
                "Creating group…",
                work,
                on_success=ok,
                on_error=lambda err: QMessageBox.warning(self, "New group", err),
                wait_cursor=False,
            )
            return

        from payra.models.demo_data import ME_AVATAR, as_group_member, current_user

        me = current_user()
        member_people = [as_group_member(p) for p in people]
        me_member = ContactPerson(
            me.id,
            "You",
            me.initials or "YO",
            me.accent,
            me.avatar_url or ME_AVATAR,
            "Admin",
            member_role="admin",
        )
        members = [me_member] + [m for m in member_people if m.id != me.id]
        new_id = f"g-{len(self._conversations) + 1}"
        conversation = Conversation(
            id=new_id,
            name=title,
            preview="Group created",
            time="Now",
            is_group=True,
            about=f"{len(members)} members",
            initials="".join(p.initials[:1] for p in people[:2]) or "GR",
            members=members,
            messages=[],
            my_role="admin",
        )
        self._conversations[new_id] = conversation
        self._section = "groups"
        self.nav._select("groups")
        self._refresh_list_preserving_selection(prefer=new_id)

    def _start_chat_with(self, person: ContactPerson, first_message: str) -> None:
        # Always defer — New Chat dialog may still be finishing its event loop.
        QTimer.singleShot(
            0, lambda: self._start_chat_with_now(person, first_message)
        )

    def _start_chat_with_now(self, person: ContactPerson, first_message: str) -> None:
        if self._live:

            def work():
                return chat_service.start_direct(person.id, first_message)

            def ok(conversation) -> None:
                self._conversations[conversation.id] = conversation
                self._section = "chats"
                self._active_id = conversation.id
                self.chat_list.set_conversations(self._filtered())
                self.chat_list.select(conversation.id)
                self.chat_pane.show_conversation(conversation)
                self.detail.show_conversation(conversation)

            run_busy(
                self._busy_host(),
                "Starting chat…",
                work,
                on_success=ok,
                on_error=lambda err: QMessageBox.warning(self, "New chat", err),
                wait_cursor=False,
            )
            return

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
        dialog.profile_updated.connect(self.nav.refresh_you)
        dialog.exec()

    def _on_section(self, key: str) -> None:
        self._section = key
        if key == "ai":
            QMessageBox.information(
                self,
                "Payra AI",
                "AI assistant is Phase 3 — skipped for this release.",
            )
        self._apply_section(select_first=True)
        self.close_detail_panel()
