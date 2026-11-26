# Teammate setup — why you see old demo users

## What’s going wrong?

Payra has **two modes**:

| Mode | When | What you see |
|------|------|----------------|
| **Live Supabase** | Repo-root `.env` has real `SUPABASE_URL` + `SUPABASE_ANON_KEY` | Real accounts, real chats from the shared project |
| **Demo / local** | `.env` missing, empty, or still has `YOUR_PROJECT` / `your_anon_key_here` | Fake people (Alex Johnson, Jane Cooper, …) + accounts saved only on **that PC** under `~/.payra/` |

`git pull` does **not** bring `.env` (it is gitignored on purpose).  
So after a pull on Windows or Linux, if you never add `.env`, the app stays in demo mode: signup writes to a local JSON file, **not** Supabase — and New Chat may list demo contacts, not the database.

Local leftover files can also confuse you:

- macOS / Linux: `~/.payra/local_users.json`, `~/.payra/session.json`
- Windows: `C:\Users\<You>\.payra\local_users.json`, `session.json`

---

## Fix in 5 minutes

### A. Get keys (pick one)

**Option 1 — zip from a teammate (fastest)**  
They send you `payra-env.zip` (private channel: Slack/Drive, not GitHub).  
Inside it is a single file named `.env`.

```text
payra-env.zip
└── .env          ← put this in the repo root (next to README.md)
```

**Option 2 — copy from template**

```bash
cp .env.example .env          # macOS / Linux
copy .env.example .env        # Windows
```

Then paste URL + **anon** key from Supabase → Project Settings → API.

### B. Confirm the file location

```text
payra/                 ← repo root after git clone / pull
├── README.md
├── .env               ← MUST be here (not inside src/)
├── .env.example
├── requirements.txt
└── src/payra/...
```

### C. Install & run

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python scripts/check_env.py          # should say LIVE
python -m payra
```

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="src"
python scripts/check_env.py
python -m payra
```

### D. Clear old local demo data (optional but recommended)

If you previously signed up while offline/demo:

```bash
# macOS / Linux
rm -rf ~/.payra/local_users.json ~/.payra/session.json

# Windows PowerShell
Remove-Item "$env:USERPROFILE\.payra\local_users.json" -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.payra\session.json" -ErrorAction SilentlyContinue
```

Then open Payra → **Create account** again (that user is created in Supabase).

---

## How to share `.env` as a zip (for you / lead)

**Do not commit keys.** Share privately:

```bash
# From the machine that already has a working .env (repo root)
zip -j payra-env.zip .env
# Send payra-env.zip via Slack / Google Drive (not email to a public list)
```

Windows (PowerShell, repo root):

```powershell
Compress-Archive -Path .env -DestinationPath payra-env.zip -Force
```

Tell teammates: *“Unzip so `.env` sits next to `README.md`, then run `python scripts/check_env.py`.”*

---

## Checklist if it still looks “demo”

1. `python scripts/check_env.py` prints **LIVE**, not DEMO  
2. Auth window / profile note says synced from Supabase (not “Local profile”)  
3. `.env` has no `YOUR_PROJECT` or `your_anon_key_here`  
4. `PYTHONPATH=src` and venv active  
5. Old `~/.payra/local_users.json` deleted  
6. Internet can reach `*.supabase.co`  

---

## Related docs

- [Supabase setup](./SUPABASE_SETUP.md)  
- [Packaging installers](./PACKAGING.md)  
- [macOS setup](./SETUP_MAC.md)  
