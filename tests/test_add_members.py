"""Offscreen tests for Add Member dialog + DetailPanel demo flow."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Headless Qt before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from payra.models.demo_data import ContactPerson, Conversation, demo_conversations, demo_directory  # noqa: E402
from payra.ui.theme_app import apply_app_theme  # noqa: E402
from payra.ui.widgets.detail_panel import DetailPanel  # noqa: E402
from payra.ui.widgets.dialogs import AddMemberDialog, MembersListDialog  # noqa: E402


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


def _people(*ids: str) -> list[ContactPerson]:
    directory = {p.id: p for p in demo_directory()}
    return [directory[i] for i in ids]


class AddMemberDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_empty_candidates_shows_and_rejects_ok(self) -> None:
        dialog = AddMemberDialog([], group_name="Design Team")
        self.assertEqual(dialog.selected_members(), [])
        dialog._accept()
        self.assertEqual(dialog.result(), QDialog.Rejected)
        dialog.close()

    def test_accept_requires_selection(self) -> None:
        people = _people("u3", "u5")
        dialog = AddMemberDialog(people, group_name="Project Group")
        dialog._accept()
        self.assertFalse(dialog.error.isHidden())
        self.assertIn("at least one", dialog.error.text().lower())
        self.assertEqual(dialog.selected_members(), [])
        self.assertNotEqual(dialog.result(), QDialog.Accepted)
        dialog.close()

    def test_accept_with_checked_members(self) -> None:
        people = _people("u3", "u5", "u8")
        dialog = AddMemberDialog(people, group_name="Project Group")
        dialog._checks["u3"].setChecked(True)
        dialog._checks["u8"].setChecked(True)
        emitted: list[list[ContactPerson]] = []
        dialog.members_selected.connect(emitted.append)
        dialog._accept()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        selected = dialog.selected_members()
        self.assertEqual([p.id for p in selected], ["u3", "u8"])
        # Production path: no emit during accept (read selected_members after exec).
        self.assertEqual(len(emitted), 0)
        dialog.close()

    def test_search_filters_by_username_and_email(self) -> None:
        people = _people("u3", "u5", "u8")
        dialog = AddMemberDialog(people)

        def row_hidden(pid: str) -> bool:
            return dialog._checks[pid].parentWidget().isHidden()

        dialog._filter("omark")
        self.assertTrue(row_hidden("u3"))
        self.assertFalse(row_hidden("u5"))
        self.assertTrue(row_hidden("u8"))

        dialog._filter("@noraali")
        self.assertTrue(row_hidden("u3"))
        self.assertTrue(row_hidden("u5"))
        self.assertFalse(row_hidden("u8"))
        dialog.close()

    def test_selection_count_label(self) -> None:
        people = _people("u3", "u5")
        dialog = AddMemberDialog(people)
        self.assertIn("at least one", dialog._count.text().lower())
        dialog._checks["u3"].setChecked(True)
        self.assertIn("1 person", dialog._count.text().lower())
        dialog._checks["u5"].setChecked(True)
        self.assertIn("2 people", dialog._count.text().lower())
        dialog.close()


class DetailPanelAddMembersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_add_button_only_for_groups(self) -> None:
        panel = DetailPanel()
        dm = next(c for c in demo_conversations() if not c.is_group)
        group = next(c for c in demo_conversations() if c.is_group)

        panel.show_conversation(dm)
        self.assertTrue(panel._add_btn.isHidden())

        panel.show_conversation(group)
        self.assertFalse(panel._add_btn.isHidden())
        panel.close()

    def test_demo_confirm_and_add_updates_members(self) -> None:
        panel = DetailPanel()
        group = next(c for c in demo_conversations() if c.id == "2")
        before = len(group.members)
        panel.show_conversation(group)

        updates: list[Conversation] = []
        panel.conversation_updated.connect(updates.append)

        from PySide6.QtWidgets import QMessageBox
        from payra.services import auth as auth_service

        original_q = QMessageBox.question
        original_i = QMessageBox.information
        original_ready = auth_service.supabase_ready
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)  # type: ignore[assignment]
        QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)  # type: ignore[assignment]
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        try:
            newbie = _people("u8")[0]
            self.assertTrue(all(m.id != newbie.id for m in group.members))
            panel._confirm_and_add_members(panel, [newbie])
        finally:
            QMessageBox.question = original_q  # type: ignore[assignment]
            QMessageBox.information = original_i  # type: ignore[assignment]
            auth_service.supabase_ready = original_ready  # type: ignore[assignment]

        self.assertEqual(len(group.members), before + 1)
        self.assertTrue(any(m.id == "u8" for m in group.members))
        self.assertEqual(len(updates), 1)
        self.assertIn("members", (panel._about.text() or "").lower())
        panel.close()

    def test_demo_add_skips_duplicates(self) -> None:
        panel = DetailPanel()
        group = next(c for c in demo_conversations() if c.id == "4")
        existing = group.members[0]
        before = len(group.members)
        panel.show_conversation(group)

        from PySide6.QtWidgets import QMessageBox
        from payra.services import auth as auth_service

        original_q = QMessageBox.question
        original_i = QMessageBox.information
        original_ready = auth_service.supabase_ready
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)  # type: ignore[assignment]
        QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)  # type: ignore[assignment]
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        try:
            panel._confirm_and_add_members(panel, [existing])
        finally:
            QMessageBox.question = original_q  # type: ignore[assignment]
            QMessageBox.information = original_i  # type: ignore[assignment]
            auth_service.supabase_ready = original_ready  # type: ignore[assignment]

        self.assertEqual(len(group.members), before)
        panel.close()

    def test_group_shows_role_and_photo_controls(self) -> None:
        panel = DetailPanel()
        group = next(c for c in demo_conversations() if c.id == "2")
        dm = next(c for c in demo_conversations() if not c.is_group)

        panel.show_conversation(group)
        self.assertFalse(panel._change_photo_btn.isHidden())
        self.assertFalse(panel._role_chip.isHidden())
        self.assertIn("admin", panel._role_chip.text().lower())
        self.assertTrue(panel._leave_action.isVisible())

        panel.show_conversation(dm)
        self.assertTrue(panel._change_photo_btn.isHidden())
        self.assertTrue(panel._role_chip.isHidden())
        panel.close()

    def test_demo_promote_member_updates_role(self) -> None:
        panel = DetailPanel()
        group = next(c for c in demo_conversations() if c.id == "2")
        panel.show_conversation(group)
        target = next(m for m in group.members if m.member_role == "member")

        from PySide6.QtWidgets import QMessageBox
        from payra.services import auth as auth_service

        original_q = QMessageBox.question
        original_ready = auth_service.supabase_ready
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)  # type: ignore[assignment]
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        try:
            panel._set_member_role(target, "admin")
        finally:
            QMessageBox.question = original_q  # type: ignore[assignment]
            auth_service.supabase_ready = original_ready  # type: ignore[assignment]

        self.assertEqual(target.member_role, "admin")
        self.assertEqual(target.role, "Admin")
        panel.close()


class MembersListDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_admin_queues_promote_action(self) -> None:
        group = next(c for c in demo_conversations() if c.id == "2")
        member = next(m for m in group.members if m.member_role == "member")
        dialog = MembersListDialog(
            group.members,
            my_user_id="me",
            my_role="admin",
        )
        dialog._queue("promote", member)
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.pending_action(), ("promote", member))
        dialog.close()

    def test_non_admin_has_no_manage_menus(self) -> None:
        group = next(c for c in demo_conversations() if c.id == "2")
        dialog = MembersListDialog(
            group.members,
            my_user_id="me",
            my_role="member",
        )
        from PySide6.QtWidgets import QToolButton

        # Non-admins should not get the ⋮ manage menus.
        self.assertEqual(len(dialog.findChildren(QToolButton)), 0)
        dialog.close()


class AddMembersServiceContractTests(unittest.TestCase):
    """Pure contract checks that don't need a live Supabase session."""

    def test_add_members_function_exists_and_documents_return(self) -> None:
        from payra.services import chat as chat_service
        import inspect
        from typing import get_args, get_origin, get_type_hints

        sig = inspect.signature(chat_service.add_members)
        self.assertIn("conversation_id", sig.parameters)
        self.assertIn("user_ids", sig.parameters)
        hints = get_type_hints(chat_service.add_members)
        ret = hints.get("return")
        self.assertIs(get_origin(ret), tuple)
        self.assertEqual(get_args(ret), (Conversation, int))

    def test_role_and_avatar_apis_exist(self) -> None:
        from payra.services import chat as chat_service
        from payra.services import storage as storage_service

        self.assertTrue(callable(chat_service.set_member_role))
        self.assertTrue(callable(chat_service.remove_member))
        self.assertTrue(callable(chat_service.set_group_avatar))
        self.assertTrue(callable(storage_service.upload_group_avatar))


if __name__ == "__main__":
    unittest.main()
