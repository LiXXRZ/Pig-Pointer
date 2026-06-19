<#=====================================================================
 Build script — package PigPointer.exe via PyInstaller
 Usage: .\build.ps1
=====================================================================#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Ensure dependencies are installed
if (-not (python -c "import PyInstaller" 2>$null)) {
    Write-Host "Installing PyInstaller ..."
    pip install -r requirements-dev.txt
}

# Clean previous builds
Remove-Item -Path dist, build, *.spec -Recurse -Force -ErrorAction SilentlyContinue

python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "PigPointer" `
  --icon "pig_pointer.ico" `
  --add-data "pig_pointer.gif;." `
  --add-data "pig_pointer.ico;." `
  --collect-all pig_pointer `
  "pig_pointer.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Build complete: dist\PigPointer.exe" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
