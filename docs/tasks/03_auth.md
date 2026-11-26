# 03 — Supabase Auth

## Implement
- Session file: `~/.payra/supabase_session.json` (access + refresh tokens)
- `register` → `sign_up` with `display_name` / `username` metadata
- `login` → `sign_in_with_password`
- `logout` → `sign_out` + clear tokens
- `restore_session` → `set_session` / refresh, then load `profiles` row
- Clear errors for email confirmation / invalid credentials

## Acceptance
- Two users can register and log in via smoke test.
