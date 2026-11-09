"""2026 semiconductor news archive: permitted RSS metadata only. Python stdlib.

- Google News RSS search for many KR/EN topics and publisher scopes.
- 2026 monthly backfill in small resumable batches.
- Incremental daily noon queries plus analysis for every new title.
- Optional Gemini auto-analysis (explicitly opt-in through GEMINI_API_KEY env).
Never downloads or republishes full publisher articles.
"""
from __future__ import annotations
import calendar,random,urllib.error,datetime,email.utils,hashlib,html,json,os,re,time,urllib.parse,urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE=Path(__file__).resolve().parent
ARCHIVE=BASE/'news_archive.json'
STATE=BASE/'news_state.json'
NEWS_LOCK=BASE/'news_archive.lock'
SEOUL=datetime.timezone(datetime.timedelta(hours=9))
CURRENT_YEAR=2026
START_DATE='2026-01-01'
MAX_ARCHIVE=12000

# Search queries use publicly served Google News RSS; none bypass login/paywalls.
KOREAN_TOPICS=[
 '반도체 HBM4 HBM4E 메모리', '반도체 DDR5 DRAM NAND SSD CXL',
 '반도체 첨단 패키징 하이브리드 본딩 칩렛', '반도체 EUV High-NA 노광 공정',
 '반도체 식각 ALD CVD 증착 장비', '반도체 파운드리 2nm GAA CFET',
 '반도체 검사 계측 수율 결함', '반도체 TSMC 삼성전자 SK하이닉스',
 '반도체 ASML TEL Lam Research AMAT KLA', '반도체 한미반도체 원익IPS 주성엔지니어링',
 '반도체 팹 공장 설비투자 증설 공장', '반도체 수출 규제 공급망 투자',
 '전력반도체 SiC GaN 차량용', '실리콘 포토닉스 CPO 광연결',
 '반도체 AI GPU TPU ASIC 엔비디아', '반도체 소재 웨이퍼 포토레지스트 기판',
 '반도체 OSAT 앰코 ASE 테스팅', '반도체 장비 연구 개발 양산 성과',
]
ENGLISH_TOPICS=[
 'semiconductor chip packaging HBM4 hybrid bonding',
 'semiconductor fab equipment EUV High NA lithography',
 'chip manufacturing etch deposition ALD CVD plasma',
 'semiconductor foundry TSMC Samsung Intel 2nm GAA',
 'semiconductor manufacturing inspection metrology yield',
 'semiconductor memory DRAM NAND HBM Micron SK hynix',
 'semiconductor fab construction capex equipment supply',
 'chiplets interposer 2.5D 3D packaging CoWoS',
 'semiconductor supply chain export controls China',
 'semiconductor silicon photonics co packaged optics CPO',
 'power semiconductor SiC GaN EV equipment',
 'semiconductor design EDA AI GPU accelerator',
]
# Publisher-specific search scopes, to keep domestic + global coverage varied.
# Sources are links to public sites, not assertions that RSS feeds are provided.
PUBLISHERS=[
 ('조선비즈','biz.chosun.com','KR'), ('조선일보','chosun.com','KR'),
 ('전자신문','etnews.com','KR'), ('디일렉','thelec.kr','KR'),
 ('ZDNet Korea','zdnet.co.kr','KR'),('디지털데일리','ddaily.co.kr','KR'),
 ('연합뉴스','yna.co.kr','KR'),('매일경제','mk.co.kr','KR'),
 ('한국경제','hankyung.com','KR'),('서울경제','sedaily.com','KR'),
 ('Reuters','reuters.com','EN'),('Semiconductor Engineering','semiengineering.com','EN'),
 ('EE Times','eetimes.com','EN'),('TrendForce','trendforce.com','EN'),
 ('DigiTimes','digitimes.com','EN'),('Tom’s Hardware','tomshardware.com','EN'),
 ('eeNews Europe','eenewseurope.com','EN'),('IEEE Spectrum','spectrum.ieee.org','EN'),
 ('Semiconductor Digest','semiconductor-digest.com','EN'),
 ('Samsung Semiconductor','news.samsungsemiconductor.com','KR'),
 ('SK hynix Newsroom','news.skhynix.com','EN'),
 ('TSMC','pr.tsmc.com','EN'),('ASML','asml.com','EN'),
 ('Applied Materials','appliedmaterials.com','EN'),
 ('Intel Newsroom','newsroom.intel.com','EN'),
 ('Micron','micron.com','EN'),
]
RSS_FEEDS=[
 ('SK hynix Newsroom','https://news.skhynix.com/en/feed/'),
 ('Samsung Newsroom','https://news.samsung.com/global/feed'),
 # Each may be temporarily unavailable; error recorded, other feeds continue.
 ('Semiconductor Engineering','https://semiengineering.com/feed/'),
 ('Tom’s Hardware','https://www.tomshardware.com/feeds/all'),
]

