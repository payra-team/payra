"""Async avatar download with memory + disk cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from payra.resources import IMAGES

_CACHE_DIR = IMAGES / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class AvatarCache(QObject):
    """Shared network avatar loader (demo URLs until Supabase Storage)."""

    pixmap_ready = Signal(str, QPixmap)  # url, pixmap

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mem: dict[str, QPixmap] = {}
        self._pending: dict[str, list] = {}
        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_finished)

    def get(self, url: str, callback) -> QPixmap | None:
        """Return cached pixmap immediately, or fetch and call callback(url, pixmap)."""
        if not url:
            return None
        if url in self._mem:
            return self._mem[url]

        disk = self._disk_path(url)
        if disk.exists():
            pix = QPixmap(str(disk))
            if not pix.isNull():
                self._mem[url] = pix
                return pix

        self._pending.setdefault(url, []).append(callback)
        if len(self._pending[url]) == 1:
            req = QNetworkRequest(QUrl(url))
            req.setAttribute(
                QNetworkRequest.Attribute.CacheLoadControlAttribute,
                QNetworkRequest.CacheLoadControl.PreferCache,
            )
            self._nam.get(req)
        return None

    def _disk_path(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]
        return _CACHE_DIR / f"{digest}.jpg"

    def _on_finished(self, reply: QNetworkReply) -> None:
        url = reply.url().toString()
        callbacks = self._pending.pop(url, [])
        if reply.error() != QNetworkReply.NetworkError.NoError:
            reply.deleteLater()
            return
        data = reply.readAll().data()
        reply.deleteLater()
        image = QImage.fromData(data)
        if image.isNull():
            return
        pix = QPixmap.fromImage(image)
        self._mem[url] = pix
        try:
            pix.save(str(self._disk_path(url)), "JPG")
        except Exception:
            pass
        for cb in callbacks:
            try:
                cb(url, pix)
            except Exception:
                pass
        self.pixmap_ready.emit(url, pix)


_avatar_cache: AvatarCache | None = None


def avatar_cache() -> AvatarCache:
    global _avatar_cache
    if _avatar_cache is None:
        _avatar_cache = AvatarCache()
    return _avatar_cache
