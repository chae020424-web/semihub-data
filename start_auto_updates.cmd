@echo off
setlocal
cd /d "%~dp0"
title SEMI-HUB - Python Auto Update Mode
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 server.py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python server.py
  ) else (
    echo [ERROR] Python 3 is not installed.
    echo You can use start_semihub.cmd without Python.
  )
)
echo.
echo When auto-update mode works, keep this window open.
pause
