"""Organized Supabase Storage uploads with client-side image optimization.

Layout:
  avatars/{user_id}/avatar.webp          — profile photo (upsert)
  chat-images/{user_id}/chat/{uuid}.webp — chat attachments
"""

from __future__ import annotations

import uuid
from pathlib import Path

from payra.services import image_optimizer
from payra.services import supabase_client as sb
from payra.services.auth import current_session

AVATARS_BUCKET = "avatars"
CHAT_BUCKET = "chat-images"
MAX_SOURCE_BYTES = 12 * 1024 * 1024  # allow larger source; we compress before upload
ALLOWED_SOURCE = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def upload_avatar(local_path: str | Path) -> str:
    """Optimize and upload profile photo; return public URL."""
    session = _require_session()
    path = _validate_source(local_path)
    optimized = image_optimizer.optimize_avatar(path)
    object_path = f"{session.id}/avatar{optimized.extension}"
    return _upload_bytes(
        AVATARS_BUCKET,
        object_path,
        optimized.data,
        content_type=optimized.content_type,
        upsert=True,
    )


def upload_chat_image(local_path: str | Path) -> str:
    """Optimize and upload a chat image; return public URL."""
    session = _require_session()
    path = _validate_source(local_path)
    optimized = image_optimizer.optimize_chat_image(path)
    object_path = f"{session.id}/chat/{uuid.uuid4().hex}{optimized.extension}"
    return _upload_bytes(
        CHAT_BUCKET,
        object_path,
        optimized.data,
        content_type=optimized.content_type,
        upsert=False,
    )


def _require_session():
    client = sb.get_client()
    if client is None:
        raise ValueError("Supabase is not configured.")
    session = current_session()
    if session is None:
        raise ValueError("Not signed in.")
    return session


def _validate_source(local_path: str | Path) -> Path:
    path = Path(local_path)
    if not path.is_file():
        raise ValueError("File not found.")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Empty file.")
    if size > MAX_SOURCE_BYTES:
        raise ValueError("Image must be 12 MB or smaller before compression.")
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_SOURCE:
        raise ValueError("Use JPG, PNG, WEBP, GIF, or BMP.")
    return path


def _upload_bytes(
    bucket: str,
    object_path: str,
    data: bytes,
    *,
    content_type: str,
    upsert: bool,
) -> str:
    client = sb.get_client()
    if client is None:
        raise ValueError("Supabase is not configured.")
    if not data:
        raise ValueError("Nothing to upload.")

    options = {
        "content-type": content_type,
        "upsert": "true" if upsert else "false",
    }
    storage = client.storage.from_(bucket)
    try:
        storage.upload(object_path, data, file_options=options)
    except Exception as exc:
        # Retry as update when upsert insert fails on some Storage versions.
        if upsert and "already exists" in str(exc).lower():
            storage.update(object_path, data, file_options=options)
        else:
            raise ValueError(_storage_error(exc)) from exc

    public = storage.get_public_url(object_path)
    if isinstance(public, str):
        # Bust CDN/cache after avatar replace.
        url = public.rstrip("?")
        if upsert:
            return f"{url}?v={uuid.uuid4().hex[:8]}"
        return url
    return str(public)


def _storage_error(exc: BaseException) -> str:
    text = str(exc).strip() or "Upload failed."
    lower = text.lower()
    if "row-level security" in lower or "unauthorized" in lower or "403" in lower:
        return "Upload blocked by storage permissions. Sign in again and retry."
    if "payload" in lower or "too large" in lower or "413" in lower:
        return "Compressed image is still too large. Try a smaller photo."
    return text
