# 08 — Run + test

## Automated
1. Recreate venv + install deps
2. `scripts/smoke_test_supabase.py` — register 2 users, DM, message, upload, cleanup
3. Import-check GUI modules headless (`QT_QPA_PLATFORM=offscreen` if available)

## Manual (when back)
```bash
source .venv/bin/activate
PYTHONPATH=src python -m payra
```
Register two accounts in two app instances and chat.

## Acceptance
- Smoke script exit code 0
- App starts without traceback
