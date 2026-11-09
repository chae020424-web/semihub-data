import json, os, sys, time, tempfile, pathlib
import updater, server
d=pathlib.Path(tempfile.mkdtemp())
updater.LIVE=d/'live.json'; updater.LOCK=d/'update.lock'
def live(): return json.loads(updater.LIVE.read_text(encoding='utf-8'))
updater.LIVE.write_text(json.dumps({'status':'updating','lastSuccess':'2026-11-03T12:02:44+09:00','news':[1],'jobs':[2]}),encoding='utf-8')
# 1) 오래된 잠금 → 정리, 기존 데이터 보존
updater.LOCK.write_text('x'); old=time.time()-3000; os.utime(updater.LOCK,(old,old))
assert updater.recover_stale() is True and not updater.LOCK.exists()
L=live(); assert L['status']=='error' and L['news']==[1] and L['lastSuccess'].startswith('2026-11-03') and '중단' in L['errors'][0]
# 2) 최근 잠금은 그대로(실제 실행 중일 수 있음)
updater.LOCK.write_text('x'); assert updater.recover_stale() is False and updater.LOCK.exists(); updater.LOCK.unlink()
# 3) 잠금 없이 '갱신 중'으로 남은 상태 → 오류로 표시
L=live(); L['status']='updating'; updater.LIVE.write_text(json.dumps(L),encoding='utf-8')
assert updater.recover_stale() is True and live()['status']=='error'
assert updater.recover_stale() is False
# 4) 멈춘 갱신은 시간 제한 후 강제 종료
t=time.time(); r=server.run_update_guarded(False,cmd=[sys.executable,'-c','import time;time.sleep(60)'],timeout=2)
assert r=='timeout' and time.time()-t<20 and live()['status']=='error' and not updater.LOCK.exists()
# 5) 정상 종료는 출력 반환
assert server.run_update_guarded(False,cmd=[sys.executable,'-c','print("한글 ok")'],timeout=10).startswith('done:')
print('PASS updater_lock')
