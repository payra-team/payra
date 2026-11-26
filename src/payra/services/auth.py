"""Auth: register, login, session — Supabase when configured, else local JSON."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from payra.models.demo_data import CurrentUser, ME_AVATAR
from payra.services import supabase_client as sb


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
    return sb.supabase_ready()


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


def _set_local_session(user: SessionUser | None) -> None:
    global _session
    _session = user
    _ensure_data_dir()
    if user is None:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
        return
    _SESSION_FILE.write_text(json.dumps(asdict(user), indent=2), encoding="utf-8")


def _auth_error_message(exc: BaseException) -> str:
    text = str(exc).strip() or "Authentication failed."
    lower = text.lower()
    if "email not confirmed" in lower or ("confirm" in lower and "email" in lower):
        return (
            "Confirm your email before signing in "
            "(or disable Confirm email in Supabase Auth settings)."
        )
    if "invalid login" in lower or "invalid credentials" in lower:
        return "Incorrect email or password."
    if "already registered" in lower or "user already" in lower:
        return "An account with this email already exists."
    if "password" in lower and ("least" in lower or "short" in lower or "6" in lower):
        return "Password must be at least 6 characters."
    return text


def _profile_to_session(row: dict) -> SessionUser:
    return SessionUser(
        id=str(row["id"]),
        display_name=row.get("display_name") or "You",
        username=row.get("username") or "user",
        email=row.get("email") or "",
        about=row.get("about") or "Hey — I'm on Payra",
        avatar_url=row.get("avatar_url") or ME_AVATAR,
        initials=row.get("initials") or "??",
        accent=row.get("accent") or "#7B61FF",
        status=row.get("status") or "Online",
    )


def _fetch_profile(user_id: str) -> SessionUser:
    client = sb.get_client()
    if client is None:
        raise ValueError("Supabase is not configured.")
    result = (
        client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        user_resp = client.auth.get_user()
        auth_user = getattr(user_resp, "user", None) or user_resp
        email = getattr(auth_user, "email", "") or ""
        meta = getattr(auth_user, "user_metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        name = meta.get("display_name") or _username_from_email(email)
        uname = meta.get("username") or _username_from_email(email)
        return SessionUser(
            id=user_id,
            display_name=name,
            username=uname,
            email=email,
            initials=_initials_from_name(name),
        )
    return _profile_to_session(rows[0])


def _session_from_auth_response(response: Any) -> SessionUser:
    """Build a SessionUser from sign-up / sign-in. Sign-up may omit session."""
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if user is None:
        raise ValueError("Could not create account. Try a different email.")
    if session is not None:
        sb.save_tokens(session.access_token, session.refresh_token)
        try:
            return _fetch_profile(str(user.id))
        except Exception:
            pass
    meta = getattr(user, "user_metadata", None) or {}
    if not isinstance(meta, dict):
        meta = {}
    name = meta.get("display_name") or _username_from_email(getattr(user, "email", "") or "")
    uname = meta.get("username") or _username_from_email(getattr(user, "email", "") or "")
    return SessionUser(
        id=str(user.id),
        display_name=name,
        username=uname,
        email=(getattr(user, "email", None) or ""),
        initials=_initials_from_name(name),
    )


def restore_session() -> SessionUser | None:
    """Load last session (app start)."""
    global _session
    if _session is not None:
        return _session

    if supabase_ready():
        client = sb.get_client()
        if client is None:
            return None
        try:
            tokens = sb.load_tokens()
            if not tokens:
                return None
            client.auth.set_session(tokens["access_token"], tokens["refresh_token"])
            user_resp = client.auth.get_user()
            user = getattr(user_resp, "user", None)
            if user is None:
                sb.clear_tokens()
                return None
            current = client.auth.get_session()
            if current and getattr(current, "access_token", None):
                sb.save_tokens(current.access_token, current.refresh_token)
            _session = _fetch_profile(str(user.id))
            return _session
        except Exception:
            sb.clear_tokens()
            return None

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
    global _session
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

    if supabase_ready():
        client = sb.get_client()
        if client is None:
            raise ValueError("Supabase is not configured.")
        try:
            response = client.auth.sign_up(
                {
                    "email": mail,
                    "password": password,
                    "options": {
                        "data": {
                            "display_name": name,
                            "username": uname,
                        }
                    },
                }
            )
            session_user = _session_from_auth_response(response)
            session_user.display_name = name
            session_user.username = uname
            session_user.email = mail
            session_user.initials = _initials_from_name(name)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(_auth_error_message(exc)) from exc
        # Registration never leaves you signed in — UI sends user to login.
        try:
            client.auth.sign_out()
        except Exception:
            pass
        sb.clear_tokens()
        sb.reset_client()
        _session = None
        return session_user

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
    # Match Supabase flow: account created → sign in separately
    _set_local_session(None)
    return session


def login(email: str, password: str) -> SessionUser:
    """Sign in. Raises ValueError on failure."""
    global _session
    mail = email.strip().lower()
    if not mail or not password:
        raise ValueError("Enter email and password.")

    if supabase_ready():
        client = sb.get_client()
        if client is None:
            raise ValueError("Supabase is not configured.")
        try:
            response = client.auth.sign_in_with_password(
                {"email": mail, "password": password}
            )
            session_user = _session_from_auth_response(response)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(_auth_error_message(exc)) from exc
        _session = session_user
        return session_user

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
    _set_local_session(session)
    return session


def logout() -> None:
    global _session
    if supabase_ready():
        client = sb.get_client()
        try:
            if client is not None:
                client.auth.sign_out()
        except Exception:
            pass
        sb.clear_tokens()
        sb.reset_client()
        _session = None
        return
    _set_local_session(None)


def reset_password(email: str, new_password: str) -> None:
    """MVP reset: email + new password (no email verification)."""
    mail = email.strip().lower()
    if "@" not in mail or "." not in mail.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    if supabase_ready():
        client = sb.get_client()
        if client is None:
            raise ValueError("Supabase is not configured.")
        try:
            client.rpc(
                "reset_password_mvp",
                {"user_email": mail, "new_password": new_password},
            ).execute()
        except Exception as exc:
            raise ValueError(_auth_error_message(exc)) from exc
        return

    users = _load_users()
    match_id = next(
        (uid for uid, u in users.items() if u.get("email", "").lower() == mail),
        None,
    )
    if match_id is None:
        raise ValueError("No account found for that email.")
    salt = secrets.token_hex(8)
    users[match_id]["salt"] = salt
    users[match_id]["password_hash"] = _hash_password(new_password, salt)
    _save_users(users)
