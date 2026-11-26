"""Load settings from environment. Fill .env after Supabase is created."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _candidate_env_paths() -> list[Path]:
    """Search repo root, CWD, next to frozen exe, and ~/.payra/."""
    paths: list[Path] = []
    # src/payra/config.py → parents[2] = repo root when running from source
    try:
        paths.append(Path(__file__).resolve().parents[2] / ".env")
    except IndexError:
        pass
    paths.append(Path.cwd() / ".env")
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / ".env")
    paths.append(Path.home() / ".payra" / ".env")
    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


_LOADED: Path | None = None
for _candidate in _candidate_env_paths():
    if _candidate.is_file():
        load_dotenv(_candidate, override=True)
        _LOADED = _candidate
        break
else:
    # Still call load_dotenv on the preferred path so empty installs are predictable
    _preferred = _candidate_env_paths()[0]
    load_dotenv(_preferred)
    _LOADED = _preferred


def env_file_path() -> Path:
    """Path used (or expected) for .env — useful for check_env / docs."""
    return _LOADED or (Path.cwd() / ".env")


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "").strip()
