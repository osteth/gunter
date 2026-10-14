param(
  [string]$InstallDir = "",
  [switch]$RemoveUserData,
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

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

Write-Host "Uninstalling GUNTER from: $InstallDir"

# Remove shortcuts
try {
  $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
  $folder = Join-Path $startMenu "GUNTER"
  if (Test-Path $folder) { Remove-Item -Recurse -Force $folder }
} catch { }

try {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $desktopShortcut = Join-Path $desktop "GUNTER.lnk"
  if (Test-Path $desktopShortcut) { Remove-Item -Force $desktopShortcut }
} catch { }

# Backup progress unless explicitly removing user data
try {
  $progress = Join-Path $InstallDir "stamp_progress.json"
  if ((Test-Path $progress) -and (-not $RemoveUserData)) {
    $backupRoot = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "GUNTER Backups"
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
    $dest = Join-Path $backupRoot "stamp_progress.$stamp.json"
    Copy-Item $progress -Destination $dest -Force
    Write-Host "Backed up progress to: $dest"
  }
} catch { }

if (-not $Quiet) {
  $resp = Read-Host "Remove installed files in $InstallDir ? (Y/n)"
  if ($resp -and $resp.Trim().ToLower().StartsWith("n")) {
    Write-Host "Leaving installed files in place."
    Write-Host "Uninstall complete."
    exit 0
  }
}

if (Test-Path $InstallDir) {
  if ($RemoveUserData) {
    Remove-Item -Recurse -Force $InstallDir
  } else {
    # Remove everything except (optionally) keep Export.txt (user might want it) – but most installs won't have it.
    Remove-Item -Recurse -Force $InstallDir
  }
}

# Remove cached install info (so upgrade/uninstall don't target old dir)
try {
  $configDir = Join-Path $env:LOCALAPPDATA "GUNTER"
  $infoPath = Join-Path $configDir "install_info.json"
  if (Test-Path $infoPath) { Remove-Item -Force $infoPath }
} catch { }

Write-Host "Uninstall complete."

