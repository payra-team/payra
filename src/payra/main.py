"""Application entry point — auth gate, then main shell."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from payra.resources import load_app_icon
from payra.services import auth as auth_service
from payra.ui.theme_app import apply_app_theme
from payra.ui.windows.auth_window import AuthWindow
from payra.ui.windows.main_window import MainWindow


class AppController:
    """Shows login/register until a session exists, then the main window."""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.auth_window: AuthWindow | None = None
        self.main_window: MainWindow | None = None

        if auth_service.current_session() is not None:
            self.show_main()
        else:
            self.show_auth()

    def show_auth(self) -> None:
        if self.main_window is not None:
            self.main_window.close()
            self.main_window = None
        if self.auth_window is None:
            self.auth_window = AuthWindow()
            self.auth_window.authenticated.connect(self.show_main)
        self.auth_window.show_login()

    def show_main(self) -> None:
        if self.auth_window is not None:
            self.auth_window.hide()
        if self.main_window is not None:
            self.main_window.close()
        self.main_window = MainWindow()
        self.main_window.logout_requested.connect(self._on_logout)
        self.main_window.show()

    def _on_logout(self) -> None:
        auth_service.logout()
        self.show_auth()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Payra")
    app.setOrganizationName("Payra")
    app.setWindowIcon(load_app_icon())
    apply_app_theme(app)
    # Keep a reference so it isn't garbage-collected
    app._payra = AppController(app)  # type: ignore[attr-defined]
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