CATEGORIES={
 '메모리·HBM':['hbm','dram','디램','d램','d램','nand','낸드','memory','메모리','ddr','cxl','ssd','hbf','gddr'],
 '첨단 패키징':['패키징','packaging','bonding','본딩','chiplet','칩렛','interposer','인터포저','cowos','osat','tsv','기판','substrate','bump','범프','fan-out','3d-ic'],
 '노광·리소그래피':['euv','high na','high-na','asml','lithography','노광','photomask','포토마스크','scanner','pellicle','펠리클'],
 '식각·증착·공정':['etch','식각','ald','cvd','증착','deposition','plasma','플라즈마','epitaxy','에피택시','etching'],
 '파운드리·소자':['foundry','파운드리','gaa','cfet','finfet','nanosheet','나노시트','2nm','1.4nm','transistor','트랜지스터','fabless','팹리스'],
 '검사·계측·테스트':['inspection','계측','검사','test equipment','tester','테스터','probe','수율','yield','metrology','defect','결함'],
 'AI·칩설계':['gpu','nvidia','엔비디아','ai chip','ai 반도체','accelerator','가속기','asic','tpu','eda','synopsys','cadence'],
 '광통신·CPO':['photonics','포토닉스','silicon photonics','cpo','optical','광통신','광연결'],
 '전력·차량용':['sic','gan','전력반도체','power semiconductor','automotive chip','차량용 반도체'],
 '공장·장비 투자':['fab ','fab,','팹','공장','plant','투자','capex','equipment','장비','facility','설비','production','생산능력'],
 '산업·정책·공급망':['수출 규제','export control','관세','tariff','chip act','chipse','supply chain','공급망','중국','china','매출','실적','profit','투자'],
}
TOPIC_LINKS={
 'hbm4':['hbm','dram','hbme','hbm4','zhbm','z-hbm'],'hybrid':['hybrid bonding','하이브리드 본딩'],
 'tsv':['tsv','through silicon via'],'cowos':['cowos','chiplet','칩렛','interposer','패키징','packaging'],
 'si':['si/pi','signal integrity','power integrity'],'highna':['high-na','high na','euv','lithography','노광'],
 'gaa':['gaa','2nm','nanosheet','cfet'],'backside':['bspdn','backside power','후면 전력'],
 'cpo':['cpo','photonics','포토닉스'],'cxl':['cxl'],'hbf':['hbf'],'nand':['nand','낸드'],
 'etch':['etch','식각'],'ald':['ald','cvd','증착'],'glass':['유리기판','glass substrate'],
 'pim':['pim','cim'],'thermal':['cooling','thermal','발열','냉각'],
 'inspection':['inspection','metrology','검사','계측'],
}
LEARN={
 '메모리·HBM':('메모리 대역폭과 데이터 이동 효율을 개선하는 기술 경쟁', 'DRAM 셀·메모리 인터페이스 → TSV/적층 → 패키징 연결 → AI 연산 성능', 'HBM·DRAM 구조, 대역폭, TSV, 수율, 발열'),
 '첨단 패키징':('서로 다른 다이를 짧은 연결로 결합해 시스템 성능을 높이는 기술', '칩 제조 → 범프/본딩 → 인터포저·RDL → SI/PI·열/신뢰성 검증', '2.5D·3D, 칩렛, 하이브리드 본딩, SI/PI, 열저항'),
 '노광·리소그래피':('미세 패턴을 정확히 전사하는 노광 및 패턴 형성 기술', '광원·마스크 → 노광광학계(NA) → PR 현상 → 식각·계측', 'EUV, NA, 해상도, DOF, 포토마스크, 오버레이'),
 '식각·증착·공정':('수많은 박막을 증착하고 선택적으로 제거하는 제조 공정', '포토 패턴 → 플라즈마 식각 → 박막 증착/세정 → 결함·균일도 검사', 'ICP/RIE, ALD/CVD, 선택비, 식각 프로파일, 균일도'),
 '파운드리·소자':('공정 미세화와 소자 구조 혁신으로 성능·전력·면적 개선', '트랜지스터 구조 → 배선·전력 공급 → 제조·수율 → 칩 구현', 'FinFET/GAA/CFET, PPA, 공정 노드, 수율'),
 '검사·계측·테스트':('불량을 조기에 찾아 제조 수율과 신뢰성을 높이는 기술', '공정 중 측정 → 결함 검출 → 원인 분석 → 공정 제어·최종 테스트', 'CD-SEM, 오버레이, 웨이퍼 검사, ATE, 수율'),
 'AI·칩설계':('AI 연산 수요가 칩 아키텍처와 메모리·패키징 혁신을 이끄는 현상', 'GPU/ASIC 설계 → 파운드리 생산 → HBM·패키징 → 서버 시스템', 'GPU/TPU, HBM, 칩렛, EDA, 전력 효율'),
 '광통신·CPO':('데이터센터 연결에서 전기 배선의 거리·전력 한계를 광학으로 보완', '광소자·실리콘 포토닉스 → 패키지 통합 → 광전 변환 → 스위치/서버', '광트랜시버, CPO, SI/PI, 열 관리'),
 '전력·차량용':('고전압·고온 환경에서 전력 변환 손실을 줄이는 반도체', 'SiC/GaN 소재 → 소자 제작 → 패키징/방열 → 인버터·충전기', 'SiC MOSFET, GaN HEMT, 항복전압, 방열'),
 '공장·장비 투자':('생산능력 확장은 장비 반입·설치·공정 안정화 후 실제 출하로 이어짐', '클린룸 → 장비 반입·셋업 → 공정 인증 → 수율 램프업 → 양산', 'CAPEX, WPM, 가동률, 램프업, 수율'),
 '산업·정책·공급망':('장비·소재·부품·국가별 공급망이 생산 및 시장 경쟁력에 주는 영향', '투자·규제 → 부품·장비 확보 → 제조능력·가격 → 고용·산업 변화', '반도체 공급망, 수출 규제, 장비 수급, 설비투자'),
}
KEYWORD_FILTER=('반도체','메모리','hbm','dram','nand','웨이퍼','패키징','파운드리','fab','chip','semiconductor','silicon','euv','노광','식각','증착','chiplet','bonding','tsmc','asml','gpu','asic','nvidia','엔비디아','bump','interposer','광통신','micron','microm','intel','semiconductor','공정','전력소자','photonic','cxl','semicon','생산라인','디램')

