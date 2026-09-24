"""Login and register windows (local auth until Supabase)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from payra.resources import brand_mark_label, load_app_icon
from payra.services import auth as auth_service
from payra.ui.effects import apply_card_shadow


def _form_brand_row() -> QWidget:
    """Small logo + Payra above Sign in / Create account."""
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 8)
    lay.setSpacing(10)
    lay.addWidget(brand_mark_label(40, "AuthFormBrandMark"))
    name = QLabel("Payra")
    name.setObjectName("AuthFormBrandName")
    lay.addWidget(name)
    lay.addStretch()
    return row


class AuthWindow(QWidget):
    """Brand-first auth shell with Login / Register pages."""

    authenticated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthWindow")
        self.setWindowTitle("Payra")
        self.setWindowIcon(load_app_icon())
        self.resize(980, 640)
        self.setMinimumSize(860, 560)

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(24)

        # Left brand panel
        brand = QFrame()
        brand.setObjectName("AuthBrandPanel")
        brand.setAttribute(Qt.WA_StyledBackground, True)
        brand_lay = QVBoxLayout(brand)
        brand_lay.setContentsMargins(36, 40, 36, 40)
        brand_lay.setSpacing(14)
        brand_lay.addStretch(1)

        mark_row = QHBoxLayout()
        mark_row.addWidget(brand_mark_label(88, "AuthBrandMark"))
        mark_row.addStretch()
        brand_lay.addLayout(mark_row)

        title = QLabel("Payra")
        title.setObjectName("AuthBrandTitle")
        brand_lay.addWidget(title)

        tagline = QLabel(
            "Messages that find their way — like a carrier pigeon.\n"
            "Desktop chat for your campus circle."
        )
        tagline.setObjectName("AuthBrandTagline")
        tagline.setWordWrap(True)
        brand_lay.addWidget(tagline)
        brand_lay.addStretch(2)

        note = QLabel("Auth is local for now · Supabase next")
        note.setObjectName("AuthBrandNote")
        brand_lay.addWidget(note)
        apply_card_shadow(brand)
        root.addWidget(brand, stretch=5)

        # Right card with stacked forms
        card = QFrame()
        card.setObjectName("AuthFormCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(36, 36, 36, 32)
        card_lay.setSpacing(10)

        self._stack = QStackedWidget()
        self._login = _LoginPage()
        self._register = _RegisterPage()
        self._stack.addWidget(self._login)
        self._stack.addWidget(self._register)
        card_lay.addWidget(self._stack)
        apply_card_shadow(card)
        root.addWidget(card, stretch=4)

        self._login.switch_to_register.connect(lambda: self._stack.setCurrentWidget(self._register))
        self._register.switch_to_login.connect(lambda: self._stack.setCurrentWidget(self._login))
        self._login.authenticated.connect(self.authenticated.emit)
        self._register.authenticated.connect(self.authenticated.emit)

    def show_login(self) -> None:
        self._login.clear_error()
        self._stack.setCurrentWidget(self._login)
        self.show()
        self.raise_()
        self.activateWindow()


class _LoginPage(QWidget):
    authenticated = Signal()
    switch_to_register = Signal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        lay.addWidget(_form_brand_row())

        heading = QLabel("Sign in")
        heading.setObjectName("AuthHeading")
        lay.addWidget(heading)

        sub = QLabel("Use the email and password you registered with.")
        sub.setObjectName("AuthSubheading")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(8)

        self.email = QLineEdit()
        self.email.setObjectName("AuthInput")
        self.email.setPlaceholderText("Email")
        lay.addWidget(self.email)

        self.password = QLineEdit()
        self.password.setObjectName("AuthInput")
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.password)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        submit = QPushButton("Sign in")
        submit.setObjectName("AuthPrimaryButton")
        submit.setCursor(Qt.PointingHandCursor)
        submit.clicked.connect(self._submit)
        lay.addWidget(submit)

        switch = QPushButton("Create account")
        switch.setObjectName("AuthLinkButton")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(self.switch_to_register.emit)
        lay.addWidget(switch)
        lay.addStretch()

        self.password.returnPressed.connect(self._submit)
        self.email.returnPressed.connect(self._submit)

    def clear_error(self) -> None:
        self.error.hide()
        self.error.setText("")

    def _submit(self) -> None:
        self.clear_error()
        try:
            auth_service.login(self.email.text(), self.password.text())
        except ValueError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return
        self.authenticated.emit()


class _RegisterPage(QWidget):
    authenticated = Signal()
    switch_to_login = Signal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(_form_brand_row())

        heading = QLabel("Create account")
        heading.setObjectName("AuthHeading")
        lay.addWidget(heading)

        sub = QLabel("No email verification for MVP — you can sign in right away.")
        sub.setObjectName("AuthSubheading")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(4)

        self.name = QLineEdit()
        self.name.setObjectName("AuthInput")
        self.name.setPlaceholderText("Display name")
        lay.addWidget(self.name)

        self.username = QLineEdit()
        self.username.setObjectName("AuthInput")
        self.username.setPlaceholderText("Username (optional)")
        lay.addWidget(self.username)

        self.email = QLineEdit()
        self.email.setObjectName("AuthInput")
        self.email.setPlaceholderText("Email")
        lay.addWidget(self.email)

        self.password = QLineEdit()
        self.password.setObjectName("AuthInput")
        self.password.setPlaceholderText("Password (min 6)")
        self.password.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.password)

        self.confirm = QLineEdit()
        self.confirm.setObjectName("AuthInput")
        self.confirm.setPlaceholderText("Confirm password")
        self.confirm.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.confirm)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        submit = QPushButton("Create account")
        submit.setObjectName("AuthPrimaryButton")
        submit.setCursor(Qt.PointingHandCursor)
        submit.clicked.connect(self._submit)
        lay.addWidget(submit)

        switch = QPushButton("Already have an account? Sign in")
        switch.setObjectName("AuthLinkButton")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(self.switch_to_login.emit)
        lay.addWidget(switch)
        lay.addStretch()

        self.confirm.returnPressed.connect(self._submit)

    def _submit(self) -> None:
        self.error.hide()
        if self.password.text() != self.confirm.text():
            self.error.setText("Passwords do not match.")
            self.error.show()
            return
        try:
            auth_service.register(
                self.name.text(),
                self.email.text(),
                self.password.text(),
                username=self.username.text(),
            )
        except ValueError as exc:
            self.error.setText(str(exc))
            self.error.show()
            return
        self.authenticated.emit()
