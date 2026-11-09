# SEMI-HUB 자동 갱신: 6시간마다(Windows 로컬 시간 00/06/12/18시) update_once_windows.bat 실행
# 중요: Windows 시간대를 (UTC+09:00) 서울로 맞추세요. PC가 켜져 있어야 합니다.
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskFile = Join-Path $folder 'update_once_windows.bat'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/d /c ""' + $taskFile + '""') -WorkingDirectory $folder
$trigger = New-ScheduledTaskTrigger -Once -At '12:00AM' -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
try {
  # 예전 '매일 12시' 작업이 있으면 같은 이름으로 덮어씁니다.
  Register-ScheduledTask -TaskName 'SEMIHUB_DailyNoon' -Action $action -Trigger $trigger -Settings $settings -Description 'SEMI-HUB RSS, jobs and Kakao alerts every 6 hours' -Force -ErrorAction Stop | Out-Null
  Write-Host 'SUCCESS: 6시간마다 자동 갱신(SEMIHUB_DailyNoon 작업) 등록 완료. Windows 시간대가 서울인지 확인하세요.'
} catch {
  Write-Host 'ERROR: 작업 등록 실패'
  Write-Host $_.Exception.Message
  Write-Host '작업 스케줄러에서 update_once_windows.bat 을 6시간마다 실행하도록 직접 등록할 수 있습니다.'
  exit 1
}
