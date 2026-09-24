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


def load_logo_pixmap(size: int = 34) -> QPixmap:
    """Carrier-pigeon brand mark (Payra = pigeon + message)."""
    pix = QPixmap(str(LOGO_PATH))
    if pix.isNull() and APP_ICON_PATH.exists():
        pix = QPixmap(str(APP_ICON_PATH))
    if pix.isNull():
        return QPixmap()
    # HiDPI-aware scale for crisp nav / auth marks
    dpr = 2.0
    target = int(size * dpr)
    scaled = pix.scaled(
        target,
        target,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(dpr)
    return scaled


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


def load_app_icon() -> QIcon:
    """Window / dock icon."""
    if APP_ICON_PATH.exists():
        return QIcon(str(APP_ICON_PATH))
    # Fallback to logo mark
    if LOGO_PATH.exists():
        return QIcon(str(LOGO_PATH))
    return QIcon()


def load_mascot_pixmap(max_width: int = 190) -> QPixmap:
    """Nav bottom illustration (PNG with transparent background)."""
    path = MASCOT_PATH
    pix = QPixmap(str(path))
    if pix.isNull():
        return QPixmap()
    return pix.scaledToWidth(max_width, Qt.SmoothTransformation)


def avatar_icon_size() -> QSize:
    return QSize(40, 40)
