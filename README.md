# Payra

<p align="center">
  <img src="src/payra/resources/images/logo.png" alt="Payra logo" width="120" />
</p>

<p align="center">
  <strong>Desktop realtime chat for SDP-2</strong><br/>
  <em>Payra (পায়রা) = pigeon — inspired by carrier pigeons that once delivered messages.</em>
</p>

---

## What is this?

Payra is a **native desktop messenger** (Windows + macOS) built with **Python + PySide6**, with **Supabase** for auth/realtime/storage later, and a separate **AI assistant** phase.

| Phase | Focus |
|-------|--------|
| 1 | UI (login, chat shell, groups, profile) |
| 2 | Supabase — auth, 1:1 + group chat, images |
| 3 | Payra AI (separate from human chats) |

Right now you can **clone → set up → run** the app with **local auth** (no Supabase keys required yet).

---

## Quick start (after clone)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR-ORG/payra.git
cd payra
```

Replace `YOUR-ORG` with your GitHub organization or username.

---

### 2. Create a virtual environment & install deps

#### Option A — Recommended on macOS (uv)

Homebrew Python can break `venv`/`pip` on newer macOS. Prefer **uv**:

```bash
brew install uv

# from the project root
./scripts/bootstrap_venv.sh
```

Or manually:

```bash
uv python install 3.12
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

#### Option B — Standard Python (Windows / most Linux)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

#### Verify install

```bash
python -c "import PySide6; print('PySide6', PySide6.__version__)"
```

---

### 3. Environment file (optional for now)

```bash
cp .env.example .env
```

- **Today:** you can leave placeholders — the app runs with **local auth**.
- **Later (Supabase):** put Project URL + anon key in `.env`.  
  Never commit `.env` (it is gitignored).

---

### 4. Run the app

Always from the **project root**:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\activate
export PYTHONPATH=src              # Windows PowerShell: $env:PYTHONPATH="src"
python -m payra
```

You should see the **Payra** login / register window.

---

### 5. First login

1. Click **Create account**.
2. Enter display name, email, password (min 6 characters).
3. Sign in — the main chat shell opens.

Accounts are stored locally under `~/.payra/` (not in the repo). Each teammate registers their own account on their machine.

---

## Every work session (cheat sheet)

```bash
cd payra
source .venv/bin/activate
export PYTHONPATH=src
python -m payra
```

---

## Project structure

```
payra/
├── README.md                 ← you are here
├── requirements.txt          ← Python dependencies
├── .env.example              ← template for secrets (copy → .env)
├── .gitignore
│
├── scripts/
│   └── bootstrap_venv.sh     ← one-command macOS/uv setup
│
├── design/                   ← UI mockups & Stitch prompts
│   ├── STITCH_PROMPTS.md
│   ├── exports/              ← design screenshots
│   └── notes.md
│
├── docs/                     ← team documentation
│   ├── SETUP_MAC.md          ← macOS troubleshooting
│   ├── SUPABASE_SETUP.md     ← backend setup (phase 2)
│   ├── architecture.md       ← human chat vs AI notes
│   └── proposal/             ← project proposal DOCX
│
└── src/
    └── payra/                ← application package
        ├── __main__.py       ← python -m payra entry
        ├── main.py           ← auth gate → main window
        ├── config.py         ← env / settings
        │
        ├── models/           ← data shapes & demo content
        │   └── demo_data.py
        │
        ├── services/         ← business logic (backend-facing)
        │   ├── auth.py       ← register / login / session
        │   ├── chat.py       ← messaging (phase 2)
        │   ├── storage.py    ← images (phase 2)
        │   ├── supabase_client.py
        │   └── ai.py         ← AI assistant (phase 3)
        │
        ├── ui/               ← all GUI code
        │   ├── theme.py      ← colors / spacing tokens
        │   ├── theme_app.py  ← apply light theme
        │   ├── styles/
        │   │   └── app.qss   ← Qt stylesheet
        │   ├── windows/
        │   │   ├── auth_window.py
        │   │   └── main_window.py
        │   └── widgets/
        │       ├── nav_sidebar.py
        │       ├── chat_list.py
        │       ├── chat_pane.py
        │       ├── detail_panel.py
        │       ├── dialogs.py
        │       └── ...
        │
        └── resources/        ← assets (like Flutter assets/)
            ├── icons/
            │   ├── app_icon.png
            │   └── nav/      ← chats, groups, contacts, …
            └── images/
                ├── logo.png
                └── nav_mascot.png
```

### Who edits what?

| Area | Folder | Typical work |
|------|--------|----------------|
| Screens / widgets | `src/payra/ui/` | Layout, buttons, chat UI |
| Look & feel | `ui/styles/app.qss`, `ui/theme.py` | Colors, fonts, spacing |
| Login / accounts | `services/auth.py` | Register, session |
| Backend | `services/`, `docs/SUPABASE_*` | Supabase, realtime |
| Icons / logo | `resources/` | PNG / SVG assets |
| Docs for the team | `docs/`, this `README.md` | Setup & design notes |

---

## Stack (short)

| Layer | Tech |
|-------|------|
| Desktop UI | Python · PySide6 (Qt) |
| Backend | Supabase (Auth, Postgres, Realtime, Storage) |
| AI | Separate module / API (later) |
| Design | Google Stitch → implement in Qt |

---

## Team tips

1. **Pull before you start** — `git pull`
2. **Branch for features** — e.g. `feature/login-polish`
3. **Don’t commit** `.venv/`, `.env`, or `__pycache__/`
4. **Keep PRs small** — one feature / one fix
5. Mac setup issues? See [`docs/SETUP_MAC.md`](docs/SETUP_MAC.md)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named payra` | Run from repo root and set `PYTHONPATH=src` |
| `No module named PySide6` | Activate `.venv` and reinstall: `uv pip install -r requirements.txt` |
| `python -m venv` fails on macOS | Use uv — see Option A above / `docs/SETUP_MAC.md` |
| Window doesn’t open | Check terminal for errors; confirm `python -m payra` from project root |
| Forgot local password | Delete `~/.payra/local_users.json` (and `session.json`) and register again |

---

## More docs

- [macOS setup details](docs/SETUP_MAC.md)
- [Supabase setup](docs/SUPABASE_SETUP.md)
- [Architecture notes](docs/architecture.md)
- [Asset / logo guide](src/payra/resources/README.md)

---

<p align="center">
  <sub>SDP-2 · Built with ❤️ by the Payra team</sub>
</p>
