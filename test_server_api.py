import json, threading, urllib.request, urllib.error, functools
import server, ai_local, user_store, kakao_notify
kakao_notify.configured=lambda *a,**k:False   # 테스트가 실제 카카오톡 전송을 하지 않도록 막음
kakao_notify.send=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('테스트에서 전송 금지'))
from http.server import ThreadingHTTPServer
httpd=ThreadingHTTPServer(('127.0.0.1',8765),server.Handler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
seen={}
server.personal=lambda d,key=None:seen.setdefault('p',d) and 'P분석'
server.career=lambda d,key=None:seen.setdefault('c',d) and {'analysis':'C분석'}
server.mock=lambda d,key=None:seen.setdefault('m',d) and 'M피드백'
user_store.load=lambda *a:{'profile':{'level':'신입','roles':[],'companies':[],'keywords':'rtl'}}
def post(path,body,origin='http://127.0.0.1:8765'):
    r=urllib.request.Request('http://127.0.0.1:8765'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin})
    try:
        with urllib.request.urlopen(r) as x:return x.status,json.loads(x.read())
    except urllib.error.HTTPError as e:return e.code,e.read()[:80]
print(post('/api/ai/personal',{'title':'T'}))
assert post('/api/ai/personal',{'title':'T'})==(200,{'analysis':'P분석'})
assert post('/api/ai/mock',{'question':'q','answer':'a'})==(200,{'feedback':'M피드백'})
assert post('/api/ai/mock',{'q':1},origin='http://evil.com')[0]==403
big={'mode':'connected','job_description':'가'*5000,'news':[{'title':'t','url':'https://a.b','summary':'나'*850}],'profile':{'skills':'다'*600,'experiences':['마'*280]*6},'experience':'바'*1600}
assert len(json.dumps(big,ensure_ascii=False).encode())>24000
assert post('/api/ai/career',big)==(200,{'analysis':'C분석'})            # 큰 AI 취업전략 요청도 통과
assert post('/api/ai/career',{'a':1},origin='http://evil.com')[0]==403
assert post('/api/ai/mock',{'x':'가'*9000})[0]==413                       # 다른 경로는 기존 크기 제한 유지
def get(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765'+path) as x:return x.status
    except urllib.error.HTTPError as e:return e.code
for p in ['/kakao_token.json','/kakao_config.json','/user_data.json','/user_backups/20261105.json','/notify_state.json','/__pycache__/server.cpython-311.pyc','/%75ser_data.json']:
    assert get(p)==403,(p,get(p))                                          # 민감 파일은 브라우저로 못 열게 차단
assert get('/index.html')==200
c,b=post('/api/notify/preview',{}); print(c,b); assert c==200 and 'text' in b
c,b=post('/api/notify/ai-digest',{}); print(c); assert c==400                 # AI 요약을 켜지 않았으면 안내 오류
assert post('/api/notify/ai-digest',{},origin='http://evil.com')[0]==403
c,b=post('/api/notify/test',{}); print(c,b); assert c==400   # 카톡 미설정
print('PASS')
httpd.shutdown()
