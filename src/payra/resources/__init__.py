"""Resolve bundled icons and images (Flutter-style assets layout)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# src/payra/resources/
RESOURCES = Path(__file__).resolve().parent
ICONS = RESOURCES / "icons"
IMAGES = RESOURCES / "images"
NAV_ICONS = ICONS / "nav"

LOGO_PATH = IMAGES / "logo.png"
APP_ICON_PATH = ICONS / "app_icon.png"
MASCOT_PATH = IMAGES / "nav_mascot.png"
# Primary brand illustration (carrier pigeon + envelope, transparent PNG)
PIGEON_PATH = IMAGES / "payra_pigeon.png"


def nav_icon_path(name: str) -> Path:
    """Prefer SVG; fall back to PNG if you drop a custom file."""
    svg = NAV_ICONS / f"{name}.svg"
    png = NAV_ICONS / f"{name}.png"
    if svg.exists():
        return svg
    if png.exists():
        return png
    raise FileNotFoundError(f"Missing nav icon: {name} (.svg or .png) in {NAV_ICONS}")


def load_tinted_icon(name: str, color: str, size: int = 22) -> QIcon:
    """Load nav SVG and paint with `color` (uses currentColor in the SVG)."""
    path = nav_icon_path(name)
    if path.suffix.lower() == ".png":
        pix = QPixmap(str(path)).scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        return QIcon(pix)

    raw = path.read_text(encoding="utf-8")
    # Allow both currentColor and a default #8B849C placeholder
    tinted = raw.replace("currentColor", color).replace("#8B849C", color)
    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(QPixmap.fromImage(image))


def _load_scaled_pixmap(path: Path, size: int, *, keep_aspect: bool = True) -> QPixmap:
    pix = QPixmap(str(path))
    if pix.isNull():
        return QPixmap()
    dpr = 2.0
    target = int(size * dpr)
    if keep_aspect:
        scaled = pix.scaled(
            target,
            target,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    else:
        scaled = pix.scaled(
            target,
            target,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
    scaled.setDevicePixelRatio(dpr)
    return scaled


def load_logo_pixmap(size: int = 34) -> QPixmap:
    """Small brand mark (nav wordmark). Prefers payra_pigeon, then logo.png."""
    for path in (PIGEON_PATH, LOGO_PATH, APP_ICON_PATH):
        if path.exists():
            pix = _load_scaled_pixmap(path, size)
            if not pix.isNull():
                return pix
    return QPixmap()


def load_pigeon_pixmap(size: int = 120) -> QPixmap:
    """Hero pigeon illustration for auth / larger brand surfaces."""
    if PIGEON_PATH.exists():
        pix = _load_scaled_pixmap(PIGEON_PATH, size)
        if not pix.isNull():
            return pix
    return load_logo_pixmap(size)


def brand_mark_label(size: int = 34, object_name: str = "BrandMark"):
    """QLabel showing the Payra logo — use beside the Payra wordmark."""
    from PySide6.QtWidgets import QLabel

    mark = QLabel()
    mark.setObjectName(object_name)
    mark.setAlignment(Qt.AlignCenter)
    mark.setFixedSize(size, size)
    mark.setPixmap(load_logo_pixmap(size))
    mark.setScaledContents(False)
    return mark


def pigeon_mark_label(size: int = 120, object_name: str = "PigeonMark"):
    """Larger pigeon mark (auth hero)."""
    from PySide6.QtWidgets import QLabel

    mark = QLabel()
    mark.setObjectName(object_name)
    mark.setAlignment(Qt.AlignCenter)
    # Allow slight height variance from aspect ratio
    pix = load_pigeon_pixmap(size)
    if not pix.isNull():
        mark.setPixmap(pix)
        mark.setFixedSize(pix.deviceIndependentSize().toSize())
    else:
        mark.setFixedSize(size, size)
    mark.setScaledContents(False)
    return mark


def load_app_icon() -> QIcon:
    """Window / dock icon (PNG should already have transparent corners)."""
    path = APP_ICON_PATH if APP_ICON_PATH.exists() else LOGO_PATH
    if not path.exists():
        return QIcon()
    image = QImage(str(path))
    if image.isNull():
        return QIcon()
    # Ensure ARGB so macOS dock respects alpha in the corners
    if image.format() != QImage.Format_ARGB32:
        image = image.convertToFormat(QImage.Format_ARGB32)
    return QIcon(QPixmap.fromImage(image))


def load_mascot_pixmap(max_width: int = 190) -> QPixmap:
    """Nav bottom illustration — Payra pigeon (fallback: legacy mascot)."""
    for path in (PIGEON_PATH, MASCOT_PATH):
        if not path.exists():
            continue
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        return pix.scaledToWidth(max_width, Qt.SmoothTransformation)
    return QPixmap()


def avatar_icon_size() -> QSize:
    return QSize(40, 40)
