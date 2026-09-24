"""Mock conversations for UI development (before Supabase)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Demo network avatars (pravatar) — cached on disk after first load
ME_AVATAR = "https://i.pravatar.cc/150?img=12"


@dataclass
class Message:
    text: str
    outgoing: bool
    time: str
    image_path: str | None = None
    seen: bool = True  # outgoing: ✓✓ when True, ✓ when False


@dataclass
class ContactPerson:
    id: str
    name: str
    initials: str
    accent: str = "#7B61FF"
    avatar_url: str = ""
    role: str = "Member"
    email: str = ""
    username: str = ""


@dataclass
class CurrentUser:
    """Logged-in Payra user (demo until Supabase Auth)."""

    id: str = "me"
    display_name: str = "Mosharof Khan"
    username: str = "mosharof"
    email: str = "mosharof@payra.app"
    about: str = "SDP-2 · Building Payra desktop chat with the team"
    avatar_url: str = ME_AVATAR
    initials: str = "MK"
    accent: str = "#7B61FF"
    status: str = "Online"


@dataclass
class Conversation:
    id: str
    name: str
    preview: str
    time: str
    unread: int = 0
    online: bool = False
    is_group: bool = False
    about: str = ""
    initials: str = ""
    accent: str = "#7B61FF"
    avatar_url: str = ""
    messages: list[Message] = field(default_factory=list)
    media_urls: list[str] = field(default_factory=list)
    members: list[ContactPerson] = field(default_factory=list)


def current_user() -> CurrentUser:
    return CurrentUser()


def demo_directory() -> list[ContactPerson]:
    """People available to chat with / add to groups (demo)."""
    return [
        ContactPerson("u1", "Alex Johnson", "AJ", "#7B61FF", "https://i.pravatar.cc/150?img=33", "Designer", "alex@payra.app", "alexj"),
        ContactPerson("u2", "Jane Cooper", "JC", "#5B8CFF", "https://i.pravatar.cc/150?img=5", "Frontend", "jane@payra.app", "janecooper"),
        ContactPerson("u3", "Sam Wilson", "SW", "#44C4A1", "https://i.pravatar.cc/150?img=15", "Backend", "sam@payra.app", "samw"),
        ContactPerson("u4", "Sarah Lee", "SL", "#FF7B9C", "https://i.pravatar.cc/150?img=9", "Design", "sarah@payra.app", "sarahlee"),
        ContactPerson("u5", "Omar Khan", "OK", "#F5A623", "https://i.pravatar.cc/150?img=11", "QA", "omar@payra.app", "omark"),
        ContactPerson("u6", "Mia Chen", "MC", "#9B7BFF", "https://i.pravatar.cc/150?img=20", "PM", "mia@payra.app", "miachen"),
        ContactPerson("u7", "Rahul Das", "RD", "#2EC4B6", "https://i.pravatar.cc/150?img=52", "Mobile", "rahul@payra.app", "rahuld"),
        ContactPerson("u8", "Nora Ali", "NA", "#E85D75", "https://i.pravatar.cc/150?img=25", "Content", "nora@payra.app", "noraali"),
        ContactPerson("u9", "Priya Sen", "PS", "#6C63FF", "https://i.pravatar.cc/150?img=32", "Student", "priya@university.edu", "priyasen"),
        ContactPerson("u10", "Hasan Ahmed", "HA", "#00B894", "https://i.pravatar.cc/150?img=14", "Student", "hasan@university.edu", "hasanahmed"),
    ]


def _media(seed_start: int, count: int = 9) -> list[str]:
    return [f"https://picsum.photos/seed/payra{seed_start + i}/200" for i in range(count)]


def demo_conversations() -> list[Conversation]:
    people = {p.id: p for p in demo_directory()}
    return [
        Conversation(
            id="1",
            name="Alex Johnson",
            preview="That sounds amazing! Can't wait…",
            time="10:42 AM",
            unread=2,
            online=True,
            about="Product designer. Loves coffee and clean UI.",
            initials="AJ",
            accent="#7B61FF",
            avatar_url="https://i.pravatar.cc/150?img=33",
            media_urls=_media(10, 6),
            members=[],
            messages=[
                Message("Hey! Are we still on for the design review?", False, "10:30 AM"),
                Message(
                    "Yes — 3pm works for me. I'll share the Figma link.",
                    True,
                    "10:32 AM",
                    seen=True,
                ),
                Message("Perfect. Also drop the latest screenshots when you can.", False, "10:35 AM"),
                Message("That sounds amazing! Can't wait to see it.", False, "10:42 AM"),
            ],
        ),
        Conversation(
            id="2",
            name="Design Team",
            preview="Sarah: Updated the color tokens",
            time="Yesterday",
            unread=5,
            is_group=True,
            about="SDP-2 Payra design squad · 5 members",
            initials="DT",
            accent="#9B7BFF",
            avatar_url="https://i.pravatar.cc/150?img=47",
            media_urls=_media(40, 9),
            members=[
                people["u1"],
                people["u2"],
                people["u4"],
                people["u6"],
                ContactPerson("me", "You", "YO", "#7B61FF", ME_AVATAR, "Admin"),
            ],
            messages=[
                Message("Updated the color tokens for Payra.", False, "Yesterday"),
                Message("Nice — matching the soft purple shell.", True, "Yesterday", seen=True),
            ],
        ),
        Conversation(
            id="3",
            name="Jane Cooper",
            preview="Thanks for the notes!",
            time="Mon",
            online=True,
            about="Frontend lead · Groups & chat list",
            initials="JC",
            accent="#5B8CFF",
            avatar_url="https://i.pravatar.cc/150?img=5",
            media_urls=_media(70, 4),
            messages=[
                Message("Thanks for the notes!", False, "Mon"),
                Message("Anytime — let's sync on groups next.", True, "Mon", seen=False),
            ],
        ),
        Conversation(
            id="4",
            name="Project Group",
            preview="You: Image attached",
            time="Sun",
            is_group=True,
            about="University SDP-2 · Payra chat app",
            initials="PG",
            accent="#FF7B9C",
            avatar_url="https://i.pravatar.cc/150?img=60",
            media_urls=_media(100, 8),
            members=[
                people["u1"],
                people["u2"],
                people["u3"],
                people["u5"],
                people["u7"],
                ContactPerson("me", "You", "YO", "#7B61FF", ME_AVATAR, "Admin"),
            ],
            messages=[
                Message("Here's the architecture sketch.", True, "Sun", seen=True),
                Message("Looks good. Add image upload next.", False, "Sun"),
            ],
        ),
        Conversation(
            id="5",
            name="Sam Wilson",
            preview="See you in the lab",
            time="Sat",
            initials="SW",
            accent="#44C4A1",
            about="Backend · Supabase realtime",
            avatar_url="https://i.pravatar.cc/150?img=15",
            media_urls=_media(130, 3),
            messages=[
                Message("See you in the lab", False, "Sat"),
            ],
        ),
    ]
