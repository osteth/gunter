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

# Player data (profiles\, settings.json) always lives in %LOCALAPPDATA%\GUNTER,
# which is also the default install folder. Keep it unless -RemoveUserData.
$userDataDir = Join-Path $env:LOCALAPPDATA "GUNTER"
$userDataNames = @("profiles", "settings.json", "stamp_progress.json")

# Back up player data unless explicitly removing it
if (-not $RemoveUserData) {
  try {
    $toBackup = @()
    foreach ($dir in @($userDataDir, $InstallDir) | Select-Object -Unique) {
      foreach ($name in $userDataNames) {
        $p = Join-Path $dir $name
        if (Test-Path $p) { $toBackup += $p }
      }
    }
    if ($toBackup.Count -gt 0) {
      $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
      $dest = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "GUNTER Backups\$stamp"
      New-Item -ItemType Directory -Force -Path $dest | Out-Null
      foreach ($p in $toBackup) { Copy-Item -Recurse -Force $p -Destination $dest }
      Write-Host "Backed up your profiles and progress to: $dest"
    }
  } catch {
    Write-Warning "Could not back up player data: $_"
  }
}

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
    # Remove app files but leave player data so a reinstall picks it back up
    Get-ChildItem -Force $InstallDir |
      Where-Object { $userDataNames -notcontains $_.Name } |
      Remove-Item -Recurse -Force
    if (-not (Get-ChildItem -Force $InstallDir)) { Remove-Item -Force $InstallDir }
    else { Write-Host "Kept your profiles and progress in: $InstallDir" }
  }
}

if ($RemoveUserData -and (Test-Path $userDataDir)) {
  Remove-Item -Recurse -Force $userDataDir
}

# Remove cached install info (so upgrade/uninstall don't target old dir)
try {
  $configDir = Join-Path $env:LOCALAPPDATA "GUNTER"
  $infoPath = Join-Path $configDir "install_info.json"
  if (Test-Path $infoPath) { Remove-Item -Force $infoPath }
} catch { }

Write-Host "Uninstall complete."

