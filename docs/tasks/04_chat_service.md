# 04 — Chat service

## API (`services/chat.py`)
- `list_directory()` → profiles except me
- `list_conversations()` → member chats with preview, unread, peer/group meta
- `load_messages(conversation_id)`
- `send_message(conversation_id, content, image_path=None)`
- `start_direct(other_user_id, first_message="")`
- `create_group(title, member_ids)`
- `add_members(conversation_id, user_ids)` → RPC `add_group_members` (any member), returns refreshed `Conversation`
- `set_member_role(conversation_id, user_id, role)` → admin-only promote/demote
- `remove_member(conversation_id, user_id)` → admin kick or self-leave
- `set_group_avatar(conversation_id, avatar_url)` + `storage.upload_group_avatar`
- `set_starred(conversation_id, starred)`
- `mark_read(conversation_id)`
- Map rows → existing `Conversation` / `Message` / `ContactPerson` dataclasses (`member_role`, `my_role`)

## Acceptance
- Smoke test: A starts DM with B, both see message.
- Smoke test: A creates a group; member B can add; only admin can change roles; sole-admin leave rejected; group avatar uploads.
- Unit: `tests/` (`test_add_members.py`, `test_group_production.py`) — dialogs, roles, RPC error copy, sole-admin UX.
