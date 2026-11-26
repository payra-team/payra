# Payra Phase 2 — Execution Plan (AI skipped)

**Goal:** Production-ready desktop chat on Supabase Auth + Postgres + Realtime + Storage.  
**Out of scope:** Payra AI (`services/ai.py` stays a stub).

**Project:** `tvaqgdiscjzmfcrnlumr` · Region `ap-northeast-2` · Status `ACTIVE_HEALTHY`

## Decisions (locked)

| Topic | Decision |
|--------|----------|
| Auth | Email/password via Supabase; local JSON only as offline fallback if `.env` missing |
| Email confirm | App handles “confirm email” error; prefer Confirm email OFF in dashboard for MVP |
| Keys | Anon key in `.env` only — never `service_role` in the desktop app |
| Schema | Already applied via MCP: `profiles`, `conversations`, `conversation_members`, `messages`, bucket `chat-images`, RLS + RPCs |
| Demo data | UI loads live data when `supabase_ready()`; demo fixtures kept for offline UI only |
| Realtime | Subscribe to `messages` inserts; marshal onto Qt main thread via signals |
| Groups | Create via `create_group_conversation` RPC when adding multiple members later; New Chat = 1:1 |
| Starred | `conversation_members.starred` |
| Contacts | `profiles` directory excluding self |

## Task order

| # | File | Status |
|---|------|--------|
| 00 | [00_overview.md](./00_overview.md) | Done |
| 01 | [01_env_deps.md](./01_env_deps.md) | Done |
| 02 | [02_schema_verify.md](./02_schema_verify.md) | Done |
| 03 | [03_auth.md](./03_auth.md) | Done |
| 04 | [04_chat_service.md](./04_chat_service.md) | Done |
| 05 | [05_storage.md](./05_storage.md) | Done |
| 06 | [06_ui_wire.md](./06_ui_wire.md) | Done |
| 07 | [07_realtime.md](./07_realtime.md) | Done |
| 08 | [08_test_run.md](./08_test_run.md) | Done |

See [STATUS.md](./STATUS.md) for smoke evidence and how to run.

## Done criteria

1. Register / login / logout against live Supabase  
2. Empty inbox until chats exist; New Chat lists real profiles  
3. Send text + image; peer can receive via Realtime  
4. Star toggles; Groups filter works  
5. `scripts/smoke_test_supabase.py` exits 0  
6. App launches with `python -m payra`
