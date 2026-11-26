"""Production hardening tests for group roles, dialogs, and RPC errors."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication, QDialog, QPushButton  # noqa: E402

from payra.models.demo_data import (  # noqa: E402
    ContactPerson,
    Conversation,
    as_group_member,
    demo_conversations,
    demo_directory,
)
from payra.services import chat as chat_service  # noqa: E402
from payra.ui.theme_app import apply_app_theme  # noqa: E402
from payra.ui.widgets.dialogs import MembersListDialog, NewGroupDialog  # noqa: E402


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


class RpcErrorMessageTests(unittest.TestCase):
    def test_last_admin_message(self) -> None:
        msg = chat_service._rpc_error_message(
            Exception("{'message': 'Cannot remove the last admin', 'code': 'P0001'}")
        )
        self.assertIn("Promote another admin", msg)

    def test_only_admins_roles(self) -> None:
        msg = chat_service._rpc_error_message(
            Exception("Only group admins can change roles")
        )
        self.assertIn("Only group admins", msg)

    def test_passthrough_unknown(self) -> None:
        msg = chat_service._rpc_error_message(Exception("weird failure xyz"))
        self.assertEqual(msg, "weird failure xyz")


class SoleAdminHelperTests(unittest.TestCase):
    def test_sole_admin_true(self) -> None:
        people = demo_directory()
        conv = Conversation(
            id="g1",
            name="Solo",
            preview="",
            time="Now",
            is_group=True,
            my_role="admin",
            members=[
                ContactPerson("me", "You", "YO", member_role="admin", role="Admin"),
                as_group_member(people[0]),
            ],
        )
        self.assertTrue(chat_service.is_sole_admin(conv, "me"))

    def test_sole_admin_false_with_two(self) -> None:
        group = next(c for c in demo_conversations() if c.id == "2")
        self.assertFalse(chat_service.is_sole_admin(group, "me"))


class NewGroupDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_accept_queues_pending_without_immediate_emit(self) -> None:
        people = demo_directory()[:3]
        dialog = NewGroupDialog(people)
        emitted: list[tuple] = []
        dialog.group_requested.connect(lambda t, p: emitted.append((t, p)))

        dialog.title_input.setText("SDP Team")
        dialog._checks[people[0].id].setChecked(True)
        dialog._accept()
        # Signal should fire from finished, not mid-accept. Force finished delivery.
        self.assertEqual(dialog.result(), QDialog.Accepted)
        dialog._emit_pending(QDialog.DialogCode.Accepted)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0], "SDP Team")
        self.assertEqual(emitted[0][1][0].id, people[0].id)
        dialog.close()

    def test_reject_validation(self) -> None:
        dialog = NewGroupDialog(demo_directory()[:2])
        dialog.title_input.setText("A")
        dialog._accept()
        self.assertFalse(dialog.error.isHidden())
        dialog.close()


class MembersSoleAdminLeaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_sole_admin_leave_disabled(self) -> None:
        people = demo_directory()
        members = [
            ContactPerson("me", "You", "YO", member_role="admin", role="Admin"),
            as_group_member(people[0]),
        ]
        dialog = MembersListDialog(members, my_user_id="me", my_role="admin")
        leave_btns = [
            b for b in dialog.findChildren(QPushButton) if "Leave" in (b.text() or "")
        ]
        self.assertEqual(len(leave_btns), 1)
        self.assertFalse(leave_btns[0].isEnabled())
        dialog.close()

    def test_multi_admin_leave_enabled(self) -> None:
        group = next(c for c in demo_conversations() if c.id == "2")
        dialog = MembersListDialog(
            group.members, my_user_id="me", my_role="admin"
        )
        leave_btns = [
            b for b in dialog.findChildren(QPushButton) if "Leave" in (b.text() or "")
        ]
        self.assertEqual(len(leave_btns), 1)
        self.assertTrue(leave_btns[0].isEnabled())
        dialog.close()


class AddMembersReturnContractTests(unittest.TestCase):
    def test_add_members_annotated_as_tuple(self) -> None:
        from typing import get_type_hints

        hints = get_type_hints(chat_service.add_members)
        # tuple[Conversation, int]
        self.assertIn("tuple", str(hints.get("return")).lower())


if __name__ == "__main__":
    unittest.main()
