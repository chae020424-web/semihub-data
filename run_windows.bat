@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (py -3 server.py & goto end)
where python >nul 2>nul
if %ERRORLEVEL%==0 (python server.py & goto end)
echo Python 3 is required for online updates and AI.
:end
pause
