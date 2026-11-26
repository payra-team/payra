# 01 — Env + dependencies

## Steps
1. Confirm project-root `.env` has live `SUPABASE_URL` + `SUPABASE_ANON_KEY`.
2. Recreate `.venv` if interpreter symlink is broken.
3. `pip install -r requirements.txt`.
4. Verify: `import supabase, dotenv, PySide6` and `supabase_ready() is True`.

## Acceptance
- `scripts/smoke_test_supabase.py` can import the app package.
