@echo off
setlocal
cd /d "%~dp0"
title SEMI-HUB v6 - 반도체 기술 학습센터
if not exist "index.html" (
 echo ERROR: Please extract the ZIP file first.
 pause
 exit /b 1
)
where py >nul 2>nul
if %ERRORLEVEL%==0 (
 echo Starting Python local server. News updates and free AI available with a key.
 py -3 server.py
 goto end
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
 echo Starting Python local server.
 python server.py
 goto end
)
echo Python is not installed. Opening basic local viewer without AI or updates.
if exist "semihub_offline.html" start "" "semihub_offline.html"
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
 echo Optional: for a local web server without AI, use Windows PowerShell.
 "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0local_server.ps1"
)
:end
echo If the browser does not open, use the http://127.0.0.1:PORT address printed above.
pause
