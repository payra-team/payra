# Packaging Payra (macOS · Windows · Linux)

Build **one-folder or one-file installers** with [PyInstaller](https://pyinstaller.org/).  
Do this on **each target OS** (cross-building Qt apps is unreliable).

## 1. Prepare

```bash
cd payra
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install "pyinstaller>=6.0.0"
export PYTHONPATH=src              # Windows PowerShell: $env:PYTHONPATH="src"
```

Put a production `.env` beside the built app **or** ask users to create one (see [TEAMMATE_SETUP.md](./TEAMMATE_SETUP.md)).  
Shipping a `.env` inside the installer is convenient for a private class build, but treat the anon key as semi-public.

## 2. Build command (all platforms)

From repo root:

```bash
pyinstaller \
  --name Payra \
  --windowed \
  --noconfirm \
  --clean \
  --paths src \
  --add-data "src/payra/resources:payra/resources" \
  --hidden-import PySide6.QtSvg \
  --collect-all PySide6 \
  --collect-all supabase \
  src/payra/__main__.py
```

**Windows note:** `--add-data` uses `;` instead of `:`:

```text
--add-data "src/payra/resources;payra/resources"
```

Outputs:

- `dist/Payra/` — folder you can zip and share  
- or add `--onefile` for a single binary (slower startup)

### macOS `.app` / `.dmg`

```bash
# After PyInstaller created dist/Payra.app (with --windowed on macOS)
hdiutil create -volname Payra -srcfolder dist/Payra.app -ov -format UDZO dist/Payra.dmg
```

Optional: code-sign / notarize for Gatekeeper (Apple Developer account).

### Windows `.exe`

1. Run PyInstaller on a Windows machine (see command above; use `;` in `--add-data`).  
2. Zip `dist\Payra\` **or** wrap with [Inno Setup](https://jrsoftware.org/isinfo.php) / [NSIS](https://nsis.sourceforge.io/) for a Setup.exe.  
3. SmartScreen may warn until the binary is signed (optional code-signing cert).

### Linux

```bash
# Folder build
pyinstaller ...   # same as above

# Optional AppImage (after installing appimagetool)
# Or ship dist/Payra as a .tar.gz and document:
#   ./Payra
```

For `.deb`, use [fpm](https://github.com/jordansissel/fpm) or a small `debian/` package that installs the `dist/Payra` tree under `/opt/payra`.

## 3. Helper script

```bash
./scripts/build_installer.sh          # macOS / Linux
# Windows: scripts\build_installer.ps1
```

## 4. Runtime checklist for packaged apps

1. Users still need network access to Supabase.  
2. Prefer loading `.env` from:
   - next to the executable, or  
   - `~/.payra/.env`  
   (see `payra.config` search paths).  
3. Clear demo leftovers: delete `~/.payra/local_users.json` if they tested without keys.

## 5. CI tip

Use GitHub Actions with `macos-latest`, `windows-latest`, and `ubuntu-latest` jobs, each running PyInstaller and uploading `dist/` artifacts. Do **not** bake `service_role` into builds.
