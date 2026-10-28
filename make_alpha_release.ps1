param(
  [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

$version = "unknown"
if (Test-Path ".\\VERSION") {
  $version = (Get-Content ".\\VERSION" -Raw).Trim()
  if ([string]::IsNullOrWhiteSpace($version)) { $version = "unknown" }
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = ".\\GUNTER-$version"
}

Write-Host "Building alpha release in: $OutDir"

if (Test-Path $OutDir) {
  try {
    Remove-Item -Recurse -Force $OutDir
  } catch {
    # If files are locked (Explorer/zip viewer), fall back to a timestamped folder
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutDir = "$OutDir-$stamp"
    Write-Host "Existing folder locked; using: $OutDir"
  }
}
try {
  New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
} catch {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $OutDir = "$OutDir-$stamp"
  Write-Host "Could not create folder; using: $OutDir"
  New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$files = @(
  "gunter.py",
  "master_list.csv",
  "VERSION",
  "INSTALL_GUNTER.bat",
  "UPGRADE_GUNTER.bat",
  "UNINSTALL_GUNTER.bat",
  "requirements.txt",
  "README_ALPHA.md"
)

# Optional files
$optional = @(
  "EGG ICON.ico",
  "EGG ICON.jpeg"
)

foreach ($f in $files) {
  if (-not (Test-Path $f)) {
    throw "Missing required file: $f"
  }
  Copy-Item $f -Destination $OutDir
}

foreach ($f in $optional) {
  if (Test-Path $f) {
    Copy-Item $f -Destination $OutDir
  }
}

# Copy scripts/ and images/ folders
if (Test-Path ".\\scripts") {
  New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "scripts") | Out-Null
  Copy-Item -Recurse -Force ".\\scripts\\*" -Destination (Join-Path $OutDir "scripts")
}

if (Test-Path ".\\images") {
  New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "images") | Out-Null
  Copy-Item -Recurse -Force ".\\images\\*" -Destination (Join-Path $OutDir "images")
}

# Standalone exe build (from build_exe.ps1) -> app\
# With this present, the installer uses GUNTER.exe and testers don't need Python.
if (Test-Path ".\\dist\\GUNTER\\GUNTER.exe") {
  $appOut = Join-Path $OutDir "app"
  New-Item -ItemType Directory -Force -Path $appOut | Out-Null
  Copy-Item -Recurse -Force ".\\dist\\GUNTER\\*" -Destination $appOut
  Write-Host "Included standalone app: $appOut\GUNTER.exe"
} else {
  Write-Warning "dist\GUNTER\GUNTER.exe not found - release will require Python. Run build_exe.ps1 first."
}

Write-Host "Done."
Write-Host "Send testers the folder: $OutDir"

