@echo off
rem Old name kept for compatibility: now registers the 6-hour schedule.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_every6h.ps1"
pause
