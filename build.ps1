$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "PigPointer" `
  --icon "pig_pointer.ico" `
  --add-data "pig_pointer.gif;." `
  --add-data "pig_pointer.ico;." `
  "pig_pointer.py"

Write-Host ""
Write-Host "Build complete: dist\PigPointer.exe"
