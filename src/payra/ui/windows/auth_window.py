"""Login and register — brand-first auth shell."""

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


def _field(label: str, widget: QLineEdit) -> QWidget:
    wrap = QWidget()
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    caption = QLabel(label)
    caption.setObjectName("AuthFieldLabel")
    lay.addWidget(caption)
    lay.addWidget(widget)
    return wrap


class AuthWindow(QWidget):
    """Brand-first auth shell with Login / Register pages."""

    authenticated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthWindow")
        self.setWindowTitle("Payra")
        self.setWindowIcon(load_app_icon())
        self.resize(1040, 700)
        self.setMinimumSize(900, 600)

        root = QHBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(28)

        # Left brand panel
        brand = QFrame()
        brand.setObjectName("AuthBrandPanel")
        brand.setAttribute(Qt.WA_StyledBackground, True)
        brand_lay = QVBoxLayout(brand)
        brand_lay.setContentsMargins(40, 44, 40, 40)
        brand_lay.setSpacing(16)
        brand_lay.addStretch(1)

        mark_row = QHBoxLayout()
        mark = brand_mark_label(96, "AuthBrandMark")
        mark.setStyleSheet(
            "background: rgba(255,255,255,0.16); border-radius: 28px; padding: 10px;"
        )
        mark_row.addWidget(mark)
        mark_row.addStretch()
        brand_lay.addLayout(mark_row)

        title = QLabel("Payra")
        title.setObjectName("AuthBrandTitle")
        brand_lay.addWidget(title)

        tagline = QLabel(
            "Messages that find their way —\nlike a carrier pigeon."
        )
        tagline.setObjectName("AuthBrandTagline")
        tagline.setWordWrap(True)
        brand_lay.addWidget(tagline)

        points = QLabel(
            "• Private campus chats\n"
            "• Groups & media sharing\n"
            "• Realtime when you’re online"
        )
        points.setObjectName("AuthBrandPoints")
        points.setWordWrap(True)
        brand_lay.addWidget(points)
        brand_lay.addStretch(2)

        mode = (
            "Secure sign-in via Supabase"
            if auth_service.supabase_ready()
            else "Local mode · add .env to connect Supabase"
        )
        note = QLabel(mode)
        note.setObjectName("AuthBrandNote")
        brand_lay.addWidget(note)
        apply_card_shadow(brand)
        root.addWidget(brand, stretch=5)

        # Right card
        card = QFrame()
        card.setObjectName("AuthFormCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 40, 40, 36)
        card_lay.setSpacing(12)

        self._stack = QStackedWidget()
        self._login = _LoginPage()
        self._register = _RegisterPage()
        self._stack.addWidget(self._login)
        self._stack.addWidget(self._register)
        card_lay.addWidget(self._stack)
        apply_card_shadow(card)
        root.addWidget(card, stretch=4)

        self._login.switch_to_register.connect(
            lambda: self._stack.setCurrentWidget(self._register)
        )
        self._register.switch_to_login.connect(
            lambda: self._stack.setCurrentWidget(self._login)
        )
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
        lay.setSpacing(14)

        eyebrow = QLabel("WELCOME BACK")
        eyebrow.setObjectName("AuthEyebrow")
        lay.addWidget(eyebrow)

        heading = QLabel("Sign in to Payra")
        heading.setObjectName("AuthHeading")
        lay.addWidget(heading)

        sub = QLabel("Pick up your conversations exactly where you left off.")
        sub.setObjectName("AuthSubheading")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(10)

        self.email = QLineEdit()
        self.email.setObjectName("AuthInput")
        self.email.setPlaceholderText("you@university.edu")
        lay.addWidget(_field("Email", self.email))

        self.password = QLineEdit()
        self.password.setObjectName("AuthInput")
        self.password.setPlaceholderText("Your password")
        self.password.setEchoMode(QLineEdit.Password)
        lay.addWidget(_field("Password", self.password))

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        submit = QPushButton("Sign in")
        submit.setObjectName("AuthPrimaryButton")
        submit.setCursor(Qt.PointingHandCursor)
        submit.setMinimumHeight(48)
        submit.clicked.connect(self._submit)
        lay.addWidget(submit)

        switch_row = QHBoxLayout()
        switch_row.setSpacing(4)
        hint = QLabel("New here?")
        hint.setObjectName("AuthSubheading")
        switch_row.addWidget(hint)
        switch = QPushButton("Create an account")
        switch.setObjectName("AuthLinkButton")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(self.switch_to_register.emit)
        switch_row.addWidget(switch)
        switch_row.addStretch()
        lay.addLayout(switch_row)
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
        lay.setSpacing(12)

        eyebrow = QLabel("JOIN PAYRA")
        eyebrow.setObjectName("AuthEyebrow")
        lay.addWidget(eyebrow)

        heading = QLabel("Create your account")
        heading.setObjectName("AuthHeading")
        lay.addWidget(heading)

        sub = QLabel("A few details and you’re ready to message your circle.")
        sub.setObjectName("AuthSubheading")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(4)

        self.name = QLineEdit()
        self.name.setObjectName("AuthInput")
        self.name.setPlaceholderText("Mosharof Khan")
        lay.addWidget(_field("Display name", self.name))

        self.username = QLineEdit()
        self.username.setObjectName("AuthInput")
        self.username.setPlaceholderText("mosharof")
        lay.addWidget(_field("Username", self.username))

        self.email = QLineEdit()
        self.email.setObjectName("AuthInput")
        self.email.setPlaceholderText("you@university.edu")
        lay.addWidget(_field("Email", self.email))

        row = QHBoxLayout()
        row.setSpacing(12)
        self.password = QLineEdit()
        self.password.setObjectName("AuthInput")
        self.password.setPlaceholderText("Min 6 characters")
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit()
        self.confirm.setObjectName("AuthInput")
        self.confirm.setPlaceholderText("Repeat password")
        self.confirm.setEchoMode(QLineEdit.Password)
        row.addWidget(_field("Password", self.password))
        row.addWidget(_field("Confirm", self.confirm))
        lay.addLayout(row)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        submit = QPushButton("Create account")
        submit.setObjectName("AuthPrimaryButton")
        submit.setCursor(Qt.PointingHandCursor)
        submit.setMinimumHeight(48)
        submit.clicked.connect(self._submit)
        lay.addWidget(submit)

        switch_row = QHBoxLayout()
        hint = QLabel("Already have an account?")
        hint.setObjectName("AuthSubheading")
        switch_row.addWidget(hint)
        switch = QPushButton("Sign in")
        switch.setObjectName("AuthLinkButton")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(self.switch_to_login.emit)
        switch_row.addWidget(switch)
        switch_row.addStretch()
        lay.addLayout(switch_row)
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
