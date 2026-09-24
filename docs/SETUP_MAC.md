# macOS setup — Payra

## Why the normal pip/venv path failed

On **macOS 26**, Homebrew Python reports an empty `platform.mac_ver()`. That breaks:

- `python -m venv` / `ensurepip` / `get-pip.py`
- `uv venv --python /opt/homebrew/bin/python3.12`

Your external disk is fine. The fix is to use **uv + uv-managed Python** (not Homebrew Python for the venv).

## One-time setup (already done on this machine if verify passed)

```bash
# uv was installed via: brew install uv

cd /Volumes/MAC_ST/mk/projects/payra
./scripts/bootstrap_venv.sh
```

Or manually:

```bash
brew install uv
cd /Volumes/MAC_ST/mk/projects/payra
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

Confirm:

```bash
source .venv/bin/activate
python -c "import PySide6; print(PySide6.__version__)"
python -c "import supabase; print('supabase OK')"
```

## Every work session

```bash
cd /Volumes/MAC_ST/mk/projects/payra
source .venv/bin/activate
export PYTHONPATH=src
python -m payra
```

## Adding packages later

Prefer uv (works with this venv):

```bash
source .venv/bin/activate
uv pip install some-package
uv pip freeze > requirements.txt   # only when you intend to lock deps
```

Avoid `python -m pip` with Homebrew Python on macOS 26.

## Supabase keys (next phase)

```bash
cp .env.example .env
# edit .env — paste Project URL + anon key from Dashboard → Settings → API
```

Details: [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md).
