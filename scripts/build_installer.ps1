# Build Payra with PyInstaller on Windows. Run from repo root:
#   .\scripts\build_installer.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "Create .venv and install requirements.txt first."
}
& .\.venv\Scripts\Activate.ps1
pip install -q "pyinstaller>=6.0.0"
$env:PYTHONPATH = "src"

pyinstaller `
  --name Payra `
  --windowed `
  --noconfirm `
  --clean `
  --paths src `
  --add-data "src/payra/resources;payra/resources" `
  --hidden-import PySide6.QtSvg `
  --collect-all PySide6 `
  --collect-all supabase `
  src/payra/__main__.py

Write-Host ""
Write-Host "Built: $Root\dist\Payra"
Write-Host "Zip that folder or wrap with Inno Setup. See docs/PACKAGING.md"
