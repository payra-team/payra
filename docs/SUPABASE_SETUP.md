# Supabase setup (Phase 2 live)

Payra is wired to the live **Payra** project (`tvaqgdiscjzmfcrnlumr`).

## 1. Env file

Project-root `.env` (gitignored):

```env
SUPABASE_URL=https://tvaqgdiscjzmfcrnlumr.supabase.co
SUPABASE_ANON_KEY=<anon key from Dashboard → Settings → API>
```

Never put `service_role` in the desktop app.

## 2. Auth dashboard (recommended)

1. **Authentication → Providers → Email** — enabled  
2. **Confirm email** — **OFF** for MVP (desktop signup without mailbox)  
3. Site URL can stay `http://localhost`

## 3. Schema (already applied)

Tables + RLS + RPCs + `chat-images` bucket + Realtime:

- `profiles`
- `conversations` (`direct` | `group`)
- `conversation_members` (incl. `starred`, `last_read_at`)
- `messages`
- RPCs: `get_or_create_direct_conversation`, `create_group_conversation`

Migrations were applied via Supabase MCP; see `docs/tasks/`.

## 4. App wiring

| Piece | Module |
|-------|--------|
| Keys | `config.py` |
| Client + tokens | `services/supabase_client.py` (`~/.payra/supabase_session.json`) |
| Auth | `services/auth.py` |
| Chat | `services/chat.py` |
| Images | `services/storage.py` |
| Realtime | `services/realtime.py` |
| UI | `ui/windows/main_window.py` |

## 5. Verify

```bash
source .venv/bin/activate
export PYTHONPATH=src
python scripts/smoke_test_supabase.py --phase test --state /tmp/payra_smoke.json
python -m payra
```

Phase 3 (AI) is intentionally skipped — `services/ai.py` remains a stub.
