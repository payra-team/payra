# Supabase setup (Auth first)

After you create the Supabase project, wire keys into Payra like this.

## 1. Copy env file

From the **repo root** (`payra/` — same folder as `README.md`):

```bash
cp .env.example .env
```

## 2. Paste keys from the dashboard

In [Supabase Dashboard](https://supabase.com/dashboard) → your project → **Project Settings** → **API**:

| Dashboard field | Put in `.env` as |
|---|---|
| Project URL | `SUPABASE_URL` |
| `anon` `public` key | `SUPABASE_ANON_KEY` |

Example `.env`:

```env
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Do not** put the `service_role` key in the desktop app. That key bypasses RLS and must stay on a server only.

## 3. How Payra loads them

- File: project-root `.env` (gitignored)
- Loader: `src/payra/config.py` (`supabase_url()`, `supabase_anon_key()`)
- Client: `src/payra/services/supabase_client.py` → `get_client()`
- Auth API: `src/payra/services/auth.py` (login / register / logout)

Until real keys are set, auth runs in **local mode** (accounts saved under `~/.payra/`).

## 4. Dashboard Auth settings (before we integrate)

1. **Authentication → Providers → Email** — enable Email.
2. Turn **off** “Confirm email” for MVP (no verification), or enable later.
3. Optional: set Site URL to something like `http://localhost` (desktop app does not need a web redirect for password auth).

## 5. What we’ll do next (after your project exists)

1. Confirm `.env` is filled and `get_client()` returns a client.
2. Swap local login/register in `services/auth.py` to `sign_in_with_password` / `sign_up`.
3. Add a `profiles` table keyed by `auth.users.id`.
4. Then chat tables + Realtime.

You do not need to change any Python for keys — only create `.env` and paste URL + anon key.
