"""Offscreen tests for responsive, unclipped NavSidebar pigeon mascot."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from payra.ui.theme_app import apply_app_theme  # noqa: E402
from payra.ui.widgets.nav_sidebar import NavSidebar  # noqa: E402

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


class NavSidebarMascotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _app()

    def test_mascot_unclipped_and_behind_nav_on_short_window(self) -> None:
        nav = NavSidebar()
        nav.resize(240, 620)
        nav.show()
        _app().processEvents()

        mascot = nav._mascot
        self.assertTrue(mascot.isVisible())
        self.assertLessEqual(mascot.geometry().bottom(), nav._you.geometry().top())
        # Aspect ratio preserved (not vertically squished/cut)
        pix_sz = mascot.pixmap().deviceIndependentSize()
        self.assertAlmostEqual(mascot.width(), pix_sz.width(), delta=2)
        self.assertAlmostEqual(mascot.height(), pix_sz.height(), delta=2)
        # Behind nav items in z-order
        children = nav.children()
        self.assertLess(children.index(mascot), children.index(nav._last_nav_item))
        self.assertLess(children.index(mascot), children.index(nav._you))
        nav.close()

    def test_mascot_full_size_on_tall_window(self) -> None:
        nav = NavSidebar()
        nav.resize(240, 860)
        nav.show()
        _app().processEvents()

        mascot = nav._mascot
        self.assertEqual(mascot.width(), 168)
        self.assertGreater(mascot.y(), nav._last_nav_item.geometry().bottom())
        self.assertLess(mascot.geometry().bottom(), nav._you.geometry().top())
        nav.close()


if __name__ == "__main__":
    unittest.main()
