"""Supabase client factory — singleton with persisted user session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from payra.config import supabase_anon_key, supabase_url

_DATA_DIR = Path.home() / ".payra"
_TOKEN_FILE = _DATA_DIR / "supabase_session.json"

_client: Any | None = None


def supabase_ready() -> bool:
    url = supabase_url().strip()
    key = supabase_anon_key().strip()
    return bool(url and key and "YOUR_PROJECT" not in url and "your_anon" not in key.lower())


def get_client() -> Any | None:
    """Return a shared Supabase client, or None until URL + anon key are set."""
    global _client
    if not supabase_ready():
        return None
    if _client is None:
        from supabase import create_client

        _client = create_client(supabase_url(), supabase_anon_key())
        _restore_tokens(_client)
    return _client


def reset_client() -> None:
    """Drop cached client (after logout or key change)."""
    global _client
    _client = None


def save_tokens(access_token: str, refresh_token: str) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(
        json.dumps(
            {"access_token": access_token, "refresh_token": refresh_token},
            indent=2,
        ),
        encoding="utf-8",
    )


def clear_tokens() -> None:
    if _TOKEN_FILE.exists():
        _TOKEN_FILE.unlink()


def load_tokens() -> dict[str, str] | None:
    if not _TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(_TOKEN_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        if access and refresh:
            return {"access_token": access, "refresh_token": refresh}
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return None


def _restore_tokens(client: Any) -> None:
    tokens = load_tokens()
    if not tokens:
        return
    try:
        client.auth.set_session(tokens["access_token"], tokens["refresh_token"])
    except Exception:
        clear_tokens()
