@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo SEMI-HUB: Playwright(ASML 수집용 브라우저) 설치를 시작합니다. 약 150MB를 내려받습니다.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m pip install playwright
  py -3 -m playwright install chromium
) else (
  python -m pip install playwright
  python -m playwright install chromium
)
echo 완료되면 python job_collectors.py 로 asml 줄이 [OK]인지 확인하세요.
pause
