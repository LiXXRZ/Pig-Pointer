<#
 .SYNOPSIS
   Start PigPointer desktop pet.
 .PARAMETER Fast
   Skip dependency check.
 .EXAMPLE
   .\run.ps1
   .\run.ps1 -Fast
#>

param([switch]$Fast)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# ---- dependency check (unless -Fast) ----
if (-not $Fast) {
    try {
        $null = python -c "import PIL"
    } catch {
        Write-Host ":: 安装依赖 (Pillow, numpy, pystray) ..." -ForegroundColor Cyan
        pip install -r "$root\requirements.txt"
        if (-not $?) { throw "依赖安装失败" }
    }
}

# ---- launch ----
python "$root\pig_pointer.py"
if (-not $?) { exit $LASTEXITCODE }
