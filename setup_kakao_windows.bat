@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist kakao_config.json (
  copy kakao_config.example.json kakao_config.json >nul
  echo kakao_config.json 파일이 만들어졌습니다. 메모장으로 열어 REST API 키를 넣고 저장한 뒤 이 파일을 다시 실행하세요.
  notepad kakao_config.json
  pause
  exit /b
)
python kakao_notify.py auth
pause
