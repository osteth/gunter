@echo off
setlocal

REM Double-click upgrader
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\upgrade_support.ps1"

echo.
echo Done.
pause
