"""Background busy runner with WhatsApp-style inline feedback (no center dialog)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QPushButton, QWidget


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


def set_button_busy(button: QPushButton, busy: bool, *, idle_text: str, busy_text: str) -> None:
    button.setEnabled(not busy)
    button.setText(busy_text if busy else idle_text)


class BusyScope:
    """Run work off the UI thread; optional button busy + wait cursor."""

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
        wait_cursor: bool = True,
    ) -> None:
        del message  # kept for call-site compatibility; UI feedback is inline elsewhere
        self.host = host
        self.on_success = on_success
        self.on_error = on_error
        self.on_done = on_done
        self.button = button
        self.idle_text = idle_text or (button.text() if button else "")
        self.busy_text = busy_text
        self.wait_cursor = wait_cursor
        self._result: object | None = None
        self._error: str | None = None
        self._worker: _Worker | None = None

        if wait_cursor:
            from PySide6.QtWidgets import QApplication

            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        if button is not None:
            set_button_busy(button, True, idle_text=self.idle_text, busy_text=busy_text)

        worker = _Worker(work)
        worker.signals.setParent(host)
        worker.signals.finished.connect(self._ok)
        worker.signals.error.connect(self._fail)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _ok(self, result: object) -> None:
        self._result = result
        self._finish(success=True)

    @Slot(str)
    def _fail(self, message: str) -> None:
        self._error = message
        self._finish(success=False)

    def _finish(self, *, success: bool) -> None:
        if self.wait_cursor:
            from PySide6.QtWidgets import QApplication

            QApplication.restoreOverrideCursor()

        if self.button is not None:
            set_button_busy(
                self.button, False, idle_text=self.idle_text, busy_text=self.busy_text
            )

        result = self._result
        error = self._error
        on_success = self.on_success
        on_error = self.on_error
        on_done = self.on_done

        def _deliver() -> None:
            if success and on_success is not None:
                on_success(result)
            elif not success and on_error is not None:
                on_error(error or "Something went wrong.")
            if on_done is not None:
                on_done()

        QTimer.singleShot(0, _deliver)


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
    wait_cursor: bool = True,
) -> BusyScope:
    """Fire-and-forget busy helper (keeps a ref on the host). No modal dialog."""
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
        wait_cursor=wait_cursor,
    )
    holder.append(scope)
    refs.append(scope)
    return scope
