"""1:1 and group conversations + messages via Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from payra.models.demo_data import ContactPerson, Conversation, Message, ME_AVATAR
from payra.resources import normalize_avatar_url
from payra.services import supabase_client as sb
from payra.services.auth import current_session


def _require_client() -> Any:
    client = sb.get_client()
    if client is None:
        raise ValueError("Supabase is not configured.")
    return client


def _me_id() -> str:
    session = current_session()
    if session is None:
        raise ValueError("Not signed in.")
    return session.id


def _rpc_error_message(exc: BaseException) -> str:
    """Map PostgREST / Postgres exceptions to short user-facing copy."""
    text = str(exc).strip() or "Something went wrong."
    # Prefer nested JSON-ish message fields when present.
    lower = text.lower()
    for key in ("'message':", '"message":'):
        if key in text:
            try:
                start = text.index(key) + len(key)
                chunk = text[start:].lstrip(" '\"")
                end = min(
                    (i for i in (chunk.find("',"), chunk.find('",'), chunk.find("' }"), chunk.find('" }')) if i >= 0),
                    default=-1,
                )
                if end > 0:
                    text = chunk[:end].strip()
                    lower = text.lower()
            except Exception:
                pass
            break

    if "last admin" in lower:
        return "Promote another admin before leaving or demoting the last admin."
    if "only group admins can change roles" in lower:
        return "Only group admins can change member roles."
    if "only group admins can remove" in lower:
        return "Only group admins can remove other members."
    if "only group members can add" in lower:
        return "You must be in the group to add people."
    if "only group members can update the group photo" in lower:
        return "You must be in the group to update the photo."
    if "not a group conversation" in lower:
        return "That chat isn’t a group."
    if "not a member" in lower:
        return "That person isn’t in this group."
    if "not authenticated" in lower:
        return "Sign in again and retry."
    if "conversation not found" in lower:
        return "This group is no longer available."
    if "role must be" in lower:
        return "Role must be admin or member."
    return text


def _rpc_call(name: str, params: dict[str, Any]) -> Any:
    client = _require_client()
    try:
        return client.rpc(name, params).execute()
    except Exception as exc:  # noqa: BLE001 — normalize for UI
        raise ValueError(_rpc_error_message(exc)) from exc


def _fmt_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        # Supabase returns ISO timestamps
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        local = dt.astimezone()
        now = datetime.now(local.tzinfo)
        if local.date() == now.date():
            hour12 = local.hour % 12 or 12
            ampm = "AM" if local.hour < 12 else "PM"
            return f"{hour12}:{local.minute:02d} {ampm}"
        return f"{local.strftime('%b')} {local.day}"
    except Exception:
        return value[:16]


def _initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "??"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _profile_to_contact(row: dict) -> ContactPerson:
    return ContactPerson(
        id=str(row["id"]),
        name=row.get("display_name") or "User",
        initials=row.get("initials") or _initials(row.get("display_name") or "U"),
        accent=row.get("accent") or "#7B61FF",
        avatar_url=normalize_avatar_url(row.get("avatar_url")),
        role=row.get("status") or "Member",
        email=row.get("email") or "",
        username=row.get("username") or "",
    )


def list_directory() -> list[ContactPerson]:
    """All profiles except the current user."""
    client = _require_client()
    me = _me_id()
    result = (
        client.table("profiles")
        .select("*")
        .neq("id", me)
        .order("display_name")
        .execute()
    )
    return [_profile_to_contact(row) for row in (result.data or [])]


MESSAGE_PAGE_SIZE = 40


def row_to_message(row: dict, me: str | None = None) -> Message:
    """Convert a Supabase `messages` row dict into a UI Message."""
    uid = me if me is not None else _me_id()
    content = row.get("content") or ""
    image_path = row.get("image_path")
    text = content if content else ("📷 Image" if image_path else "")
    created = row.get("created_at")
    return Message(
        text=text,
        outgoing=str(row.get("sender_id")) == uid,
        time=_fmt_time(created),
        image_path=image_path,
        seen=True,
        created_at=str(created) if created else None,
        id=str(row.get("id") or ""),
    )


def _row_to_message(row: dict, me: str) -> Message:
    return row_to_message(row, me)


def load_messages(
    conversation_id: str,
    *,
    limit: int = MESSAGE_PAGE_SIZE,
    before: str | None = None,
) -> tuple[list[Message], bool]:
    """
    Load one page of messages (newest page by default).

    Returns (messages_oldest_first, has_more_older).
    Pass `before` (ISO created_at) to fetch the next older page.
    """
    client = _require_client()
    me = _me_id()
    # Fetch newest-first so pagination with `before` is natural, then reverse.
    query = (
        client.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(limit + 1)
    )
    if before:
        query = query.lt("created_at", before)
    result = query.execute()
    rows = list(result.data or [])
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    messages = [_row_to_message(row, me) for row in reversed(rows)]
    return messages, has_more


def _membership_contact(profile: dict, membership: dict) -> ContactPerson:
    contact = _profile_to_contact(profile)
    member_role = str(membership.get("role") or "member").lower()
    if member_role not in {"admin", "member"}:
        member_role = "member"
    contact.member_role = member_role
    contact.role = "Admin" if member_role == "admin" else "Member"
    return contact


def _build_conversation(
    conv: dict,
    *,
    members: list[dict],
    profiles: dict[str, dict],
    last_message: dict | None,
    my_membership: dict | None,
) -> Conversation:
    me = _me_id()
    is_group = conv.get("type") == "group"
    # Admins first, then alphabetical by display name.
    sorted_members = sorted(
        members,
        key=lambda m: (
            0 if str(m.get("role") or "") == "admin" else 1,
            str((profiles.get(str(m["user_id"])) or {}).get("display_name") or "").lower(),
        ),
    )
    member_contacts = [
        _membership_contact(profiles[str(m["user_id"])], m)
        for m in sorted_members
        if str(m["user_id"]) in profiles
    ]
    my_role = str((my_membership or {}).get("role") or "")

    if is_group:
        name = conv.get("title") or "Group"
        about = conv.get("about") or f"{len(member_contacts)} members"
        avatar_url = conv.get("avatar_url") or ""
        accent = conv.get("accent") or "#7B61FF"
        initials = _initials(name)
        online = False
    else:
        peer = next((c for c in member_contacts if c.id != me), None)
        if peer is None:
            name = "Direct chat"
            about = ""
            avatar_url = ""
            accent = "#7B61FF"
            initials = "??"
            online = False
        else:
            # DMs: keep profile status/job as about, not membership role label.
            peer_profile = profiles.get(peer.id) or {}
            name = peer.name
            about = peer_profile.get("status") or peer_profile.get("about") or ""
            avatar_url = peer.avatar_url
            accent = peer.accent
            initials = peer.initials
            online = True
            member_contacts = []
            my_role = ""

    preview = "Start of conversation"
    time_label = _fmt_time(conv.get("updated_at") or conv.get("created_at"))
    media_urls: list[str] = []
    if last_message:
        content = last_message.get("content") or ""
        image_path = last_message.get("image_path")
        if image_path:
            media_urls.append(image_path)
            preview = content or "📷 Image"
        else:
            preview = content or preview
        time_label = _fmt_time(last_message.get("created_at")) or time_label

    unread = 0
    last_read = (my_membership or {}).get("last_read_at")
    if last_message and str(last_message.get("sender_id")) != me:
        if not last_read:
            unread = 1
        else:
            try:
                msg_t = datetime.fromisoformat(
                    str(last_message["created_at"]).replace("Z", "+00:00")
                )
                read_t = datetime.fromisoformat(str(last_read).replace("Z", "+00:00"))
                if msg_t > read_t:
                    unread = 1
            except Exception:
                unread = 1

    starred = bool((my_membership or {}).get("starred"))

    return Conversation(
        id=str(conv["id"]),
        name=name,
        preview=preview,
        time=time_label,
        unread=unread,
        online=online,
        is_group=is_group,
        starred=bool((my_membership or {}).get("starred")),
        about=about,
        initials=initials,
        accent=accent,
        avatar_url=normalize_avatar_url(avatar_url),
        messages=[],
        media_urls=media_urls,
        members=member_contacts if is_group else [],
        my_role=my_role if is_group else "",
    )


# Attach starred dynamically — Conversation dataclass has no starred field.
# We keep a module-level cache for filters.
_starred_ids: set[str] = set()


def starred_ids() -> set[str]:
    return set(_starred_ids)


def list_conversations() -> list[Conversation]:
    """Conversations for the current user, newest activity first."""
    global _starred_ids
    client = _require_client()
    me = _me_id()

    mine = (
        client.table("conversation_members")
        .select("*")
        .eq("user_id", me)
        .execute()
    )
    memberships = {str(row["conversation_id"]): row for row in (mine.data or [])}
    if not memberships:
        _starred_ids = set()
        return []

    conv_ids = list(memberships.keys())
    convs = (
        client.table("conversations")
        .select("*")
        .in_("id", conv_ids)
        .order("updated_at", desc=True)
        .execute()
    )

    all_members = (
        client.table("conversation_members")
        .select("*")
        .in_("conversation_id", conv_ids)
        .execute()
    )
    members_by_conv: dict[str, list[dict]] = {}
    profile_ids: set[str] = set()
    for row in all_members.data or []:
        cid = str(row["conversation_id"])
        members_by_conv.setdefault(cid, []).append(row)
        profile_ids.add(str(row["user_id"]))

    profiles: dict[str, dict] = {}
    if profile_ids:
        pref = (
            client.table("profiles")
            .select("*")
            .in_("id", list(profile_ids))
            .execute()
        )
        profiles = {str(r["id"]): r for r in (pref.data or [])}

    # Last message per conversation (single batch, with fallback for missing convs)
    last_by_conv: dict[str, dict] = {}
    fetch_limit = max(50, len(conv_ids) * 3)
    msgs = (
        client.table("messages")
        .select("*")
        .in_("conversation_id", conv_ids)
        .order("created_at", desc=True)
        .limit(fetch_limit)
        .execute()
    )
    msg_rows = msgs.data or []
    for row in msg_rows:
        cid = str(row["conversation_id"])
        if cid not in last_by_conv:
            last_by_conv[cid] = row

    if len(msg_rows) >= fetch_limit:
        for cid in conv_ids:
            if cid not in last_by_conv:
                one = (
                    client.table("messages")
                    .select("*")
                    .eq("conversation_id", cid)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if one.data:
                    last_by_conv[cid] = one.data[0]

    _starred_ids = {
        cid for cid, m in memberships.items() if m.get("starred")
    }

    out: list[Conversation] = []
    for conv in convs.data or []:
        cid = str(conv["id"])
        built = _build_conversation(
            conv,
            members=members_by_conv.get(cid, []),
            profiles=profiles,
            last_message=last_by_conv.get(cid),
            my_membership=memberships.get(cid),
        )
        built.messages = []  # lazy-load on open
        out.append(built)
    return out


def get_conversation(
    conversation_id: str,
    *,
    message_limit: int = MESSAGE_PAGE_SIZE,
) -> Conversation | None:
    for conv in list_conversations():
        if conv.id == conversation_id:
            messages, has_more = load_messages(
                conversation_id, limit=message_limit
            )
            conv.messages = messages
            conv.has_more_messages = has_more
            media = [m.image_path for m in conv.messages if m.image_path]
            conv.media_urls = media[-24:]
            return conv
    return None


def load_older_messages(
    conversation_id: str,
    *,
    before: str,
    limit: int = MESSAGE_PAGE_SIZE,
) -> tuple[list[Message], bool]:
    """Fetch the next older page for infinite scroll."""
    return load_messages(conversation_id, limit=limit, before=before)


def send_message(
    conversation_id: str,
    content: str = "",
    *,
    image_path: str | None = None,
) -> Message:
    client = _require_client()
    me = _me_id()
    text = (content or "").strip()
    if not text and not image_path:
        raise ValueError("Message is empty.")
    result = (
        client.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "sender_id": me,
                "content": text,
                "image_path": image_path,
            }
        )
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise ValueError("Failed to send message.")
    row = rows[0]
    mark_read(conversation_id)
    created = row.get("created_at")
    return Message(
        text=text if text else ("📷 Image" if image_path else ""),
        outgoing=True,
        time=_fmt_time(created) or "Now",
        image_path=image_path,
        seen=False,
        created_at=str(created) if created else None,
        id=str(row.get("id") or ""),
    )


def start_direct(other_user_id: str, first_message: str = "") -> Conversation:
    result = _rpc_call(
        "get_or_create_direct_conversation",
        {"other_user_id": other_user_id},
    )
    conversation_id = result.data
    if isinstance(conversation_id, list):
        conversation_id = conversation_id[0] if conversation_id else None
    if not conversation_id:
        raise ValueError("Could not start conversation.")
    conversation_id = str(conversation_id)
    if first_message.strip():
        send_message(conversation_id, first_message.strip())
    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Conversation created but could not be loaded.")
    return conv


def create_group(title: str, member_ids: list[str]) -> Conversation:
    result = _rpc_call(
        "create_group_conversation",
        {"group_title": title, "member_ids": member_ids},
    )
    conversation_id = result.data
    if isinstance(conversation_id, list):
        conversation_id = conversation_id[0] if conversation_id else None
    if not conversation_id:
        raise ValueError("Could not create group.")
    conv = get_conversation(str(conversation_id))
    if conv is None:
        raise ValueError("Group created but could not be loaded.")
    return conv


def set_starred(conversation_id: str, starred: bool) -> None:
    client = _require_client()
    me = _me_id()
    client.table("conversation_members").update({"starred": starred}).eq(
        "conversation_id", conversation_id
    ).eq("user_id", me).execute()
    if starred:
        _starred_ids.add(conversation_id)
    else:
        _starred_ids.discard(conversation_id)


def mark_read(conversation_id: str) -> None:
    client = _require_client()
    me = _me_id()
    now = datetime.now(timezone.utc).isoformat()
    client.table("conversation_members").update({"last_read_at": now}).eq(
        "conversation_id", conversation_id
    ).eq("user_id", me).execute()


def add_members(conversation_id: str, user_ids: list[str]) -> tuple[Conversation, int]:
    """Add people to a group. Any current member may add (enforced by RPC).

    Returns (refreshed conversation, rows actually inserted).
    """
    unique_ids = list(dict.fromkeys(uid for uid in user_ids if uid))
    if not unique_ids:
        conv = get_conversation(conversation_id)
        if conv is None:
            raise ValueError("Conversation not found.")
        return conv, 0

    result = _rpc_call(
        "add_group_members",
        {"p_conversation_id": conversation_id, "p_member_ids": unique_ids},
    )
    added = result.data
    if isinstance(added, list):
        added = added[0] if added else 0
    try:
        added_n = int(added or 0)
    except (TypeError, ValueError):
        added_n = 0

    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Members added but conversation could not be reloaded.")
    return conv, added_n


def set_member_role(conversation_id: str, user_id: str, role: str) -> Conversation:
    """Promote/demote a member. Admin-only (enforced by RPC)."""
    normalized = (role or "").strip().lower()
    if normalized not in {"admin", "member"}:
        raise ValueError("Role must be admin or member.")
    _rpc_call(
        "set_group_member_role",
        {
            "p_conversation_id": conversation_id,
            "p_user_id": user_id,
            "p_role": normalized,
        },
    )
    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Role updated but conversation could not be reloaded.")
    return conv


def remove_member(conversation_id: str, user_id: str) -> Conversation | None:
    """Remove a member (admin) or leave the group (self). Returns None if you left."""
    me = _me_id()
    _rpc_call(
        "remove_group_member",
        {"p_conversation_id": conversation_id, "p_user_id": user_id},
    )
    if user_id == me:
        return None
    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Member removed but conversation could not be reloaded.")
    return conv


def set_group_avatar(conversation_id: str, avatar_url: str) -> Conversation:
    """Update group profile photo URL. Any member may update."""
    _rpc_call(
        "set_group_avatar",
        {"p_conversation_id": conversation_id, "p_avatar_url": avatar_url or ""},
    )
    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Avatar updated but conversation could not be reloaded.")
    return conv


def rename_group(conversation_id: str, title: str) -> Conversation:
    """Rename a group conversation and return the refreshed Conversation."""
    new_title = (title or "").strip()
    if len(new_title) < 2:
        raise ValueError("Enter a group name (at least 2 characters).")
    client = _require_client()
    try:
        result = (
            client.table("conversations")
            .update(
                {
                    "title": new_title,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversation_id)
            .eq("type", "group")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise ValueError(_rpc_error_message(exc)) from exc
    if not (result.data or []):
        raise ValueError("Could not rename group.")
    conv = get_conversation(conversation_id)
    if conv is None:
        raise ValueError("Group renamed but conversation could not be reloaded.")
    return conv


def is_sole_admin(conversation: Conversation, user_id: str | None = None) -> bool:
    """True when user is the only admin in the group."""
    if not conversation.is_group:
        return False
    uid = user_id or ""
    admins = [m for m in conversation.members if (m.member_role or "").lower() == "admin"]
    if not admins and conversation.my_role == "admin":
        return True
    return len(admins) == 1 and any(m.id == uid for m in admins)
