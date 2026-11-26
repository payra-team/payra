#!/usr/bin/env python3
"""Headless smoke test for Payra ↔ Supabase (auth, chat, storage).

Usage:
  PYTHONPATH=src .venv/bin/python scripts/smoke_test_supabase.py
  PYTHONPATH=src .venv/bin/python scripts/smoke_test_supabase.py --state /tmp/payra_smoke.json
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from payra.services import auth as auth_service  # noqa: E402
from payra.services import chat as chat_service  # noqa: E402
from payra.services import storage as storage_service  # noqa: E402
from payra.services import supabase_client as sb  # noqa: E402


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _save_state(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def create_users(state_path: Path) -> int:
    if not auth_service.supabase_ready():
        _fail("supabase_ready() is False — check .env")
    client = sb.get_client()
    if client is None:
        _fail("get_client() returned None")

    stamp = uuid.uuid4().hex[:8]
    password = "PayraTest1!"
    users = []
    for label, name in (("a", "Payra Alpha"), ("b", "Payra Beta")):
        # example.com is rejected by GoTrue; gmail local-part is unique per run.
        email = f"payra.{label}.{stamp}@gmail.com"
        username = f"{label}{stamp}"
        print(f"SIGNUP {email}")
        try:
            resp = client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {"display_name": name, "username": username}
                    },
                }
            )
        except Exception as exc:
            _fail(f"sign_up {label}: {exc}")
        user = getattr(resp, "user", None)
        session = getattr(resp, "session", None)
        if user is None:
            _fail(f"sign_up {label}: no user returned")
        users.append(
            {
                "label": label,
                "email": email,
                "password": password,
                "id": str(user.id),
                "username": username,
                "name": name,
                "has_session": session is not None,
            }
        )
        print(f"CREATED {label} id={user.id} session={session is not None}")
        try:
            client.auth.sign_out()
        except Exception:
            pass
        sb.clear_tokens()
        sb.reset_client()
        client = sb.get_client()

    needs_confirm = any(not u["has_session"] for u in users)
    state = {
        "stamp": stamp,
        "password": password,
        "users": users,
        "needs_confirm": needs_confirm,
    }
    _save_state(state_path, state)
    print(f"STATE {state_path}")
    if needs_confirm:
        print("NEED_CONFIRM")
        for u in users:
            print(f"CONFIRM_EMAIL {u['email']}")
        return 2
    _ok("users created with live sessions")
    return 0


def run_flow(state_path: Path) -> int:
    state = _load_state(state_path)
    users = {u["label"]: u for u in state["users"]}
    password = state["password"]
    a = users["a"]
    b = users["b"]

    # Login B
    try:
        auth_service.login(b["email"], password)
    except ValueError as exc:
        _fail(f"login B: {exc}")
    _ok("login B")

    conv = chat_service.start_direct(a["id"], "Hello from Beta")
    _ok(f"conversation {conv.id}")
    msgs, _has_more = chat_service.load_messages(conv.id)
    if not msgs or "Hello from Beta" not in msgs[-1].text:
        _fail(f"unexpected messages: {msgs!r}")
    _ok("text message")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(_png_bytes())
        path = tmp.name
    url = storage_service.upload_chat_image(path)
    if not url.startswith("http"):
        _fail(f"bad url {url}")
    chat_service.send_message(conv.id, "pic", image_path=url)
    _ok("image message")

    auth_service.logout()
    auth_service.login(a["email"], password)
    _ok("login A")

    directory = chat_service.list_directory()
    if not any(p.id == b["id"] for p in directory):
        _fail("directory missing B")
    _ok("directory")

    convs = chat_service.list_conversations()
    if not any(c.id == conv.id for c in convs):
        _fail("A missing conversation")
    loaded = chat_service.get_conversation(conv.id)
    if loaded is None or len(loaded.messages) < 2:
        _fail("A missing messages")
    _ok(f"A sees {len(loaded.messages)} messages")

    chat_service.set_starred(conv.id, True)
    chat_service.list_conversations()
    if conv.id not in chat_service.starred_ids():
        _fail("star failed")
    _ok("starred")

    # Groups + roles + add members (any member) + admin settings
    stamp = state.get("stamp") or uuid.uuid4().hex[:8]
    group = chat_service.create_group(f"Smoke Group {stamp}", [b["id"]])
    if not group.is_group:
        _fail("create_group did not return a group")
    if not any(m.id == b["id"] for m in group.members):
        _fail("create_group missing member B")
    if group.my_role != "admin":
        _fail(f"creator my_role expected admin, got {group.my_role!r}")
    roles = {m.id: m.member_role for m in group.members}
    if roles.get(a["id"]) != "admin":
        _fail(f"A role expected admin, got {roles}")
    if roles.get(b["id"]) != "member":
        _fail(f"B role expected member, got {roles}")
    _ok(f"group {group.id} roles ok ({len(group.members)} members)")

    before = {m.id for m in group.members}
    reloaded, added_n = chat_service.add_members(group.id, [b["id"]])
    after = {m.id for m in reloaded.members}
    if after != before or added_n != 0:
        _fail(f"duplicate add changed members: {before} -> {after} added={added_n}")
    _ok("add_members idempotent for existing member")

    # Non-admin member B can still add people (membership required, not admin).
    auth_service.logout()
    auth_service.login(b["email"], password)
    _ok("login B for member add + admin settings check")
    try:
        _conv, _n = chat_service.add_members(group.id, [a["id"]])
    except Exception as exc:
        _fail(f"member B should be allowed to add: {exc}")
    _ok("member B can call add_members")

    try:
        chat_service.set_member_role(group.id, a["id"], "member")
        _fail("non-admin B was allowed to change roles")
    except Exception as exc:
        msg = str(exc).lower()
        if "admin" not in msg:
            _fail(f"unexpected role error: {exc}")
        _ok("non-admin role change rejected")

    # Sole-admin leave must fail while A is the only admin.
    auth_service.logout()
    auth_service.login(a["email"], password)
    try:
        chat_service.remove_member(group.id, a["id"])
        _fail("sole admin A was allowed to leave")
    except Exception as exc:
        msg = str(exc).lower()
        if "admin" not in msg:
            _fail(f"unexpected leave error: {exc}")
        _ok("sole-admin leave rejected")

    promoted = chat_service.set_member_role(group.id, b["id"], "admin")
    b_role = next((m.member_role for m in promoted.members if m.id == b["id"]), "")
    if b_role != "admin":
        _fail(f"promote B failed, role={b_role!r}")
    _ok("admin A promoted B")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(_png_bytes())
        avatar_path = tmp.name
    url = storage_service.upload_group_avatar(group.id, avatar_path)
    if not url.startswith("http"):
        _fail(f"bad group avatar url {url}")
    with_avatar = chat_service.set_group_avatar(group.id, url)
    if not with_avatar.avatar_url:
        _fail("group avatar_url empty after set")
    _ok("group avatar updated")

    auth_service.logout()
    state["conversation_id"] = conv.id
    state["group_id"] = group.id
    _save_state(state_path, state)
    _ok("smoke test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state",
        default=str(Path.home() / ".payra" / "smoke_state.json"),
    )
    parser.add_argument(
        "--phase",
        choices=("create", "test", "all"),
        default="all",
    )
    args = parser.parse_args()
    state_path = Path(args.state)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    if args.phase in ("create", "all"):
        code = create_users(state_path)
        if code == 2 and args.phase == "create":
            return 2
        if code == 2 and args.phase == "all":
            print(
                "Email confirmation required. Confirm users in Supabase then run:\n"
                f"  PYTHONPATH=src .venv/bin/python scripts/smoke_test_supabase.py --phase test --state {state_path}"
            )
            return 2
        if code != 0:
            return code

    if args.phase in ("test", "all"):
        if not state_path.exists():
            _fail(f"missing state file {state_path}")
        return run_flow(state_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        _fail(repr(exc))
