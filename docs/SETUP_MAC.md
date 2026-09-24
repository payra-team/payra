# macOS setup (Homebrew) — Payra

## What went wrong

Python **3.12.14** installed fine. Creating `.venv` failed because of **macOS 26**, not the external disk.

On macOS 26.2, `platform.mac_ver()` returns empty (`''`). Pip then crashes:

```text
ValueError: invalid literal for int() with base 10: ''
```

Your disk `/Volumes/MAC_ST` is **APFS** — storing the project there is fine.

---

## Fix: run these in Terminal (project root)

```bash
cd /Volumes/MAC_ST/mk/projects/payra

# Clean broken venv
rm -rf .venv

# Create venv without broken ensurepip
/opt/homebrew/bin/python3.12 -m venv --without-pip .venv

SITE=.venv/lib/python3.12/site-packages

# macOS 26 fix (must exist BEFORE pip runs)
cat > "$SITE/macver_fix.py" << 'EOF'
import platform
platform.mac_ver = lambda: ("26.2", ("", "", ""), "arm64")
EOF
echo "import macver_fix" > "$SITE/macver_fix.pth"

# Confirm fix
.venv/bin/python -c "import platform; print(platform.mac_ver())"
# expect: ('26.2', ('', '', ''), 'arm64')

# Install pip properly
curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
.venv/bin/python /tmp/get-pip.py

# Activate + install project packages (PySide6 is large ~400MB+)
source .venv/bin/activate
python -m pip install -r requirements.txt

# Confirm
python -c "import PySide6; print('PySide6', PySide6.__version__)"
python -c "import supabase; print('supabase OK')"
```

### Run the app

```bash
cd /Volumes/MAC_ST/mk/projects/payra
source .venv/bin/activate
export PYTHONPATH=src
python -m payra
```

---

## Every work session

```bash
cd /Volumes/MAC_ST/mk/projects/payra
source .venv/bin/activate
export PYTHONPATH=src
```

---

## Teammates on older macOS

They can use the normal path:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Do **not** commit `.venv/`. Keep it gitignored.
