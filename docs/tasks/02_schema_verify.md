# 02 — Schema verify

## Already applied (MCP migration `payra_core_schema`)
- Tables: `profiles`, `conversations`, `conversation_members`, `messages` (+ RLS)
- Trigger: `handle_new_user` → profile row on signup
- RPCs: `get_or_create_direct_conversation`, `create_group_conversation`
- Storage bucket: `chat-images` (public read, own-folder write)
- Realtime publication on `messages` + `conversations`

## Steps
1. `list_tables` / SQL: tables exist, RLS on.
2. Confirm RPCs exist.
3. Fix advisors if blocking (revoke stray SECURITY DEFINER EXECUTE).

## Acceptance
- Empty but ready database; no missing core objects.
