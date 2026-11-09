import json, os, tempfile, pathlib, threading, functools, http.server, datetime
import updater, news_engine, career_watch, sync_remote as sr
d=pathlib.Path(tempfile.mkdtemp()); local=d/'local'; remote=d/'remote'; local.mkdir(); remote.mkdir()
updater.LIVE=local/'live.json'; updater.LOCK=local/'update.lock'; news_engine.ARCHIVE=local/'news_archive.json'; news_engine.STATE=local/'news_state.json'; career_watch.STATE=local/'career_watch.json'
W=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False),encoding='utf-8')
R=lambda p:json.loads(p.read_text(encoding='utf-8'))
# 가짜 GitHub(raw) 서버
H=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(remote))
H.log_message=lambda *a,**k:None
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
os.environ['SEMIHUB_REMOTE_BASE']='http://127.0.0.1:%d/'%srv.server_address[1]
# 설정 검사
for bad in ['','a','a/b/c','a b/c','../x/y','a/b?x','http://x/y']:
    os.environ['SEMIHUB_REMOTE_REPO']=bad; assert (sr.settings() is None) or bad=='' and False,(bad)
os.environ['SEMIHUB_REMOTE_REPO']='me/semihub-data'; assert sr.settings()=={'repo':'me/semihub-data','branch':'main'}
# 원격 데이터: 더 최신
W(remote/'live.json',{'status':'ok','lastSuccess':'2026-11-09T18:05:00+09:00','news':[1,2],'jobs':[{'url':'u1'}]})
W(remote/'news_archive.json',[{'url':'https://r/1','title':'원격','date':'2026-11-09'},{'url':'https://both','title':'공통(원격 분석)','date':'2026-11-08','analysis':'AI'}])
W(remote/'news_state.json',{'completed':['a','b','c']}); W(remote/'career_watch.json',{'x':1})
# 로컬: 더 오래됨
W(updater.LIVE,{'status':'ok','lastSuccess':'2026-11-09T00:03:20+09:00','news':[9],'jobs':[]})
W(news_engine.ARCHIVE,[{'url':'https://l/1','title':'로컬만','date':'2026-11-07'},{'url':'https://both','title':'공통','date':'2026-11-08'}]); W(news_engine.STATE,{'completed':['a']})
r=sr.sync(); assert r['status']=='synced',r
assert R(updater.LIVE)['news']==[1,2] and R(local/'live.local.bak.json')['news']==[9]
arc=R(news_engine.ARCHIVE); assert {a['url'] for a in arc}=={'https://l/1','https://r/1','https://both'} and [a for a in arc if a['url']=='https://both'][0].get('analysis')=='AI' and arc[0]['date']>=arc[-1]['date']
assert len(R(news_engine.STATE)['completed'])==3 and R(career_watch.STATE)=={'x':1}
# 이미 최신 → 변경 없음
assert sr.sync()['status']=='uptodate'
# 원격이 아직 갱신 중이면 받지 않음
W(remote/'live.json',{'status':'updating','lastSuccess':'2026-11-10T00:00:00+09:00'}); assert sr.sync()['status']=='uptodate' and R(updater.LIVE)['news']==[1,2]
# 갱신 잠금 중이면 건너뜀
W(remote/'live.json',{'status':'ok','lastSuccess':'2026-11-10T06:05:00+09:00','news':[7]}); updater.LOCK.write_text('x'); assert sr.sync()['status']=='busy'; updater.LOCK.unlink()
# 원격 파일 없음(404) → 오류, 로컬 데이터 유지
(remote/'live.json').unlink(); r=sr.sync(); assert r['status']=='error' and R(updater.LIVE)['news']==[1,2],r
# 미설정
os.environ['SEMIHUB_REMOTE_REPO']=''; assert sr.sync()['status']=='off' if not sr.CONFIG.exists() else True
# 개인 파일은 동기화 대상에 없음
assert not {'user_data.json','kakao_token.json','kakao_config.json','notify_state.json'} & set(sr.FILES)
# 동기화 후 최근 갱신 판정
assert updater._recent((updater.now()-datetime.timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%S+09:00'),hours=7)
print('PASS sync_remote')
