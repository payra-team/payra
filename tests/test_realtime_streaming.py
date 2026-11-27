"""Unit tests for Supabase Realtime streaming and MainWindow live updates."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from payra.models.demo_data import Conversation, Message  # noqa: E402
from payra.services import auth as auth_service  # noqa: E402
from payra.services import chat as chat_service  # noqa: E402
from payra.services import realtime as realtime_service  # noqa: E402
from payra.ui.theme_app import apply_app_theme  # noqa: E402
from payra.ui.windows.main_window import MainWindow  # noqa: E402

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    existing = QApplication.instance()
    if existing is not None:
        _APP = existing
        return existing
    _APP = QApplication(sys.argv)
    apply_app_theme(_APP)
    return _APP


class RealtimePayloadTests(unittest.TestCase):
    def tearDown(self) -> None:
        realtime_service._handlers.clear()
        realtime_service._change_handlers.clear()

    def test_extract_change_v2_payload(self) -> None:
        from realtime.types import RealtimePostgresChangesListenEvent

        payload = {
            "data": {
                "schema": "public",
                "table": "messages",
                "type": RealtimePostgresChangesListenEvent.Insert,
                "record": {"id": "m1", "conversation_id": "c1", "content": "hi"},
            },
            "ids": [1],
        }
        table, ev, rec, old = realtime_service._extract_change(payload)
        self.assertEqual(table, "messages")
        self.assertEqual(ev, "INSERT")
        self.assertEqual(rec["id"], "m1")
        self.assertEqual(old, {})

    def test_extract_change_object_payload(self) -> None:
        payload = SimpleNamespace(
            data={
                "table": "conversations",
                "type": "UPDATE",
                "record": {"id": "c1", "title": "Renamed"},
                "old_record": {"id": "c1", "title": "Old"},
            }
        )
        table, ev, rec, old = realtime_service._extract_change(payload)
        self.assertEqual(table, "conversations")
        self.assertEqual(ev, "UPDATE")
        self.assertEqual(rec["title"], "Renamed")
        self.assertEqual(old["title"], "Old")

    def test_dispatch_notifies_message_and_change_handlers(self) -> None:
        msg_events: list[dict] = []
        chg_events: list[tuple] = []
        realtime_service.add_handler(msg_events.append)
        realtime_service.add_change_handler(lambda t, e, r, o: chg_events.append((t, e, r, o)))

        realtime_service._dispatch(
            {
                "data": {
                    "table": "messages",
                    "type": "INSERT",
                    "record": {"id": "m2", "conversation_id": "c1", "content": "yo"},
                }
            }
        )
        realtime_service._dispatch(
            {
                "data": {
                    "table": "conversations",
                    "type": "UPDATE",
                    "record": {"id": "c1", "title": "Squad"},
                }
            }
        )

        self.assertEqual(len(msg_events), 1)
        self.assertEqual(msg_events[0]["id"], "m2")
        self.assertEqual(len(chg_events), 2)
        self.assertEqual(chg_events[0][0], "messages")
        self.assertEqual(chg_events[1][0], "conversations")


class FormatTimeTests(unittest.TestCase):
    def test_fmt_time_today_not_raw_iso(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        formatted = chat_service._fmt_time(now_iso)
        self.assertTrue("AM" in formatted or "PM" in formatted, formatted)

    def test_fmt_time_older_date(self) -> None:
        formatted = chat_service._fmt_time("2025-01-05T10:15:00+00:00")
        self.assertIn("Jan", formatted)


class MainWindowRealtimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def _make_window(self) -> MainWindow:
        orig_ready = auth_service.supabase_ready
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        try:
            win = MainWindow()
        finally:
            auth_service.supabase_ready = orig_ready  # type: ignore[assignment]
        win._live = True
        return win

    def test_realtime_message_updates_active_thread_and_list_order(self) -> None:
        win = self._make_window()
        orig_session = auth_service.current_session
        orig_mark = chat_service.mark_read
        auth_service.current_session = lambda: SimpleNamespace(id="me-id")  # type: ignore[assignment]
        chat_service.mark_read = lambda _cid: None  # type: ignore[assignment]
        try:
            c1 = Conversation(id="c1", name="Alpha", preview="Old", time="10:00 AM", messages=[])
            c2 = Conversation(id="c2", name="Beta", preview="Hey", time="10:05 AM", messages=[])
            win._conversations = {"c1": c1, "c2": c2}
            win._active_id = "c1"
            win.chat_list.set_conversations([c1, c2])
            win.chat_pane.show_conversation(c1)
            self.assertIsNotNone(win.chat_pane._empty)

            now_iso = datetime.now(timezone.utc).isoformat()
            rec = {
                "id": "msg-1",
                "conversation_id": "c1",
                "sender_id": "other-id",
                "content": "Live hello!",
                "created_at": now_iso,
            }
            win._on_realtime_change("messages", "INSERT", rec, {})

            # Duplicate event with same ID must not add a second message
            win._on_realtime_change("messages", "INSERT", rec, {})

            self.assertEqual(len(c1.messages), 1)
            self.assertEqual(c1.messages[0].text, "Live hello!")
            self.assertEqual(c1.preview, "Live hello!")
            self.assertIsNone(win.chat_pane._empty)

            # Inactive chat message increments unread and moves c2 to top
            rec2 = {
                "id": "msg-2",
                "conversation_id": "c2",
                "sender_id": "other-id",
                "content": "Ping in Beta",
                "created_at": now_iso,
            }
            win._on_realtime_change("messages", "INSERT", rec2, {})
            self.assertEqual(c2.unread, 1)
            self.assertEqual(list(win._conversations.keys())[0], "c2")
        finally:
            auth_service.current_session = orig_session  # type: ignore[assignment]
            chat_service.mark_read = orig_mark  # type: ignore[assignment]
            win._live = False
            win.close()

    def test_realtime_conversation_update_preserves_messages(self) -> None:
        win = self._make_window()
        try:
            m = Message(id="m1", text="Keep me", outgoing=False, time="11:00 AM")
            grp = Conversation(
                id="g1",
                name="Old Title",
                preview="Keep me",
                time="11:00 AM",
                is_group=True,
                messages=[m],
            )
            win._conversations = {"g1": grp}
            win._active_id = "g1"
            win.chat_list.set_conversations([grp])
            win.chat_pane.show_conversation(grp)

            win._on_realtime_change(
                "conversations",
                "UPDATE",
                {"id": "g1", "title": "New Group Title"},
                {},
            )

            self.assertEqual(grp.name, "New Group Title")
            self.assertEqual(win.chat_pane._name.text(), "New Group Title")
            self.assertEqual(len(grp.messages), 1)
            self.assertEqual(grp.messages[0].text, "Keep me")
        finally:
            win._live = False
            win.close()


if __name__ == "__main__":
    unittest.main()
