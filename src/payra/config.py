"""Load settings from environment. Fill .env after Supabase is created."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "")


def supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "")
