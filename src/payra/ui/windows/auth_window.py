"""Login, register, and forgot-password — brand-first auth shell."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from payra.resources import load_app_icon, pigeon_mark_label
from payra.services import auth as auth_service
from payra.ui.effects import apply_card_shadow
from payra.ui.widgets.loading import run_busy


def _field(label: str, widget: QLineEdit) -> QWidget:
    wrap = QWidget()
    wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    caption = QLabel(label)
    caption.setObjectName("AuthFieldLabel")
    lay.addWidget(caption)
    widget.setObjectName("AuthInput")
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    widget.setMinimumHeight(48)
    lay.addWidget(widget)
    return wrap


_EYE_OPEN = "👀"
_EYE_CLOSED = "🙈"


def _password_field(label: str, *, placeholder: str = "Password") -> tuple[QWidget, QLineEdit]:
    """Labeled password input with show/hide eye toggle."""
    wrap = QWidget()
    wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    lay = QVBoxLayout(wrap)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)

    caption = QLabel(label)
    caption.setObjectName("AuthFieldLabel")
    lay.addWidget(caption)

    shell = QFrame()
    shell.setObjectName("AuthPasswordShell")
    shell.setAttribute(Qt.WA_StyledBackground, True)
    shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    shell.setMinimumHeight(48)
    row = QHBoxLayout(shell)
    row.setContentsMargins(4, 0, 4, 0)
    row.setSpacing(0)

    edit = QLineEdit()
    edit.setObjectName("AuthPasswordInput")
    edit.setPlaceholderText(placeholder)
    edit.setEchoMode(QLineEdit.Password)
    edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    edit.setMinimumHeight(44)
    row.addWidget(edit, stretch=1)

    toggle = QToolButton()
    toggle.setObjectName("AuthPasswordToggle")
    toggle.setCursor(Qt.PointingHandCursor)
    toggle.setFocusPolicy(Qt.NoFocus)
    toggle.setAutoRaise(True)
    toggle.setFixedSize(40, 40)
    toggle.setText(_EYE_OPEN)
    toggle.setToolTip("Show password")

    def _toggle_visibility() -> None:
        if edit.echoMode() == QLineEdit.Password:
            edit.setEchoMode(QLineEdit.Normal)
            toggle.setText(_EYE_CLOSED)
            toggle.setToolTip("Hide password")
        else:
            edit.setEchoMode(QLineEdit.Password)
            toggle.setText(_EYE_OPEN)
            toggle.setToolTip("Show password")

    toggle.clicked.connect(_toggle_visibility)
    row.addWidget(toggle, 0, Qt.AlignVCenter)

    lay.addWidget(shell)
    return wrap, edit


def _scroll_body() -> tuple[QScrollArea, QVBoxLayout]:
    """Scrollable form body that shrinks cleanly on short windows."""
    scroll = QScrollArea()
    scroll.setObjectName("AuthFormScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    scroll.setFocusPolicy(Qt.NoFocus)
    # Avoid native viewport painting quirks under styled parents on macOS.
    scroll.viewport().setAutoFillBackground(False)
    scroll.setStyleSheet("QScrollArea#AuthFormScroll { background: transparent; border: none; }")

    body = QWidget()
    body.setObjectName("AuthFormScrollBody")
    body.setAutoFillBackground(False)
    body_lay = QVBoxLayout(body)
    body_lay.setContentsMargins(0, 0, 8, 0)
    body_lay.setSpacing(14)
    body_lay.setAlignment(Qt.AlignTop)
    scroll.setWidget(body)
    return scroll, body_lay


def _feature_card(emoji: str, text: str) -> QFrame:
    card = QFrame()
    card.setObjectName("AuthFeatureCard")
    card.setAttribute(Qt.WA_StyledBackground, True)
    row = QHBoxLayout(card)
    row.setContentsMargins(14, 12, 14, 12)
    row.setSpacing(12)
    icon = QLabel(emoji)
    icon.setObjectName("AuthFeatureEmoji")
    icon.setFixedWidth(28)
    icon.setAlignment(Qt.AlignCenter)
    row.addWidget(icon)
    label = QLabel(text)
    label.setObjectName("AuthFeatureText")
    label.setWordWrap(True)
    row.addWidget(label, stretch=1)
    return card


class AuthWindow(QWidget):
    """Brand-first auth shell with Login / Register / Forgot pages."""

    authenticated = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AuthWindow")
        self.setWindowTitle("Payra")
        self.setWindowIcon(load_app_icon())
        self.resize(1120, 740)
        self.setMinimumSize(960, 640)

        root = QHBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(28)

        brand = self._build_brand_panel()
        apply_card_shadow(brand)
        root.addWidget(brand, stretch=5)

        card = QFrame()
        card.setObjectName("AuthFormCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 40, 40, 36)
        card_lay.setSpacing(12)

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._login = _LoginPage()
        self._register = _RegisterPage()
        self._forgot = _ForgotPasswordPage()
        self._stack.addWidget(self._login)
        self._stack.addWidget(self._register)
        self._stack.addWidget(self._forgot)
        card_lay.addWidget(self._stack)
        # No QGraphicsDropShadowEffect on this card — it wraps QScrollArea pages
        # and that combo can segfault on macOS Cocoa when switching stacks.
        root.addWidget(card, stretch=5)

        self._login.switch_to_register.connect(self._show_register)
        self._login.switch_to_forgot.connect(self._show_forgot)
        self._register.switch_to_login.connect(self._go_login)
        self._register.account_created.connect(self._on_account_created)
        self._forgot.switch_to_login.connect(self._go_login)
        self._forgot.password_reset.connect(self._on_password_reset)
        self._login.authenticated.connect(self.authenticated.emit)

    def _build_brand_panel(self) -> QFrame:
        brand = QFrame()
        brand.setObjectName("AuthBrandPanel")
        brand.setAttribute(Qt.WA_StyledBackground, True)
        brand_lay = QVBoxLayout(brand)
        brand_lay.setContentsMargins(36, 40, 36, 28)
        brand_lay.setSpacing(14)

        top = QVBoxLayout()
        top.setSpacing(12)
        top.setAlignment(Qt.AlignHCenter)

        mark = pigeon_mark_label(128, "AuthBrandMark")
        mark.setAlignment(Qt.AlignCenter)
        mark_wrap = QHBoxLayout()
        mark_wrap.addStretch()
        mark_wrap.addWidget(mark)
        mark_wrap.addStretch()
        top.addLayout(mark_wrap)

        title = QLabel("Payra")
        title.setObjectName("AuthBrandTitle")
        title.setAlignment(Qt.AlignCenter)
        top.addWidget(title)

        tagline = QLabel("Messages that find their way — like a carrier pigeon.")
        tagline.setObjectName("AuthBrandTagline")
        tagline.setWordWrap(True)
        tagline.setAlignment(Qt.AlignCenter)
        top.addWidget(tagline)
        brand_lay.addLayout(top)

        brand_lay.addSpacing(18)

        features = QVBoxLayout()
        features.setSpacing(10)
        features.addWidget(_feature_card("🎓", "Verified university campus network"))
        features.addWidget(_feature_card("💬", "Private direct & student study groups"))
        features.addWidget(_feature_card("📁", "Lossless high-res notes & media sharing"))
        features.addWidget(_feature_card("⚡", "Ultra-fast realtime sync by Infinity"))
        brand_lay.addLayout(features)
        brand_lay.addStretch(1)

        line = QFrame()
        line.setObjectName("AuthBrandDivider")
        line.setFixedHeight(1)
        brand_lay.addWidget(line)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 10, 0, 0)
        left = QLabel("🔒  End-to-end encrypted")
        left.setObjectName("AuthBrandFooter")
        right = QLabel("by Infinity")
        right.setObjectName("AuthBrandFooter")
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        footer.addWidget(left)
        footer.addStretch()
        footer.addWidget(right)
        brand_lay.addLayout(footer)
        return brand

    def show_login(self) -> None:
        self._go_login()
        self.show()
        self.raise_()
        self.activateWindow()

    def _show_register(self) -> None:
        self._stack.setCurrentWidget(self._register)

    def _show_forgot(self) -> None:
        self._forgot.clear_form()
        self._stack.setCurrentWidget(self._forgot)

    def _go_login(self, email: str = "") -> None:
        self._login.clear_error()
        self._login.show_success("")
        if email:
            self._login.email.setText(email)
            self._login.password.clear()
            self._login.password.setFocus()
        self._stack.setCurrentWidget(self._login)

    def _on_account_created(self, email: str, display_name: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Welcome to Payra")
        box.setIcon(QMessageBox.Information)
        box.setText("Account created successfully")
        box.setInformativeText(
            f"Hi {display_name} — your Payra account is ready.\n\n"
            "Sign in with your email and password to start chatting."
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.button(QMessageBox.Ok).setText("Continue to sign in")
        box.exec()
        self._register.clear_form()
        self._go_login(email)
        self._login.show_success("Account created. Sign in to continue.")

    def _on_password_reset(self, email: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Password updated")
        box.setIcon(QMessageBox.Information)
        box.setText("Password reset successfully")
        box.setInformativeText(
            "Your new password is saved.\nSign in with your email and new password."
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.button(QMessageBox.Ok).setText("Continue to sign in")
        box.exec()
        self._forgot.clear_form()
        self._go_login(email)
        self._login.show_success("Password updated. Sign in to continue.")


class _LoginPage(QWidget):
    authenticated = Signal()
    switch_to_register = Signal()
    switch_to_forgot = Signal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

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

        scroll, body = _scroll_body()
        body.setSpacing(16)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email address")
        body.addWidget(_field("Email", self.email))

        pwd_wrap, self.password = _password_field("Password", placeholder="Password")
        body.addWidget(pwd_wrap)

        forgot_row = QHBoxLayout()
        forgot_row.addStretch()
        forgot = QPushButton("Forgot password?")
        forgot.setObjectName("AuthLinkButton")
        forgot.setCursor(Qt.PointingHandCursor)
        forgot.clicked.connect(self.switch_to_forgot.emit)
        forgot_row.addWidget(forgot)
        body.addLayout(forgot_row)
        body.addStretch(1)
        lay.addWidget(scroll, stretch=1)

        self.success = QLabel("")
        self.success.setObjectName("AuthSuccess")
        self.success.setWordWrap(True)
        self.success.hide()
        lay.addWidget(self.success)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        self.submit = QPushButton("Sign in")
        self.submit.setObjectName("AuthPrimaryButton")
        self.submit.setCursor(Qt.PointingHandCursor)
        self.submit.setMinimumHeight(52)
        self.submit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.submit.clicked.connect(self._submit)
        lay.addWidget(self.submit)

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

        self.password.returnPressed.connect(self._submit)
        self.email.returnPressed.connect(self._submit)

    def clear_error(self) -> None:
        self.error.hide()
        self.error.setText("")

    def show_success(self, text: str) -> None:
        if not text:
            self.success.hide()
            self.success.setText("")
            return
        self.success.setText(text)
        self.success.show()

    def _submit(self) -> None:
        self.clear_error()
        self.show_success("")
        email = self.email.text()
        password = self.password.text()
        host = self.window()

        def work():
            return auth_service.login(email, password)

        run_busy(
            host,
            "Signing in…",
            work,
            button=self.submit,
            idle_text="Sign in",
            busy_text="Signing in…",
            on_success=lambda _user: self.authenticated.emit(),
            on_error=lambda msg: (self.error.setText(msg), self.error.show()),
        )


class _RegisterPage(QWidget):
    account_created = Signal(str, str)
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

        scroll, body = _scroll_body()
        body.setSpacing(14)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Your display name")
        body.addWidget(_field("Display name", self.name))

        self.username = QLineEdit()
        self.username.setPlaceholderText("Choose a username")
        body.addWidget(_field("Username", self.username))

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email address")
        body.addWidget(_field("Email", self.email))

        pwd_wrap, self.password = _password_field(
            "Password", placeholder="Min 6 characters"
        )
        body.addWidget(pwd_wrap)

        confirm_wrap, self.confirm = _password_field(
            "Confirm password", placeholder="Confirm password"
        )
        body.addWidget(confirm_wrap)
        body.addStretch(1)
        lay.addWidget(scroll, stretch=1)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        self.submit = QPushButton("Create account")
        self.submit.setObjectName("AuthPrimaryButton")
        self.submit.setCursor(Qt.PointingHandCursor)
        self.submit.setMinimumHeight(52)
        self.submit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.submit.clicked.connect(self._submit)
        lay.addWidget(self.submit)

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

        self.confirm.returnPressed.connect(self._submit)

    def clear_form(self) -> None:
        self.name.clear()
        self.username.clear()
        self.email.clear()
        self.password.clear()
        self.confirm.clear()
        self.error.hide()
        self.error.setText("")

    def _submit(self) -> None:
        self.error.hide()
        if self.password.text() != self.confirm.text():
            self.error.setText("Passwords do not match.")
            self.error.show()
            return
        name = self.name.text().strip()
        email = self.email.text().strip()
        password = self.password.text()
        username = self.username.text()
        host = self.window()

        def work():
            user = auth_service.register(
                name, email, password, username=username
            )
            auth_service.logout()
            return user

        def ok(_user) -> None:
            self.account_created.emit(email.lower(), name or "there")

        def fail(msg: str) -> None:
            if "account created" in msg.lower() or "confirm your email" in msg.lower():
                auth_service.logout()
                self.account_created.emit(email.lower(), name or "there")
                return
            self.error.setText(msg)
            self.error.show()

        run_busy(
            host,
            "Creating your account…",
            work,
            button=self.submit,
            idle_text="Create account",
            busy_text="Creating…",
            on_success=ok,
            on_error=fail,
        )


class _ForgotPasswordPage(QWidget):
    """Simple MVP reset: email + new password + confirm (no email link)."""

    password_reset = Signal(str)  # email
    switch_to_login = Signal()

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        eyebrow = QLabel("ACCOUNT RECOVERY")
        eyebrow.setObjectName("AuthEyebrow")
        lay.addWidget(eyebrow)

        heading = QLabel("Reset password")
        heading.setObjectName("AuthHeading")
        lay.addWidget(heading)

        sub = QLabel(
            "Enter your account email and choose a new password. "
            "No email verification for now."
        )
        sub.setObjectName("AuthSubheading")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        scroll, body = _scroll_body()
        body.setSpacing(16)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email address")
        body.addWidget(_field("Email", self.email))

        pwd_wrap, self.password = _password_field(
            "New password", placeholder="New password (min 6)"
        )
        body.addWidget(pwd_wrap)

        confirm_wrap, self.confirm = _password_field(
            "Confirm password", placeholder="Confirm new password"
        )
        body.addWidget(confirm_wrap)
        body.addStretch(1)
        lay.addWidget(scroll, stretch=1)

        self.error = QLabel("")
        self.error.setObjectName("AuthError")
        self.error.setWordWrap(True)
        self.error.hide()
        lay.addWidget(self.error)

        self.submit = QPushButton("Update password")
        self.submit.setObjectName("AuthPrimaryButton")
        self.submit.setCursor(Qt.PointingHandCursor)
        self.submit.setMinimumHeight(52)
        self.submit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.submit.clicked.connect(self._submit)
        lay.addWidget(self.submit)

        switch_row = QHBoxLayout()
        hint = QLabel("Remembered it?")
        hint.setObjectName("AuthSubheading")
        switch_row.addWidget(hint)
        switch = QPushButton("Back to sign in")
        switch.setObjectName("AuthLinkButton")
        switch.setCursor(Qt.PointingHandCursor)
        switch.clicked.connect(self.switch_to_login.emit)
        switch_row.addWidget(switch)
        switch_row.addStretch()
        lay.addLayout(switch_row)

        self.confirm.returnPressed.connect(self._submit)

    def clear_form(self) -> None:
        self.email.clear()
        self.password.clear()
        self.confirm.clear()
        self.error.hide()
        self.error.setText("")

    def _submit(self) -> None:
        self.error.hide()
        if self.password.text() != self.confirm.text():
            self.error.setText("Passwords do not match.")
            self.error.show()
            return
        email = self.email.text().strip()
        password = self.password.text()
        host = self.window()

        run_busy(
            host,
            "Updating password…",
            lambda: auth_service.reset_password(email, password),
            button=self.submit,
            idle_text="Update password",
            busy_text="Updating…",
            on_success=lambda _r: self.password_reset.emit(email.lower()),
            on_error=lambda msg: (self.error.setText(msg), self.error.show()),
        )
