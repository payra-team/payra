"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from payra.ui.theme_app import apply_app_theme
from payra.ui.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Payra")
    app.setOrganizationName("Payra")
    apply_app_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
