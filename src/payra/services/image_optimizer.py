"""Compress and normalize images before Supabase Storage uploads."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps


@dataclass(frozen=True)
class OptimizedImage:
    data: bytes
    content_type: str
    extension: str  # e.g. ".webp"
    width: int
    height: int
    original_bytes: int
    optimized_bytes: int


def optimize_image(
    local_path: str | Path,
    *,
    max_side: int = 1600,
    quality: int = 82,
    prefer_webp: bool = True,
) -> OptimizedImage:
    """
    Load an image, auto-orient, downscale, and compress.

    Returns WEBP by default (smaller); falls back to JPEG if WEBP encode fails.
    """
    path = Path(local_path)
    if not path.is_file():
        raise ValueError("File not found.")
    original_bytes = path.stat().st_size
    if original_bytes <= 0:
        raise ValueError("Empty file.")

    try:
        with Image.open(path) as raw:
            image = ImageOps.exif_transpose(raw)
            image.load()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read that image file.") from exc

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        # Preserve alpha when encoding WEBP; flatten for JPEG fallback.
        rgba = image.convert("RGBA")
        working = rgba
        has_alpha = True
    else:
        working = image.convert("RGB")
        has_alpha = False

    working = _downscale(working, max_side=max_side)

    if prefer_webp:
        try:
            data = _encode(working, "WEBP", quality=quality)
            return OptimizedImage(
                data=data,
                content_type="image/webp",
                extension=".webp",
                width=working.width,
                height=working.height,
                original_bytes=original_bytes,
                optimized_bytes=len(data),
            )
        except Exception:
            pass

    flat = working.convert("RGB") if has_alpha or working.mode != "RGB" else working
    data = _encode(flat, "JPEG", quality=quality)
    return OptimizedImage(
        data=data,
        content_type="image/jpeg",
        extension=".jpg",
        width=flat.width,
        height=flat.height,
        original_bytes=original_bytes,
        optimized_bytes=len(data),
    )


def optimize_avatar(local_path: str | Path) -> OptimizedImage:
    """Square avatar: center-crop, max 512px, compressed WEBP/JPEG."""
    path = Path(local_path)
    if not path.is_file():
        raise ValueError("File not found.")
    original_bytes = path.stat().st_size
    if original_bytes <= 0:
        raise ValueError("Empty file.")

    try:
        with Image.open(path) as raw:
            image = ImageOps.exif_transpose(raw)
            image.load()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read that image file.") from exc

    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        working = image.convert("RGBA")
        has_alpha = True
    else:
        working = image.convert("RGB")
        has_alpha = False

    working = ImageOps.fit(
        working, (512, 512), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
    )

    try:
        data = _encode(working, "WEBP", quality=80)
        return OptimizedImage(
            data=data,
            content_type="image/webp",
            extension=".webp",
            width=working.width,
            height=working.height,
            original_bytes=original_bytes,
            optimized_bytes=len(data),
        )
    except Exception:
        flat = working.convert("RGB") if has_alpha or working.mode != "RGB" else working
        data = _encode(flat, "JPEG", quality=80)
        return OptimizedImage(
            data=data,
            content_type="image/jpeg",
            extension=".jpg",
            width=flat.width,
            height=flat.height,
            original_bytes=original_bytes,
            optimized_bytes=len(data),
        )


def optimize_chat_image(local_path: str | Path) -> OptimizedImage:
    """Chat attachment: max 1600px, balanced quality."""
    return optimize_image(local_path, max_side=1600, quality=82, prefer_webp=True)


def _downscale(image: Image.Image, *, max_side: int) -> Image.Image:
    w, h = image.size
    longest = max(w, h)
    if longest <= max_side:
        return image
    scale = max_side / float(longest)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _encode(image: Image.Image, fmt: str, *, quality: int) -> bytes:
    buf = io.BytesIO()
    save_kwargs: dict = {"optimize": True}
    if fmt.upper() == "JPEG":
        save_kwargs.update(quality=quality, progressive=True)
    elif fmt.upper() == "WEBP":
        save_kwargs.update(quality=quality, method=6)
    image.save(buf, format=fmt, **save_kwargs)
    data = buf.getvalue()
    if not data:
        raise ValueError("Image compression produced empty output.")
    return data
