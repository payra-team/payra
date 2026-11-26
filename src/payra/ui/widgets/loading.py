"""Reusable loading overlay + background busy runner."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEvent, QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LoadingOverlay(QFrame):
    """Semi-transparent cover with indeterminate progress + message."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()
        parent.installEventFilter(self)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(14)

        card = QFrame()
        card.setObjectName("LoadingCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(28, 22, 28, 22)
        card_lay.setSpacing(12)
        card_lay.setAlignment(Qt.AlignCenter)

        self._label = QLabel("Loading…")
        self._label.setObjectName("LoadingLabel")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        card_lay.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setObjectName("LoadingBar")
        self._bar.setRange(0, 0)  # indeterminate
        self._bar.setTextVisible(False)
        self._bar.setFixedWidth(180)
        self._bar.setFixedHeight(6)
        card_lay.addWidget(self._bar, 0, Qt.AlignCenter)

        lay.addWidget(card, 0, Qt.AlignCenter)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())

    def show_message(self, message: str = "Loading…") -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
            self.raise_()
        self._label.setText(message)
        self.show()

    def hide_message(self) -> None:
        self.hide()


class _WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class _Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 — surface to UI
            self.signals.error.emit(str(exc) or repr(exc))
            return
        self.signals.finished.emit(result)


def attach_overlay(widget: QWidget) -> LoadingOverlay:
    """Create (or reuse) a loading overlay as a child of `widget`."""
    existing = widget.findChild(LoadingOverlay, "LoadingOverlay")
    if existing is not None:
        return existing
    overlay = LoadingOverlay(widget)
    overlay.setObjectName("LoadingOverlay")
    return overlay


def set_button_busy(button: QPushButton, busy: bool, *, idle_text: str, busy_text: str) -> None:
    button.setEnabled(not busy)
    button.setText(busy_text if busy else idle_text)


class BusyScope:
    """Show overlay while a background task runs; callbacks on UI thread."""

    def __init__(
        self,
        host: QWidget,
        message: str,
        work: Callable[[], Any],
        *,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_done: Callable[[], None] | None = None,
        button: QPushButton | None = None,
        idle_text: str = "",
        busy_text: str = "Please wait…",
    ) -> None:
        self.host = host
        self.overlay = attach_overlay(host)
        self.on_success = on_success
        self.on_error = on_error
        self.on_done = on_done
        self.button = button
        self.idle_text = idle_text or (button.text() if button else "")
        self.busy_text = busy_text
        self._worker: _Worker | None = None

        self.overlay.show_message(message)
        if button is not None:
            set_button_busy(button, True, idle_text=self.idle_text, busy_text=busy_text)
            if hasattr(host, "setEnabled"):
                # Keep host interactive only via overlay block
                pass

        worker = _Worker(work)
        worker.signals.finished.connect(self._ok)
        worker.signals.error.connect(self._fail)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _ok(self, result: object) -> None:
        self._finish()
        if self.on_success is not None:
            self.on_success(result)

    @Slot(str)
    def _fail(self, message: str) -> None:
        self._finish()
        if self.on_error is not None:
            self.on_error(message)

    def _finish(self) -> None:
        self.overlay.hide_message()
        if self.button is not None:
            set_button_busy(
                self.button, False, idle_text=self.idle_text, busy_text=self.busy_text
            )
        if self.on_done is not None:
            self.on_done()


def run_busy(
    host: QWidget,
    message: str,
    work: Callable[[], Any],
    *,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    on_done: Callable[[], None] | None = None,
    button: QPushButton | None = None,
    idle_text: str = "",
    busy_text: str = "Please wait…",
) -> BusyScope:
    """Fire-and-forget busy helper (keeps a ref on the host)."""
    refs: list[BusyScope] = getattr(host, "_busy_scopes", None) or []
    setattr(host, "_busy_scopes", refs)
    holder: list[BusyScope] = []

    def _done() -> None:
        if holder:
            try:
                refs.remove(holder[0])
            except ValueError:
                pass
        if on_done is not None:
            on_done()

    scope = BusyScope(
        host,
        message,
        work,
        on_success=on_success,
        on_error=on_error,
        on_done=_done,
        button=button,
        idle_text=idle_text,
        busy_text=busy_text,
    )
    holder.append(scope)
    refs.append(scope)
    return scope
