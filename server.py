"""Local-only SEMI-HUB web server. No public deployment or account required."""
from __future__ import annotations
import json,os,sys,subprocess,threading,time,datetime,webbrowser,urllib.parse
from functools import partial
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler

from updater import run_update,load_live,recover_stale,mark_interrupted,notify_now,_recent
import sync_remote
from career_ai import career
from ai_local import set_key, analyze, personal, mock
import user_store
from news_engine import ARCHIVE as NEWS_ARCHIVE, STATE as NEWS_STATE, load_json, query_specs, PUBLISHERS, RSS_FEEDS, update_news
BASE=Path(__file__).resolve().parent
HOST='127.0.0.1';PORT=8765
seoul=datetime.timezone(datetime.timedelta(hours=9), name='KST')
active=threading.Lock()
UPDATE_TIMEOUT=1500   # 25분 안에 끝나지 않으면 갱신을 강제 종료(한 곳에서 멈춰도 서버가 계속 막히지 않도록)
def run_update_guarded(force,cmd=None,timeout=UPDATE_TIMEOUT):
    """갱신을 별도 프로세스로 실행하고 시간 제한을 둔다. 반환: 'done' | 'timeout'."""
    cmd=cmd or [sys.executable,str(BASE/'updater.py')]+(['--force'] if force else [])
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    p=subprocess.Popen(cmd,cwd=str(BASE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=env)
    try:
        out,_=p.communicate(timeout=timeout)
        return 'done:'+(out or '')[-1200:]
    except subprocess.TimeoutExpired:
        p.kill()
        try:p.communicate(timeout=10)
        except Exception:pass
        mark_interrupted('갱신이 %d분 안에 끝나지 않아 중단했습니다(접속이 멈춘 사이트가 있을 수 있음). 다음 갱신에서 다시 시도합니다.'%(timeout//60))
        return 'timeout'
def start_update(force,backfill_only=False):
    if not active.acquire(blocking=False):return False
    def work():
        try:
            print('[SEMI-HUB] update started')
            print('[SEMI-HUB] update result:',update_news(backfill_count=70,only_backfill=True) if backfill_only else run_update_guarded(force))
        finally:active.release()
    threading.Thread(target=work,daemon=True).start()
    return True
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(BASE),**kwargs)
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if self.headers.get('Host','').split(':')[0].lower() not in ('127.0.0.1','localhost'):
            self.send_error(403);return
        if path=='/api/live':
            body=json.dumps(load_live(),ensure_ascii=False).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        elif path=='/api/technews':
            archive=load_json(NEWS_ARCHIVE,[])
            progress=load_json(NEWS_STATE,{})
            self.send_json(200,{'articles':archive,'status':progress,'publisherCount':len(PUBLISHERS),
                                'queryCount':len(query_specs()),'feedCount':len(RSS_FEEDS)})
        elif path=='/api/store/backups':
            origin=self.headers.get('Origin','')
            if origin and origin not in (f'http://{HOST}:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403);return
            self.send_json(200,{'backups':user_store.list_backups()})
        elif path=='/api/store/backup':
            origin=self.headers.get('Origin','')
            if origin and origin not in (f'http://{HOST}:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403);return
            name=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('name',[''])[0]
            data=user_store.read_backup(name)
            if data is None:self.send_json(404,{'error':'해당 백업이 없습니다.'})
            else:self.send_json(200,{'data':data})
        elif path=='/api/store':
            origin=self.headers.get('Origin','')
            if origin and origin not in (f'http://{HOST}:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403);return
            self.send_json(200,{'data':user_store.load()})
        elif path=='/api/health':
            body=b'{"ok":true,"mode":"local"}'
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
        else:
            name=Path(urllib.parse.unquote(path)).name.lower()
            if name in ('kakao_config.json','kakao_token.json','user_data.json','.env','notify_state.json','update.lock') or path.startswith('/user_backups/') or '/__pycache__/' in path:
                self.send_error(403);return
            super().do_GET()
    def send_json(self,status,object):
        data=json.dumps(object,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path
        if self.headers.get('Host','').split(':')[0].lower() not in ('127.0.0.1','localhost'):
            self.send_error(403);return
        origin=self.headers.get('Origin','')
        if origin and origin not in (f'http://{HOST}:{PORT}',f'http://localhost:{PORT}'):
            self.send_error(403);return
        if path in ('/api/update','/api/news/backfill'):
            started=start_update(force=True,backfill_only=(path=='/api/news/backfill'))
            self.send_json(202 if started else 409,{'started':started,'busy':not started});return
        if path=='/api/store':
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<2 or length>user_store.MAX_BYTES:
                    self.send_json(413,{'error':'요청 크기가 올바르지 않습니다.'});return
                body=json.loads(self.rfile.read(length).decode('utf-8'))
                status,current=user_store.save(body.get('data') if isinstance(body,dict) else None)
            except (ValueError,KeyError):
                self.send_json(400,{'error':'JSON 형식 오류'});return
            if status=='ok':self.send_json(200,{'ok':True})
            elif status=='conflict':self.send_json(409,{'conflict':True,'data':current})
            else:self.send_json(400,{'error':'저장할 수 없는 데이터입니다.'})
            return
        if path in ('/api/notify/preview','/api/notify/test','/api/notify/ai-digest'):
            self.handle_notify(path);return
        if path not in ('/api/ai/key','/api/ai/analyze','/api/ai/personal','/api/ai/mock','/api/ai/career'):
            self.send_error(404);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>(64000 if path=='/api/ai/career' else 24000):
                self.send_json(413,{'error':'요청 크기가 올바르지 않습니다.'});return
            data=json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(data,dict):raise ValueError('JSON object required')
            if path=='/api/ai/key':
                set_key(data.get('key',''))
                self.send_json(200,{'ok':True});return
            if path=='/api/ai/career':
                self.send_json(200,career(data));return
            if path=='/api/ai/mock':
                self.send_json(200,{'feedback':mock(data)});return
            if path=='/api/ai/personal':
                self.send_json(200,{'analysis':personal(data)});return
            result=analyze(data)
            self.send_json(200,{'analysis':result,'mode':'Gemini free API; title-and-summary context only'})
        except (ValueError,KeyError) as e:
            self.send_json(400,{'error':str(e)[:400]})
        except Exception as e:
            print('[SEMI-HUB AI] request failed:',type(e).__name__)
            self.send_json(502,{'error':'AI API 연결 실패 ('+type(e).__name__+'). 네트워크 및 키를 확인해 주세요.'})
    def handle_notify(self,path):
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length:self.rfile.read(min(length,4096))
            import personal_notify, kakao_notify
            if path=='/api/notify/test':
                if not kakao_notify.configured():
                    self.send_json(400,{'error':'카카오톡이 아직 연결되지 않았습니다. setup_kakao_windows.bat 를 먼저 실행해 주세요.'});return
                kakao_notify.send('[SEMI-HUB] 테스트 알림입니다. 내 프로필 기준 알림이 이 방식으로 도착합니다.')
                self.send_json(200,{'ok':True});return
            if path=='/api/notify/ai-digest':
                import ai_digest,datetime
                live=load_live() or {}
                news=(load_json(NEWS_ARCHIVE,[]) or [])+(load_json(Path(__file__).resolve().parent/'tech-news.json',[]) or [])
                user=user_store.load() or {}
                if not ai_digest.enabled(user):
                    self.send_json(400,{'error':'내 프로필·스펙에서 「AI 취업전략 카톡 요약」을 먼저 켜 주세요.'});return
                msgs,_=ai_digest.make_messages(user,news,live.get('jobs',[]),datetime.date.today(),{})
                self.send_json(200,{'text':'\n\n'.join(m for m,_l in msgs),'consent':ai_digest.consented(user)});return
            live=load_live() or {}
            news=(load_json(NEWS_ARCHIVE,[]) or [])+(load_json(Path(__file__).resolve().parent/'tech-news.json',[]) or [])
            text=personal_notify.preview(user_store.load(),news,live.get('jobs',[]))
            self.send_json(200,{'text':text})
        except Exception as e:
            print('[SEMI-HUB notify] failed:',type(e).__name__)
            self.send_json(502,{'error':'알림 처리 실패 ('+type(e).__name__+'): '+str(e)[:160]})
    def log_message(self,format,*args):
        if '/api/live' not in str(args[0] if args else ''):super().log_message(format,*args)

UPDATE_HOURS=(0,6,12,18)   # 한국시간, 6시간마다
def noon_runner():
    last_trigger=None
    while True:
        t=datetime.datetime.now(seoul)
        key=(t.date(),t.hour)
        if t.hour in UPDATE_HOURS and t.minute==0 and last_trigger!=key:
            last_trigger=key
            if sync_remote.configured():
                # GitHub 가 대신 수집해 둔 데이터가 최근 것이면 노트북에서 다시 긁지 않는다
                remote_sync()
                if _recent(load_live().get('lastSuccess'),hours=7):continue
            start_update(force=False)
        time.sleep(15)

def remote_sync():
    """GitHub 에서 최신 데이터를 받고, 새로 받았다면 카톡 알림도 보낸다."""
    try:
        r=sync_remote.sync()
        print('[SEMI-HUB] GitHub 동기화:',r.get('status'),r.get('remote') or r.get('error') or '')
        if r.get('status')=='synced':
            try:notify_now(load_live())
            except Exception as e:print('[SEMI-HUB] 알림 건너뜀:',type(e).__name__)
        return r
    except Exception as e:
        print('[SEMI-HUB] 동기화 실패:',type(e).__name__);return {'status':'error'}
def remote_sync_runner():
    time.sleep(6)
    while True:
        remote_sync()
        time.sleep(3600)
if __name__=='__main__':
    try:
        if recover_stale():print('[SEMI-HUB] 멈춰 있던 이전 갱신을 정리했습니다.')
    except Exception as e:print('[SEMI-HUB] stale check skipped:',type(e).__name__)
    threading.Thread(target=noon_runner,daemon=True).start()
    if sync_remote.configured():threading.Thread(target=remote_sync_runner,daemon=True).start()
    httpd=None
    for candidate_port in range(8765,8770):
        try:
            PORT=candidate_port
            httpd=ThreadingHTTPServer((HOST,PORT),Handler)
            break
        except OSError:
            continue
    if httpd is None:
        raise OSError('사용 가능한 로컬 포트(8765~8769)가 없습니다. 기존 실행 창을 종료해주세요.')
    url=f'http://{HOST}:{PORT}'
    print('SEMI-HUB v6:',url)
    print('서버를 계속 켜두면 한국시간 0·6·12·18시(6시간마다) 자동 수집이 시작됩니다.')
    webbrowser.open(url)
    try:httpd.serve_forever()
    except KeyboardInterrupt:print('Server stopped')
    finally:httpd.server_close()
