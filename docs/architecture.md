# Architecture notes

Build order: **Design → Supabase chat (1:1 + groups + images) → AI**.

## Human chat vs AI

Keep AI **separate**:

- Tables: `ai_conversations`, `ai_messages` (or local-only history first)
- UI: dedicated “AI Assistant” entry, not a normal group/DM
- Service: `services/ai.py` calling Groq/Gemini later

Do **not** use a single `is_ai` flag on human `conversations` if it complicates RLS and member logic.

## Planned human-chat tables (phase 2)

- `profiles`
- `conversations` (`type`: `direct` | `group`, `title`, `avatar_url`)
- `conversation_members`
- `messages` (`content`, `image_path` nullable, `sender_id`)
- Storage bucket: `chat-images`
