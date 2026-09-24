#!/usr/bin/env bash
# Bootstrap Payra venv on macOS 26 (empty platform.mac_ver breaks stock pip).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PY="${PY:-/opt/homebrew/bin/python3.12}"

echo "==> Using $PY"
"$PY" --version

echo "==> Recreating .venv"
rm -rf .venv
"$PY" -m venv --without-pip .venv

SITE=".venv/lib/python3.12/site-packages"

echo "==> Installing macOS 26 mac_ver workaround"
cat > "$SITE/macver_fix.py" << 'EOF'
import platform
platform.mac_ver = lambda: ("26.2", ("", "", ""), "arm64")
EOF
echo "import macver_fix" > "$SITE/macver_fix.pth"

.venv/bin/python -c "import platform; print('mac_ver', platform.mac_ver())"

echo "==> Bootstrapping pip 25.3 (pip 26.x get-pip is broken here)"
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip-payra.py
.venv/bin/python /tmp/get-pip-payra.py "pip==25.3"

echo "==> Installing requirements"
.venv/bin/python -m pip install -r requirements.txt

echo "==> Verifying"
.venv/bin/python -c "import PySide6; print('PySide6', PySide6.__version__)"
.venv/bin/python -c "import supabase; print('supabase OK')"
.venv/bin/python -c "import dotenv, httpx; print('dotenv+httpx OK')"

echo
echo "Done. Next:"
echo "  source $ROOT/.venv/bin/activate"
echo "  export PYTHONPATH=src"
echo "  python -m payra"
