# Payra

Desktop realtime chat for SDP-2 — Python + PySide6 + Supabase (AI later).

## Stack

- **UI:** PySide6 (desktop, Windows + macOS)
- **Backend:** Supabase Auth, Postgres, Realtime, Storage (images) — phase 2
- **AI:** separate module — phase 3

## Run (macOS)

```bash
cd /Volumes/MAC_ST/mk/projects/payra
source .venv/bin/activate
export PYTHONPATH=src
python -m payra
```

First-time setup: [`docs/SETUP_MAC.md`](docs/SETUP_MAC.md) · `./scripts/bootstrap_venv.sh`

## Project layout

```
payra/
  design/                      # UI reference + tokens
  docs/
  scripts/bootstrap_venv.sh
  src/payra/
    main.py
    resources/                 # like Flutter assets/
      icons/nav/*.svg          # sidebar icons (replace anytime)
      images/nav_mascot.png
      README.md                # how to add SVG/PNG icons
    ui/
      styles/app.qss
      windows/main_window.py
      widgets/
    services/                  # stubs for Supabase / AI
  requirements.txt
```

## Build order

1. **UI** (current) — main shell from design reference
2. **Supabase** — auth, DMs, groups, images, realtime
3. **AI** — separate assistant
