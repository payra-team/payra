"""Image upload via Supabase Storage (`chat-images` bucket)."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from payra.services import supabase_client as sb
from payra.services.auth import current_session

BUCKET = "chat-images"
MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def upload_chat_image(local_path: str | Path) -> str:
    """Upload a local image; return its public URL."""
    client = sb.get_client()
    if client is None:
        raise ValueError("Supabase is not configured.")
    session = current_session()
    if session is None:
        raise ValueError("Not signed in.")

    path = Path(local_path)
    if not path.is_file():
        raise ValueError("File not found.")
    size = path.stat().st_size
    if size <= 0:
        raise ValueError("Empty file.")
    if size > MAX_BYTES:
        raise ValueError("Image must be 5 MB or smaller.")
    suffix = path.suffix.lower() or ".jpg"
    if suffix not in ALLOWED:
        raise ValueError("Use JPG, PNG, WEBP, or GIF.")

    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    object_path = f"{session.id}/{uuid.uuid4().hex}{suffix}"
    data = path.read_bytes()
    client.storage.from_(BUCKET).upload(
        object_path,
        data,
        file_options={"content-type": mime, "upsert": "false"},
    )
    public = client.storage.from_(BUCKET).get_public_url(object_path)
    # supabase-py may return str or dict-like
    if isinstance(public, str):
        return public.rstrip("?")
    return str(public)
