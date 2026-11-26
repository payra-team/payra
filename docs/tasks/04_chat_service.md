# 04 — Chat service

## API (`services/chat.py`)
- `list_directory()` → profiles except me
- `list_conversations()` → member chats with preview, unread, peer/group meta
- `load_messages(conversation_id)`
- `send_message(conversation_id, content, image_path=None)`
- `start_direct(other_user_id, first_message="")`
- `create_group(title, member_ids)`
- `set_starred(conversation_id, starred)`
- `mark_read(conversation_id)`
- Map rows → existing `Conversation` / `Message` / `ContactPerson` dataclasses

## Acceptance
- Smoke test: A starts DM with B, both see message.