def now():return datetime.datetime.now(SEOUL)
def load_json(path,default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):return default

def atomic_json(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def clean(value,limit=320):
    s=html.unescape(re.sub(r'<[^>]+>',' ',str(value or '')))
    return re.sub(r'\s+',' ',s).strip()[:limit]

def parse_date(value):
    if not value:return ''
    try:
        d=email.utils.parsedate_to_datetime(value)
        if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
        return d.astimezone(SEOUL).strftime('%Y-%m-%d')
    except Exception:pass
    try:
        d=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
        return d.astimezone(SEOUL).strftime('%Y-%m-%d')
    except Exception:pass
    m=re.search(r'20\d\d[-./]\d\d[-./]\d\d',value)
    return m.group().replace('.','-').replace('/','-') if m else ''

def canon_key(article):
    # Title-based duplicate detection helps when GoogleNews uses redirect URLs.
    title=clean(article.get('title',''),320).casefold()
    title=re.sub(r'\s*[-|–]\s*(?:조선비즈|전자신문|reuters|zdnet korea|thelec|연합뉴스|semiconductor engineering|trendforce)\s*$','',title,flags=re.I)
    title=re.sub(r'[^\w가-힣]+','',title)
    return title[:170]+'|'+str(article.get('date',''))

def classify(title,desc=''):
    s=(title+' '+desc).lower()
    weights={c:sum(1 for token in toks if token.lower() in s) for c,toks in CATEGORIES.items()}
    # Strong technical terms override generic 'equipment'/'production' collisions.
    critical={
       '첨단 패키징':['hybrid bonding','하이브리드 본딩','cowos','interposer','인터포저','패키징','packaging','chiplet','tc 본더'],
       '노광·리소그래피':['high-na','high na','euv','lithography','노광'],
       '메모리·HBM':['hbm','dram','nand','낸드','디램','z-hbm','zhbm'],
       '광통신·CPO':['photonics','포토닉스','cpo','광연결'],
       '식각·증착·공정':['plasma etch','ald','cvd','식각','증착'],
       '검사·계측·테스트':['metrology','계측','inspection','반도체 검사'],
    }
    for c, terms in critical.items():
        weights[c]+=3*sum(1 for t in terms if t in s)
    cat=max(weights,key=weights.get) if max(weights.values()) else '반도체 산업'
    linked=[id for id,aliases in TOPIC_LINKS.items() if any(a in s for a in aliases)][:6]
    return cat,linked

def educational_note(article):
    category=article.get('category','반도체 산업')
    explain,process,keywords=LEARN.get(category,('반도체 기술과 시장 변화가 제조 공정 및 산업 생태계에 미치는 영향','기술 발표 → 제조·장비·공급망 → 관련 산업','반도체 공정, 패키징, 메모리, 설비투자'))
    related=', '.join(article.get('topics',[])) or keywords
    return (f'■ 이 기사와 연결해 공부할 개념\n{explain}\n\n'
            f'■ 제조·장비와 연결되는 흐름\n{process}\n\n'
            f'■ 핵심 키워드\n{related}\n\n'
            '※ 이 설명은 기사 본문을 읽고 요약한 것이 아니라 제목과 분류 키워드로 만든 기초 학습 가이드입니다. '
            '실제 사건의 세부 내용·수치·확정 여부는 원문을 확인하세요.')

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'SEMI-HUB/6.0 Educational RSS reader (public metadata only)', 'Accept':'application/rss+xml,application/atom+xml,application/xml,text/xml,*/*'})
    last=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=15) as response:
                return response.read(1800000)
        except urllib.error.HTTPError as e:
            last=e
            if e.code not in (429,500,502,503,504):raise
        except (urllib.error.URLError,TimeoutError,OSError) as e:
            last=e
        time.sleep(2*(attempt+1)+random.random())
    raise last

