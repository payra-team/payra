#!/usr/bin/env bash
# Build Payra with PyInstaller (run on the target OS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Create/activate .venv and pip install -r requirements.txt first."
  exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q "pyinstaller>=6.0.0"

SEP=":"
if [[ "${OSTYPE:-}" == msys* || "${OSTYPE:-}" == cygwin* ]]; then
  SEP=";"
fi

export PYTHONPATH=src
pyinstaller \
  --name Payra \
  --windowed \
  --noconfirm \
  --clean \
  --paths src \
  --add-data "src/payra/resources${SEP}payra/resources" \
  --hidden-import PySide6.QtSvg \
  --collect-all PySide6 \
  --collect-all supabase \
  src/payra/__main__.py

echo ""
echo "Built: $ROOT/dist/Payra"
if [[ "$(uname -s)" == "Darwin" && -d dist/Payra.app ]]; then
  hdiutil create -volname Payra -srcfolder dist/Payra.app -ov -format UDZO dist/Payra.dmg
  echo "DMG:   $ROOT/dist/Payra.dmg"
fi
echo "See docs/PACKAGING.md for Windows/Linux installers."
