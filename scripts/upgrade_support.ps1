param(
  [string]$InstallDir = "",
  [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageRoot = Split-Path -Parent $here

function Resolve-InstallDir {
  param([string]$ExplicitDir)
  if (-not [string]::IsNullOrWhiteSpace($ExplicitDir)) { return $ExplicitDir }

  $defaultDir = Join-Path $env:LOCALAPPDATA "GUNTER"
  $infoPath = Join-Path $defaultDir "install_info.json"
  if (Test-Path $infoPath) {
    try {
      $info = Get-Content $infoPath -Raw | ConvertFrom-Json
      if ($info.install_dir) { return [string]$info.install_dir }
    } catch { }
  }
  return $defaultDir
}

$InstallDir = Resolve-InstallDir $InstallDir

$installer = Join-Path $here "install_support.ps1"
if (-not (Test-Path $installer)) { throw "Missing install_support.ps1 in: $here" }

Write-Host "Upgrading GUNTER in: $InstallDir"

if ($NoDesktopShortcut) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $installer -InstallDir $InstallDir -NoDesktopShortcut -Quiet
} else {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $installer -InstallDir $InstallDir -Quiet
}

Write-Host "Upgrade complete."

