"""Offscreen tests for Shared Media viewer, collapsible nav, and responsive chat bubbles."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from payra.models.demo_data import Conversation, Message  # noqa: E402
from payra.services import auth as auth_service  # noqa: E402
from payra.ui.theme import NAV_COLLAPSED_WIDTH, NAV_WIDTH  # noqa: E402
from payra.ui.theme_app import apply_app_theme  # noqa: E402
from payra.ui.widgets.chat_pane import ChatPane, MessageBubble  # noqa: E402
from payra.ui.widgets.detail_panel import DetailPanel  # noqa: E402
from payra.ui.widgets.dialogs import MediaGalleryDialog, RenameGroupDialog, _NetworkImage  # noqa: E402
from payra.ui.widgets.image_viewer import ImageViewerDialog  # noqa: E402
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


class MediaViewerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_network_image_click_opens_viewer_in_gallery_and_detail(self) -> None:
        opened: list[str] = []
        orig_exec = ImageViewerDialog.exec

        def fake_exec(dlg) -> int:
            opened.append(dlg._url)
            return 0

        ImageViewerDialog.exec = fake_exec  # type: ignore[assignment]
        try:
            gallery = MediaGalleryDialog(["https://example.com/a.png"])
            tiles = gallery.findChildren(_NetworkImage)
            self.assertEqual(len(tiles), 1)
            ev = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPoint(10, 10),
                QPoint(10, 10),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier,
            )
            tiles[0].mousePressEvent(ev)
            gallery.close()

            panel = DetailPanel()
            panel.show_conversation(
                Conversation(
                    id="c1",
                    name="Test",
                    preview="",
                    time="Now",
                    media_urls=["https://example.com/b.png"],
                )
            )
            dtiles = panel.findChildren(_NetworkImage)
            self.assertEqual(len(dtiles), 1)
            dtiles[0].mousePressEvent(ev)
            panel.close()
        finally:
            ImageViewerDialog.exec = orig_exec  # type: ignore[assignment]

        self.assertEqual(
            opened, ["https://example.com/a.png", "https://example.com/b.png"]
        )


class ResponsiveLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_chat_pane_bubbles_and_images_fit_narrow_viewport(self) -> None:
        pane = ChatPane()
        pane.resize(260, 620)
        pane.show()
        conv = Conversation(
            id="c1",
            name="Rimi",
            preview="valo",
            time="6:42 PM",
            messages=[
                Message("outgoing short text", True, "6:42 PM"),
                Message("📷 Image", False, "6:41 PM", image_path="https://example.com/big.png"),
            ],
        )
        pane.show_conversation(conv)
        _app().processEvents()

        # Simulate large photo arriving on the image bubble
        bubbles = pane.findChildren(MessageBubble)
        self.assertEqual(len(bubbles), 2)
        big = QPixmap(800, 600)
        big.fill(Qt.blue)
        bubbles[1]._image.set_photo(big)
        pane._reflow_bubbles()
        _app().processEvents()

        vp_w = pane._scroll.viewport().width()
        self.assertLessEqual(bubbles[0]._card.maximumWidth(), vp_w)
        self.assertLessEqual(bubbles[1]._image.width(), vp_w)
        pane.close()

    def test_main_window_nav_toggle_opens_and_closes(self) -> None:
        orig_ready = auth_service.supabase_ready
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        try:
            win = MainWindow()
        finally:
            auth_service.supabase_ready = orig_ready  # type: ignore[assignment]

        win.show()
        _app().processEvents()
        self.assertTrue(win._nav_open)
        self.assertTrue(win.nav.isVisible())

        win.nav.toggle_btn.click()
        self.assertFalse(win._nav_open)
        win._nav_anim.stop()
        win.nav.setMinimumWidth(NAV_COLLAPSED_WIDTH)
        win.nav.setMaximumWidth(NAV_COLLAPSED_WIDTH)
        win._on_nav_anim_finished()
        self.assertTrue(win.nav.isVisible())
        self.assertTrue(win.nav._collapsed)
        self.assertEqual(win.nav.width(), NAV_COLLAPSED_WIDTH)
        _app().processEvents()
        nav_cx = win.nav.width() // 2
        self.assertAlmostEqual(win.nav.toggle_btn.geometry().center().x(), nav_cx, delta=3)
        self.assertAlmostEqual(win.nav._new_chat.geometry().center().x(), nav_cx, delta=3)
        self.assertAlmostEqual(win.nav._new_group.geometry().center().x(), nav_cx, delta=3)
        for item in win.nav._items.values():
            self.assertTrue(item._label.isHidden())
            self.assertTrue(item._icon.isVisible())
            self.assertAlmostEqual(item._icon.mapTo(win.nav, item._icon.rect().center()).x(), nav_cx, delta=3)

        win.nav.toggle_btn.click()
        self.assertTrue(win._nav_open)
        win._nav_anim.stop()
        win.nav.setMinimumWidth(NAV_WIDTH)
        win.nav.setMaximumWidth(NAV_WIDTH)
        win._on_nav_anim_finished()
        self.assertFalse(win.nav._collapsed)
        for item in win.nav._items.values():
            self.assertFalse(item._label.isHidden())
        win.close()

    def test_rename_group_dialog_validation_and_accept(self) -> None:
        dlg = RenameGroupDialog("Old Group")
        dlg.name_input.setText("A")
        dlg._accept()
        self.assertFalse(dlg.error.isHidden())
        self.assertEqual(dlg.group_name(), "")

        dlg.name_input.setText("  New Squad  ")
        dlg._accept()
        self.assertEqual(dlg.group_name(), "New Squad")
        dlg.close()

    def test_incoming_realtime_message_triggers_sound_once(self) -> None:
        from types import SimpleNamespace
        from payra.ui import sound as sound_mod

        orig_ready = auth_service.supabase_ready
        orig_session = auth_service.current_session
        orig_play = sound_mod.play_message_sound
        played: list[bool] = []
        sound_mod.play_message_sound = lambda: (played.append(True), True)[1]  # type: ignore[assignment]
        auth_service.supabase_ready = lambda: False  # type: ignore[assignment]
        auth_service.current_session = lambda: SimpleNamespace(id="me-id")  # type: ignore[assignment]
        try:
            win = MainWindow()
            win._live = True
            c1 = Conversation(id="c1", name="Alpha", preview="", time="", messages=[])
            win._conversations = {"c1": c1}
            win._active_id = "c1"
            win.chat_pane.show_conversation(c1)

            # Outgoing echo should NOT play sound
            win._on_realtime_change(
                "messages",
                "INSERT",
                {"id": "m-out", "conversation_id": "c1", "sender_id": "me-id", "content": "hi"},
                {},
            )
            self.assertEqual(len(played), 0)

            # Incoming message SHOULD play sound
            win._on_realtime_change(
                "messages",
                "INSERT",
                {"id": "m-in", "conversation_id": "c1", "sender_id": "other-id", "content": "yo"},
                {},
            )
            self.assertEqual(len(played), 1)
            win._live = False
            win.close()
        finally:
            auth_service.supabase_ready = orig_ready  # type: ignore[assignment]
            auth_service.current_session = orig_session  # type: ignore[assignment]
            sound_mod.play_message_sound = orig_play  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
