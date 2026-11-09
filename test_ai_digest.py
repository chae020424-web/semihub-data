import datetime, json
import ai_digest as ad, personal_notify as pn, updater
T=datetime.date(2026,11,5)
roles=[{'id':'r1','name':'RTL 설계','category':'설계','tags':'rtl verilog soc'}]
user={'profile':{'level':'신입','roles':['r1'],'companies':[],'skills':'Verilog 비밀기술','keywords':'hbm','aiDigest':True,'aiConsent':False},'exp':[{'title':'비밀경험'}]}
pn.make_profile.__defaults__  # 존재 확인
news=[{'title':'HBM4 RTL 설계 인력 수요','summary':'요약','category':'설계','date':'2026-11-04','url':'https://a/1'},
      {'title':'HBM 공정 뉴스','summary':'요약','category':'설계','date':'2026-11-05','url':'https://a/2'},
      {'title':'HBM 패키징','summary':'요약','category':'설계','date':'2026-11-05','url':'https://a/3'},
      {'title':'오래된 HBM 기사','summary':'x','category':'설계','date':'2026-10-01','url':'https://a/4'},
      {'title':'HBM http 링크','summary':'x','category':'설계','date':'2026-11-05','url':'http://a/5'}]
jobs=[{'company':'SK하이닉스','title':'RTL 설계','deadline':'2026-12-01'},{'company':'X','title':'RTL 만료','deadline':'2026-10-01'}]
# make_profile 은 roles.json 을 읽으므로 테스트용 roles 주입
orig=pn.make_profile; pn.make_profile=lambda u,r=None,c=None: orig(u,roles,[])
seen=[]
def gen(prompt): seen.append(prompt); return '핵심 사실입니다\n영향은 추정입니다\n오늘 할 일: 복습'+'가'*400
# 1) 꺼짐/프로필 없음
assert ad.make_messages({'profile':{}},news,jobs,T,{})==([],[])
off=json.loads(json.dumps(user)); off['profile']['aiDigest']=False
assert ad.run(off,news,jobs,{},lambda *a:1/0,T,gen)==0
# 2) 동의 없음: 기술·경험 미전송, 만료 공고 제외, 2건·200자 이내
msgs,urls=ad.make_messages(user,news,jobs,T,{},gen)
assert len(msgs)==2 and all(len(m)<=200 for m,_ in msgs),[len(m) for m,_ in msgs]
assert all('비밀' not in p for p in seen),'동의 없이 개인 정보 전송'
assert 'RTL 만료' not in seen[0] and 'RTL 설계' in seen[0]
assert all(u.startswith('https://') for u in urls) and 'https://a/4' not in urls
# 3) 동의 있음: 기술·경험 포함
seen.clear(); user['profile']['aiConsent']=True
ad.make_messages(user,news,jobs,T,{},gen); assert any('비밀기술' in p for p in seen) and any('비밀경험' in p for p in seen)
# 4) 실행: 중복 방지·하루 4건 제한·다음날 초기화
sent=[]; st={}
assert ad.run(user,news,jobs,st,lambda m,l:sent.append(m),T,gen)==2
assert ad.run(user,news,jobs,st,lambda m,l:sent.append(m),T,gen)==1   # 남은 기사 1건(a/3 또는 a/2) — 이미 보낸 기사는 제외
assert ad.run(user,news,jobs,st,lambda m,l:sent.append(m),T,gen)==0   # 더 보낼 기사 없음
assert len(sent)==3 and len(set(st['aiDigestIds']))==3
many=[{'title':'HBM RTL %d'%i,'summary':'s','category':'설계','date':'2026-11-05','url':'https://m/%d'%i} for i in range(10)]
st={}; n=sum(ad.run(user,many,jobs,st,lambda m,l:None,T,gen) for _ in range(5)); assert n==4 and st['aiDigestCount']==4   # 하루 최대 4건
assert ad.run(user,many,jobs,st,lambda m,l:None,T+datetime.timedelta(days=1),gen)==2                                       # 다음날 다시
# 5) 키 없음 → 예외 전달(날짜·기사 기록 안 함), notify_personal 은 삼키고 다른 알림 계속
def nokey(p): raise ValueError('키 없음')
st={}
try: ad.run(user,news,jobs,st,lambda *a:None,T,nokey); assert 0
except ValueError: pass
assert not st.get('aiDigestIds')
out=[]; pn.notify_personal(user,news,st,lambda m,l:out.append(m),today=T,jobs=jobs)   # 예외 없이 끝나야 함
# 6) 갱신 간격: 5시간 이내면 건너뜀
now=updater.now()
ts=lambda h:(now-datetime.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%S+09:00')
assert updater._recent(ts(1)) and updater._recent(ts(4.9)) and not updater._recent(ts(5.1)) and not updater._recent(ts(7)) and not updater._recent(None) and not updater._recent('x')
print('PASS ai_digest')
