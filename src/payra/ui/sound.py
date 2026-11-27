"""Lightweight notification sound effect for incoming messages."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from payra.resources import RESOURCES

NOTIFY_SOUND_PATH: Path = RESOURCES / "sounds" / "notify.wav"

_effect = None
_last_played = 0.0
_MIN_INTERVAL_SEC = 0.4


def play_message_sound() -> bool:
    """Play the incoming-message chime (debounced, safe in headless/no-audio envs)."""
    global _effect, _last_played
    now = time.monotonic()
    if now - _last_played < _MIN_INTERVAL_SEC:
        return False
    _last_played = now

    if not NOTIFY_SOUND_PATH.is_file():
        return False

    try:
        from PySide6.QtMultimedia import QSoundEffect

        if _effect is None:
            app = QApplication.instance()
            _effect = QSoundEffect(app)
            _effect.setSource(QUrl.fromLocalFile(str(NOTIFY_SOUND_PATH)))
            _effect.setVolume(0.45)
        _effect.play()
        return True
    except Exception:
        return False
