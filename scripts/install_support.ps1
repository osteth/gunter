param(
  [string]$InstallDir = "",
  [switch]$NoDesktopShortcut,
  [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Find-PythonGui {
  # Prefer pyw (Python launcher, windowless)
  $pyw = Get-Command pyw.exe -ErrorAction SilentlyContinue
  if ($pyw) { return $pyw.Source }

  # Prefer pythonw next
  $python = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($python) {
    $pythonDir = Split-Path -Parent $python.Source
    $pythonw = Join-Path $pythonDir "pythonw.exe"
    if (Test-Path $pythonw) { return $pythonw }
    return $python.Source
  }

  # Last resort: maybe pythonw is directly on PATH
  $pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
  if ($pythonw) { return $pythonw.Source }

  return $null
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageRoot = Split-Path -Parent $here
$versionFile = Join-Path $packageRoot "VERSION"
$version = if (Test-Path $versionFile) { (Get-Content $versionFile -Raw).Trim() } else { "unknown" }

# Standalone build (app\GUNTER.exe) needs no Python; otherwise fall back to running gunter.py
$appSrc = Join-Path $packageRoot "app"
$useExe = Test-Path (Join-Path $appSrc "GUNTER.exe")

if (-not $useExe) {
  if (-not (Test-Path (Join-Path $packageRoot "gunter.py"))) { throw "Missing gunter.py in: $packageRoot" }
  if (-not (Test-Path (Join-Path $packageRoot "master_list.csv"))) { throw "Missing master_list.csv in: $packageRoot" }
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
  $defaultDir = Join-Path $env:LOCALAPPDATA "GUNTER"
  if ($Quiet) {
    $InstallDir = $defaultDir
  } else {
    $resp = Read-Host "Install folder (ENTER for default: $defaultDir)"
    $InstallDir = if ([string]::IsNullOrWhiteSpace($resp)) { $defaultDir } else { $resp }
  }
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Host "Installing GUNTER $version to: $InstallDir"

if ($useExe) {
  # Exe bundle already contains master_list.csv, VERSION and images\
  Copy-Item -Recurse -Force (Join-Path $appSrc "*") -Destination $InstallDir
  # Remove a script left over from an older Python-based install
  $oldScript = Join-Path $InstallDir "gunter.py"
  if (Test-Path $oldScript) { Remove-Item -Force $oldScript }
} else {
  Copy-Item (Join-Path $packageRoot "gunter.py") -Destination $InstallDir -Force
  Copy-Item (Join-Path $packageRoot "master_list.csv") -Destination $InstallDir -Force
  Copy-Item (Join-Path $packageRoot "VERSION") -Destination $InstallDir -Force
  if (Test-Path (Join-Path $packageRoot "requirements.txt")) { Copy-Item (Join-Path $packageRoot "requirements.txt") -Destination $InstallDir -Force }
}

if (Test-Path (Join-Path $packageRoot "README_ALPHA.md")) { Copy-Item (Join-Path $packageRoot "README_ALPHA.md") -Destination $InstallDir -Force }

# Copy images/ folder if present
$imagesSrc = Join-Path $packageRoot "images"
if (Test-Path $imagesSrc) {
  Copy-Item -Recurse -Force $imagesSrc -Destination (Join-Path $InstallDir "images")
}

$pyGui = if ($useExe) { $null } else { Find-PythonGui }
if ($useExe) {
  Write-Host "Using standalone GUNTER.exe (Python not required)."
} elseif (-not $pyGui) {
  Write-Warning "Python not found on PATH. Install Python 3.10+ and re-run the installer."
  Write-Warning "You can still install the files now, but the shortcut won't run until Python is installed."
} else {
  # Optional dependency install (only if requirements.txt has real entries)
  $reqPath = Join-Path $InstallDir "requirements.txt"
  if (Test-Path $reqPath) {
    $reqLines = Get-Content $reqPath | Where-Object { $_ -and (-not $_.Trim().StartsWith("#")) }
    if ($reqLines.Count -gt 0) {
      Write-Host "Installing Python dependencies from requirements.txt..."
      try {
        & python -m pip install --user -r $reqPath
      } catch {
        Write-Warning "Dependency install failed (continuing anyway)."
        Write-Warning $_
      }
    }
  }
}

# Create Start Menu shortcut (no admin needed)
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$folder = Join-Path $startMenu "GUNTER"
New-Item -ItemType Directory -Force -Path $folder | Out-Null

$shortcutPath = Join-Path $folder "GUNTER.lnk"
if ($useExe) {
  $target = Join-Path $InstallDir "GUNTER.exe"
  $args = ""
} else {
  $target = if ($pyGui) { $pyGui } else { "python.exe" }
  $args = "`"$InstallDir\gunter.py`""
}
$working = $InstallDir

$icon = Join-Path $InstallDir "images\\EGG ICON.ico"
if (-not (Test-Path $icon)) { $icon = Join-Path $InstallDir "images\\EGG ICON.jpeg" }

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = $target
$sc.Arguments = $args
$sc.WorkingDirectory = $working
$sc.Description = "GUNTER - Quest Stamp Tracker"
if (Test-Path $icon) { $sc.IconLocation = $icon }
$sc.Save()

Write-Host "Created Start Menu shortcut: $shortcutPath"

# Optionally create a Desktop shortcut (launch icon)
if (-not $NoDesktopShortcut) {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $desktopShortcut = Join-Path $desktop "GUNTER.lnk"

  $createDesktop = $true
  if (-not $Quiet) {
    try {
      $resp = Read-Host "Create Desktop launch icon? (Y/n)"
      if ($resp -and $resp.Trim().ToLower().StartsWith("n")) { $createDesktop = $false }
    } catch {
      $createDesktop = $true
    }
  }

  if ($createDesktop) {
    $sc2 = $wsh.CreateShortcut($desktopShortcut)
    $sc2.TargetPath = $target
    $sc2.Arguments = $args
    $sc2.WorkingDirectory = $working
    $sc2.Description = "GUNTER - Quest Stamp Tracker"
    if (Test-Path $icon) { $sc2.IconLocation = $icon }
    $sc2.Save()
    Write-Host "Created Desktop shortcut: $desktopShortcut"
  }
}

# Write install info for upgrades/uninstall
try {
  $info = @{
    version = $version
    install_dir = $InstallDir
    installed_at = (Get-Date).ToString("s")
  } | ConvertTo-Json -Depth 4
  Set-Content -Path (Join-Path $InstallDir "install_info.json") -Value $info -Encoding UTF8

  # Also write to a stable location so upgrade/uninstall can find it even if InstallDir is custom.
  $configDir = Join-Path $env:LOCALAPPDATA "GUNTER"
  New-Item -ItemType Directory -Force -Path $configDir | Out-Null
  Set-Content -Path (Join-Path $configDir "install_info.json") -Value $info -Encoding UTF8
} catch {
  # ignore
}

Write-Host "Done."

