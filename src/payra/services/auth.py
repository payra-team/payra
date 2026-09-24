"""Auth: register, login, session (no email verification).

Until Supabase keys are set in `.env`, credentials are stored locally
under `~/.payra/`. After keys exist, the same API will call Supabase Auth.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

from payra.config import supabase_anon_key, supabase_url
from payra.models.demo_data import CurrentUser, ME_AVATAR


@dataclass
class SessionUser:
    id: str
    display_name: str
    username: str
    email: str
    about: str = "Hey — I'm on Payra"
    avatar_url: str = ME_AVATAR
    initials: str = "??"
    accent: str = "#7B61FF"
    status: str = "Online"

    def to_current_user(self) -> CurrentUser:
        return CurrentUser(
            id=self.id,
            display_name=self.display_name,
            username=self.username,
            email=self.email,
            about=self.about,
            avatar_url=self.avatar_url,
            initials=self.initials,
            accent=self.accent,
            status=self.status,
        )


_DATA_DIR = Path.home() / ".payra"
_USERS_FILE = _DATA_DIR / "local_users.json"
_SESSION_FILE = _DATA_DIR / "session.json"

_session: SessionUser | None = None


def supabase_ready() -> bool:
    url = supabase_url().strip()
    key = supabase_anon_key().strip()
    return bool(url and key and "YOUR_PROJECT" not in url and "your_anon" not in key.lower())


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def _load_users() -> dict[str, dict]:
    _ensure_data_dir()
    if not _USERS_FILE.exists():
        return {}
    try:
        raw = json.loads(_USERS_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_users(users: dict[str, dict]) -> None:
    _ensure_data_dir()
    _USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _initials_from_name(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip().lower()
    cleaned = "".join(c for c in local if c.isalnum() or c in "._")
    return cleaned or "user"


def _set_session(user: SessionUser | None) -> None:
    global _session
    _session = user
    _ensure_data_dir()
    if user is None:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
        return
    _SESSION_FILE.write_text(json.dumps(asdict(user), indent=2), encoding="utf-8")


def restore_session() -> SessionUser | None:
    """Load last session from disk (app start)."""
    global _session
    if _session is not None:
        return _session
    if not _SESSION_FILE.exists():
        return None
    try:
        data = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
        _session = SessionUser(**data)
        return _session
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def current_session() -> SessionUser | None:
    return _session if _session is not None else restore_session()


def register(
    display_name: str,
    email: str,
    password: str,
    *,
    username: str = "",
) -> SessionUser:
    """Create account. Raises ValueError on validation / duplicate."""
    name = display_name.strip()
    mail = email.strip().lower()
    uname = (username.strip().lstrip("@") or _username_from_email(mail)).lower()
    if len(name) < 2:
        raise ValueError("Enter your display name.")
    if "@" not in mail or "." not in mail.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if len(uname) < 3:
        raise ValueError("Username must be at least 3 characters.")

    # TODO: when supabase_ready(), call supabase.auth.sign_up(...)
    users = _load_users()
    for row in users.values():
        if row.get("email", "").lower() == mail:
            raise ValueError("An account with this email already exists.")
        if row.get("username", "").lower() == uname:
            raise ValueError("This username is already taken.")

    user_id = f"local-{secrets.token_hex(6)}"
    salt = secrets.token_hex(8)
    users[user_id] = {
        "id": user_id,
        "display_name": name,
        "username": uname,
        "email": mail,
        "about": "Hey — I'm on Payra",
        "avatar_url": ME_AVATAR,
        "initials": _initials_from_name(name),
        "accent": "#7B61FF",
        "status": "Online",
        "salt": salt,
        "password_hash": _hash_password(password, salt),
    }
    _save_users(users)
    session = SessionUser(
        id=user_id,
        display_name=name,
        username=uname,
        email=mail,
        initials=_initials_from_name(name),
    )
    _set_session(session)
    return session


def login(email: str, password: str) -> SessionUser:
    """Sign in. Raises ValueError on failure."""
    mail = email.strip().lower()
    if not mail or not password:
        raise ValueError("Enter email and password.")

    # TODO: when supabase_ready(), call supabase.auth.sign_in_with_password(...)
    users = _load_users()
    match = next((u for u in users.values() if u.get("email", "").lower() == mail), None)
    if match is None:
        raise ValueError("No account found for that email. Create one first.")
    expected = match.get("password_hash", "")
    salt = match.get("salt", "")
    if _hash_password(password, salt) != expected:
        raise ValueError("Incorrect password.")

    session = SessionUser(
        id=match["id"],
        display_name=match.get("display_name", "You"),
        username=match.get("username", "user"),
        email=match.get("email", mail),
        about=match.get("about", "Hey — I'm on Payra"),
        avatar_url=match.get("avatar_url", ME_AVATAR),
        initials=match.get("initials", "??"),
        accent=match.get("accent", "#7B61FF"),
        status=match.get("status", "Online"),
    )
    _set_session(session)
    return session


def logout() -> None:
    # TODO: when supabase_ready(), call supabase.auth.sign_out()
    _set_session(None)
