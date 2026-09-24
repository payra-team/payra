"""Supabase client factory — connect after project keys are in `.env`."""

from __future__ import annotations

from typing import Any

from payra.config import supabase_anon_key, supabase_url
from payra.services.auth import supabase_ready


def get_client() -> Any | None:
    """Return a Supabase client, or None until URL + anon key are configured.

    Keys live only in the project-root `.env` file (never commit it):

        SUPABASE_URL=https://xxxx.supabase.co
        SUPABASE_ANON_KEY=eyJ...

    Copy from Supabase Dashboard → Project Settings → API.
    Use the **anon / public** key in the desktop app — not the service_role key.
    """
    if not supabase_ready():
        return None
    from supabase import create_client

    return create_client(supabase_url(), supabase_anon_key())
