@echo off
setlocal

REM Simple double-click installer wrapper
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\install_support.ps1"

echo.
echo If nothing happened, you may need to allow PowerShell scripts.
echo If you must run PowerShell directly, run: scripts\install_support.ps1
pause