def parse_feed(raw,fallback='뉴스 검색',query_name=''):
    root=ET.fromstring(raw)
    results=[]
    if root.tag.endswith('feed'):
        ns={'a':'http://www.w3.org/2005/Atom'}
        for node in root.findall('a:entry',ns):
            link=''
            for a in node.findall('a:link',ns):
                if a.get('rel','alternate')=='alternate':link=a.get('href','');break
            results.append((node.findtext('a:title',default='',namespaces=ns),link,node.findtext('a:published',default='',namespaces=ns) or node.findtext('a:updated',default='',namespaces=ns),node.findtext('a:summary',default='',namespaces=ns),fallback))
    else:
        for node in root.findall('.//item'):
            source=node.find('source')
            provider=clean(source.text,90) if source is not None and source.text else fallback
            results.append((node.findtext('title') or '',node.findtext('link') or '',node.findtext('pubDate') or '',node.findtext('description') or '',provider))
    rows=[]
    for title,link,pub,desc,provider in results:
        title=clean(title,240)
        desc=clean(desc,160)
        link=link.strip()
        date=parse_date(pub)
        if not (title and date and link.startswith('https://')):continue
        if not (date>=START_DATE and date<=now().strftime('%Y-%m-%d')):continue
        # Search results are usually relevant, but reject unrelated false positives.
        body=(title+' '+desc).lower()
        if not any(term in body for term in KEYWORD_FILTER):continue
        # Publisher appended to title sometimes; source field takes precedence.
        if provider=='뉴스 검색' and ' - ' in title:
            guess=title.rsplit(' - ',1)[-1]
            if 2<=len(guess)<=52:provider=guess
        category,topics=classify(title,desc)
        article={'id':'a'+hashlib.sha1((title+date+link).encode('utf-8')).hexdigest()[:16],
                 'title':title,'url':link,'date':date,'source':provider,'company':provider,
                 'category':category,'topics':topics,'summary':desc[:150],
                 'lang':'ko' if re.search('[가-힣]',title) else 'en',
                 'kind':'RSS 기사','discoveredAt':now().isoformat(timespec='seconds'),
                 'querySource':query_name,'analysisMode':'키워드 기반 학습 가이드'}
        article['education']=educational_note(article)
        rows.append(article)
    return rows

