import datetime, json, tempfile
from pathlib import Path
import personal_notify as pn, kakao_notify as k
roles=[{'id':'r1','category':'설계','name':'RTL','tags':'rtl verilog ic'},{'id':'r2','category':'공정','name':'공정','tags':'etch 식각'}]
cos=[{'id':'samsung','name':'삼성전자'},{'id':'sk','name':'SK하이닉스'}]
user={'profile':{'level':'신입','roles':['r1'],'companies':['sk'],'skills':'','keywords':'DFT'},
 'apps':[{'id':'a1','company':'삼성전자','title':'DS 설계','status':'준비중','deadline':'2026-11-06','stages':[{'name':'코딩테스트','date':'2026-11-04','result':'대기'},{'name':'서류','date':'2026-11-04','result':'합격'}]},
         {'id':'a2','company':'X','title':'t','status':'불합격','deadline':'2026-11-06'}],
 'grad':[{'id':'g1','school':'연세대','program':'시스템반도체','deadline':'2026-11-04'}],
 'certs':[{'id':'c1','name':'TOEIC','date':'2024-11-06','valid':2}]}
p=pn.make_profile(user,roles,cos); assert p['has'] and 'rtl' in p['terms'] and 'dft' in p['terms'] and p['companies']==['sk하이닉스']
J=lambda **kw:dict({'company':'A','title':'','level':'신입'},**kw)
assert pn.match_job(J(title='RTL Design Engineer'),p)
assert not pn.match_job(J(title='Customer Service Manager'),p)       # 'ic' 가 service 에 걸리지 않음
assert pn.match_job(J(company='SK하이닉스',title='생산'),p)
assert not pn.match_job(J(title='RTL',level='경력'),p)
assert pn.match_job(J(title='Sales'),pn.make_profile({},roles,cos))   # 필터 없음 → 전체
today=datetime.date(2026,11,3)
al=pn.dday_alerts(user,today); txt=[t for _,t in al]; print(txt)
assert len(al)==4 and any('D-3 삼성전자' in t for t in txt) and any('코딩테스트' in t for t in txt) and any('연세대' in t for t in txt) and any('TOEIC' in t for t in txt)
assert not any('X' in t.split()[2:3] for t in txt)                      # 불합격 지원은 제외
assert pn.dday_alerts(user,today,seen=[k_ for k_,_ in al])==[]
news=[{'id':'n1','date':'2026-11-02','title':'SK하이닉스 HBM4 양산','summary':'rtl 설계 인력','category':'설계','company':'SK하이닉스'},
      {'id':'n2','date':'2026-10-01','title':'오래된 기사','category':'설계','company':'SK하이닉스'},
      {'id':'n3','date':'2026-11-02','title':'무관 기사','category':'장비','company':'기타'}]
m,ids=pn.news_digest(news,p,today); print(m); assert ids==['n1'] and len(m)<=200
sent=[]; snd=lambda t,l=None:sent.append(t); st={}
assert pn.notify_personal(user,news,st,snd,today,roles,cos)==(4,1) and len(sent)==2
assert pn.notify_personal(user,news,st,snd,today,roles,cos)==(0,0) and len(sent)==2   # 중복 없음
print(pn.preview(user,news,[J(title='RTL Engineer'),J(title='Sales')],today,roles,cos))
# kakao_notify 통합: 공고 필터
d=Path(tempfile.mkdtemp()); sp=d/'s.json'; sent.clear()
jobs=[{'id':'1','company':'A','title':'RTL 설계','level':'신입'}]
prof=pn.make_profile(user,roles,cos)
k.notify_updates(jobs,{},state_path=sp,sender=snd,user=user,profile=prof,today=today)
jobs2=jobs+[{'id':'2','company':'B','title':'RTL Engineer','level':'신입'},{'id':'3','company':'C','title':'Customer Service','level':'신입'}]
r=k.notify_updates(jobs2,{},state_path=sp,sender=snd,user=user,profile=prof,today=today)
print(r,sent); assert r==(1,0) and 'B' in sent[0] and 'Customer' not in sent[0]
print('PASS')
