#!/usr/bin/env python3
"""Print whether Payra will run LIVE (Supabase) or DEMO (local/fake users)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from payra.config import env_file_path, supabase_anon_key, supabase_url  # noqa: E402
from payra.services.supabase_client import supabase_ready  # noqa: E402


def main() -> int:
    path = env_file_path()
    print(f".env path : {path}")
    print(f"exists    : {path.exists()}")
    url = supabase_url().strip()
    key = supabase_anon_key().strip()
    print(f"URL set   : {bool(url)}  ({url[:40] + '…' if len(url) > 40 else url or '(empty)'})")
    print(f"anon set  : {bool(key)}  ({'(empty)' if not key else key[:12] + '…'})")
    if supabase_ready():
        print("mode      : LIVE  → users & chats come from Supabase")
        return 0
    print("mode      : DEMO  → fake contacts / local ~/.payra users (NOT the database)")
    print()
    print("Fix: put a real .env next to README.md (see docs/TEAMMATE_SETUP.md)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
