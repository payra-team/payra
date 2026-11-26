# 00 — Overview

## Objective
Ship Phase 2 end-to-end without AI: Auth, profiles, 1:1 chat, groups filter, starred, images, Realtime.

## Architecture
```
AuthWindow → auth.py (Supabase Auth)
MainWindow → chat.py + storage.py + Realtime worker
              ↓
         supabase-py (anon + user JWT)
              ↓
         Postgres RLS + Storage + Realtime
```

## Files to change / create
- `src/payra/services/supabase_client.py` — session-aware singleton
- `src/payra/services/auth.py` — live sign_up / sign_in / sign_out / restore
- `src/payra/services/chat.py` — conversations + messages API
- `src/payra/services/storage.py` — chat-images upload
- `src/payra/services/realtime.py` — Qt-safe message listener
- `src/payra/ui/windows/main_window.py` — live data
- `src/payra/ui/windows/auth_window.py` — copy for live mode
- `src/payra/ui/widgets/chat_pane.py` — images + current user avatar
- `scripts/smoke_test_supabase.py` — headless API smoke test
- `docs/tasks/*` — this plan

## Non-goals
- AI assistant
- Presence / typing indicators
- Push notifications
- Migrate old `~/.payra/local_users.json` accounts
