@echo off
setlocal

REM Double-click uninstaller
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\uninstall_support.ps1"

echo.
echo Done.
pause
