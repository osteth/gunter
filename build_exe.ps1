# Builds a standalone GUNTER.exe (no Python needed on the user's machine).
#
# Output: dist\GUNTER\  (GUNTER.exe plus its runtime files, master_list.csv, VERSION, images\)
#
# Requires Python 3.10+ on the BUILD machine only:
#   python -m pip install pyinstaller tkinterdnd2

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name GUNTER `
  --icon "images\EGG ICON.ico" `
  --contents-directory "." `
  --collect-all tkinterdnd2 `
  --add-data "master_list.csv;." `
  --add-data "VERSION;." `
  --add-data "images;images" `
  gunter.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path ".\dist\GUNTER\GUNTER.exe")) { throw "Build did not produce dist\GUNTER\GUNTER.exe" }

Write-Host "Built: dist\GUNTER\GUNTER.exe"