def query_specs():
    specs=[]
    for ix,q in enumerate(KOREAN_TOPICS):specs.append(('kr-topic-'+str(ix),q,'KR'))
    for ix,q in enumerate(ENGLISH_TOPICS):specs.append(('en-topic-'+str(ix),q,'EN'))
    for name,host,locale in PUBLISHERS:
        q=('반도체 OR HBM OR EUV OR 파운드리 OR 패키징' if locale=='KR' else 'semiconductor OR chip OR HBM OR lithography OR packaging')
        specs.append(('pub-'+host,'site:'+host+' ('+q+')',locale))
    return specs

def url_for(query,locale,after,before):
    region={'KR':('ko','KR','KR:ko'),'EN':('en-US','US','US:en')}[locale]
    q=f'{query} after:{after} before:{before}'
    return 'https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':region[0],'gl':region[1],'ceid':region[2]})

def monthly_tasks():
    tasks=[]
    date=now().date()
    months=[(y,m) for y in range(CURRENT_YEAR,date.year+1) for m in range(1,13) if datetime.date(y,m,1)<=date]
    for y,month in reversed(months):
        for code,q,region in query_specs():
            first=datetime.date(y,month,1)
            end=datetime.date(y+month//12,(month%12)+1,1)
            key=code+'-'+(str(month).zfill(2) if y==CURRENT_YEAR else f'{y}{month:02d}')
            tasks.append((key,url_for(q,region,str(first),str(end)),code))
    return tasks

def daily_tasks():
    # Regular crawl: now minus 4 days to tomorrow so outages can be retried.
    today=now().date()
    start=str(today-datetime.timedelta(days=4))
    end=str(today+datetime.timedelta(days=1))
    tasks=[('fresh-'+k,url_for(q,loc,start,end),k) for k,q,loc in query_specs()]
    tasks += [('direct-'+str(i),url,'RSS') for i,(_,url) in enumerate(RSS_FEEDS)]
    return tasks

def run_tasks(tasks,workers=3):
    rows=[];errors=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future={pool.submit(fetch,url):(key,label) for key,url,label in tasks}
        for task in as_completed(future):
            key,label=future[task]
            try: rows.extend(parse_feed(task.result(),fallback=label,query_name=key))
            except Exception as e:errors.append(f'{key}: {type(e).__name__}')
    return rows,errors

def merge(older,newer):
    data={canon_key(r):r for r in older if r.get('date','')>=START_DATE and r.get('url')}
    added=[]
    for row in sorted(newer,key=lambda n:n.get('date','')):
        key=canon_key(row)
        if key not in data:
            data[key]=row
            added.append(row['id'])
        else:
            existing=data[key]
            # Preserve an existing richer analysis. Prefer direct news link over Google News redirect.
            if 'news.google.com/' in str(existing.get('url','')) and 'news.google.com/' not in row['url']:
                for f in ('url','source','company'):existing[f]=row[f]
    arr=sorted(data.values(),key=lambda r:(r.get('date',''),r.get('discoveredAt','')),reverse=True)[:MAX_ARCHIVE]
    return arr,added

def auto_ai_analysis(archive,added_ids,max_per_run=12):
    import ai_local
    if not (os.environ.get('GEMINI_API_KEY','').strip() or ai_local.API_KEY):return {'ai':0,'reason':'무료 AI 키 미설정 — 모든 기사에 규칙 기반 기초 기술 설명 적용'}
    analyze=ai_local.analyze
    # New articles first; remaining backlog fills unused quota. Never rewrite completed.
    byid={r['id']:r for r in archive}
    queue=[byid[k] for k in added_ids if k in byid]
    queue.extend([r for r in archive if r['id'] not in set(added_ids)])
    attempts=0;success=0;error=''
    for row in queue:
        if row.get('aiAnalysis') or attempts>=max_per_run:continue
        attempts+=1
        try:
            result=analyze({'title':row['title'],'date':row['date'],'summary':row.get('summary',''),
                            'source':row.get('source',''),'topics':[]})
            row['aiAnalysis']=result
            row['analysisMode']='Gemini AI 자동 분석'
            row['analyzedAt']=now().isoformat(timespec='seconds')
            success+=1
        except Exception as exc:
            error=str(exc)[:160]
            if '429' in error or '한도' in error or '권한' in error or '401' in error or '403' in error:break
    return {'ai':success,'attempts':attempts,'aiError':error}

def _update_news(backfill_count=25,only_backfill=False,auto_ai=True):
    state=load_json(STATE,{'completed':[],'history':[]})
    archive=load_json(ARCHIVE,[])
    completed=set(state.get('completed',[]))
    all_months=monthly_tasks()
    remaining=[t for t in all_months if t[0] not in completed]
    selection=remaining[:max(0,backfill_count)]
    fresh=[];errors=[]
    if not only_backfill: fresh,errors=run_tasks(daily_tasks())
    older,old_errors=run_tasks(selection)
    errors+=old_errors
    # Retries failed months; successful scans recorded even if no matches.
    failed={e.split(':',1)[0] for e in old_errors}
    completed.update(k for k,_,_ in selection if k not in failed)
    archive,added=merge(archive,fresh+older)
    analysis=auto_ai_analysis(archive,added,int(os.environ.get('AUTO_AI_MAX','12'))) if auto_ai else {'ai':0}
    atomic_json(ARCHIVE,archive)
    state.update({'completed':sorted(completed),'totalBackfillTasks':len(all_months),'remainingBackfillTasks':len(all_months)-len(completed),
                  'lastAttempt':now().isoformat(timespec='seconds'),'lastSuccess':now().isoformat(timespec='seconds') if fresh or older else state.get('lastSuccess'),
                  'articleCount':len(archive),'newArticles':len(added),'errors':errors[:35],'ai':analysis,
                  'queryCount':len(daily_tasks()) if not only_backfill else 0})
    atomic_json(STATE,state)
    return {'articles':len(archive),'added':len(added),'backfillRemaining':state['remainingBackfillTasks'],'backfillTotal':len(all_months),'freshResults':len(fresh),'backfillResults':len(older),'errors':errors[:8],**analysis}

def update_news(backfill_count=25,only_backfill=False,auto_ai=True):
    """Avoid simultaneous scheduler/manual updates overwriting the same archive."""
    try:
        fd=os.open(str(NEWS_LOCK),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.close(fd)
    except FileExistsError:
        try:
            if time.time()-NEWS_LOCK.stat().st_mtime>3600:
                NEWS_LOCK.unlink(missing_ok=True)
                return update_news(backfill_count,only_backfill,auto_ai)
        except OSError:pass
        state=load_json(STATE,{})
        return {'status':'busy','articles':len(load_json(ARCHIVE,[])),
                'added':0,'backfillRemaining':state.get('remainingBackfillTasks',0),
                'errors':['다른 뉴스 수집 작업이 진행 중입니다.']}
    try:
        return _update_news(backfill_count,only_backfill,auto_ai)
    finally:
        NEWS_LOCK.unlink(missing_ok=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--backfill',action='store_true',help='Only historic 2026 month-by-month backfill, resumable')
    p.add_argument('--batch',type=int,default=40,help='Monthly backfill searches per run')
    p.add_argument('--no-ai',action='store_true')
    args=p.parse_args()
    print(json.dumps(update_news(backfill_count=args.batch,only_backfill=args.backfill,auto_ai=not args.no_ai),ensure_ascii=False,indent=2))
