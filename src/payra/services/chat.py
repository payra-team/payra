"""1:1 and group conversations + messages via Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from payra.models.demo_data import ContactPerson, Conversation, Message, ME_AVATAR
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


def _fmt_time(value: str | None) -> str:
    if not value:
        return ""
    try:
        # Supabase returns ISO timestamps
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        local = dt.astimezone()
        now = datetime.now(local.tzinfo)
        if local.date() == now.date():
            return local.strftime("%-I:%M %p").replace(" 0", " ")
        return local.strftime("%b %-d")
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
        avatar_url=row.get("avatar_url") or "",
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


def load_messages(conversation_id: str, *, limit: int = 200) -> list[Message]:
    client = _require_client()
    me = _me_id()
    result = (
        client.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    out: list[Message] = []
    for row in result.data or []:
        content = row.get("content") or ""
        image_path = row.get("image_path")
        text = content if content else ("📷 Image" if image_path else "")
        out.append(
            Message(
                text=text,
                outgoing=str(row.get("sender_id")) == me,
                time=_fmt_time(row.get("created_at")),
                image_path=image_path,
                seen=True,
            )
        )
    return out


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
    member_contacts = [
        _profile_to_contact(profiles[str(m["user_id"])])
        for m in members
        if str(m["user_id"]) in profiles
    ]

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
            name = peer.name
            about = peer.role or ""
            avatar_url = peer.avatar_url
            accent = peer.accent
            initials = peer.initials
            online = True

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
        avatar_url=avatar_url or ME_AVATAR,
        messages=[],
        media_urls=media_urls,
        members=member_contacts if is_group else [],
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

    # Last message per conversation (simple approach)
    last_by_conv: dict[str, dict] = {}
    msgs = (
        client.table("messages")
        .select("*")
        .in_("conversation_id", conv_ids)
        .order("created_at", desc=True)
        .limit(max(50, len(conv_ids) * 3))
        .execute()
    )
    for row in msgs.data or []:
        cid = str(row["conversation_id"])
        if cid not in last_by_conv:
            last_by_conv[cid] = row

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


def get_conversation(conversation_id: str) -> Conversation | None:
    for conv in list_conversations():
        if conv.id == conversation_id:
            conv.messages = load_messages(conversation_id)
            # collect media from messages
            media = [m.image_path for m in conv.messages if m.image_path]
            conv.media_urls = media[-24:]
            return conv
    return None


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
    return Message(
        text=text if text else ("📷 Image" if image_path else ""),
        outgoing=True,
        time=_fmt_time(row.get("created_at")) or "Now",
        image_path=image_path,
        seen=False,
    )


def start_direct(other_user_id: str, first_message: str = "") -> Conversation:
    client = _require_client()
    result = client.rpc(
        "get_or_create_direct_conversation",
        {"other_user_id": other_user_id},
    ).execute()
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
    client = _require_client()
    result = client.rpc(
        "create_group_conversation",
        {"group_title": title, "member_ids": member_ids},
    ).execute()
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


def add_members(conversation_id: str, user_ids: list[str]) -> None:
    client = _require_client()
    rows = [
        {"conversation_id": conversation_id, "user_id": uid, "role": "member"}
        for uid in user_ids
    ]
    if rows:
        client.table("conversation_members").insert(rows).execute()
