#!/usr/bin/env bash
# Bootstrap Payra venv on macOS 26 using uv-managed Python
# (Homebrew Python's empty platform.mac_ver() breaks pip/uv with brew Python.)
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv via Homebrew..."
  NONINTERACTIVE=1 HOMEBREW_NO_AUTO_UPDATE=1 brew install uv
fi

echo "==> Installing uv-managed Python 3.12 (if needed)"
uv python install 3.12

echo "==> Creating .venv"
rm -rf .venv
uv venv --python 3.12 .venv

echo "==> Installing requirements"
uv pip install -r requirements.txt

echo "==> Verifying"
.venv/bin/python -c "import platform; print('mac_ver', platform.mac_ver())"
.venv/bin/python -c "import PySide6; print('PySide6', PySide6.__version__)"
.venv/bin/python -c "import supabase; print('supabase OK')"
.venv/bin/python -c "import dotenv, httpx; print('dotenv+httpx OK')"

echo
echo "Done. Next:"
echo "  source $ROOT/.venv/bin/activate"
echo "  export PYTHONPATH=src"
echo "  python -m payra"
