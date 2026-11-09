@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
 py -3 backfill_full_2026.py
) else (
 python backfill_full_2026.py
)
pause
