"""SEMI-HUB authorized public RSS + optional Work24 API updater.
Start every 6 hours (00/06/12/18 KST) with a running server or Windows Task Scheduler.
No login bypass or scraping of recruiting websites; write only RSS headlines+links
and approved Work24 OpenAPI public listings.
"""
from __future__ import annotations
import json, os, sys, time, urllib.parse, urllib.request, datetime, email.utils, re, traceback
from pathlib import Path
from xml.etree import ElementTree as ET
from news_engine import update_news


BASE=Path(__file__).resolve().parent
LIVE=BASE/'live.json'
LOCK=BASE/'update.lock'
SEOUL=datetime.timezone(datetime.timedelta(hours=9), name='KST')
USER_AGENT='SEMI-HUB/4.0 (personal-education RSS reader; compatible RSS consumer)'


def now(): return datetime.datetime.now(SEOUL)
def timestamp():return now().strftime('%Y-%m-%dT%H:%M:%S+09:00')
def load_live():
    try: return json.loads(LIVE.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {'status':'not_started','lastSuccess':None,'news':[],'jobs':[]}
def save_live(data):
    tmp=LIVE.with_suffix('.new')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(LIVE)
def get_url(url,timeout=15):
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/xml, text/xml, */*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(1200000)
def clean_url(s):
    if not isinstance(s,str) or not s.startswith('https://'): return ''
    return s[:2000]
def company_matches(title,companies):
    simple=title.lower().replace(' ','').replace('㈜','')
    # longest first avoids one company matching another company's prefix
    names=sorted(((c['name'],c['id']) for c in companies),key=lambda x:-len(x[0]))
    for name,id in names:
        test=name.lower().replace(' ','').replace('㈜','')
        if len(test)>2 and test in simple:
            return name
    return ''
def clean_dt(s):
    try: return email.utils.parsedate_to_datetime(s).astimezone(SEOUL).strftime('%Y-%m-%d %H:%M')
    except (ValueError,TypeError):return ''
def parse_news_rss(xml,companies):
    root=ET.fromstring(xml)
    items=[]
    for it in root.findall('.//item'):
        title=(it.findtext('title') or '').strip()[:250]
        url=clean_url((it.findtext('link') or '').strip())
        if not title or not url:continue
        date=clean_dt(it.findtext('pubDate') or '')
        src=it.find('source')
        provider=(src.text or '').strip() if src is not None else 'Google 뉴스 RSS'
        company=company_matches(title,companies)
        items.append({'title':title,'url':url,'date':date,'company':company,'source':provider})
    return items

def load_company_list():
    return json.loads((BASE/'companies.json').read_text(encoding='utf-8'))['companies']

def load_env():
    # Keep keys outside public-served folder: only environment variables.
    return os.environ.get('WORK24_API_KEY','').strip()

def collect_news(companies):
    # Batch search, not 106 separate websites. RSS may be temporarily unavailable.
    names=[]
    for c in companies:
        n=c['name']
        if n=='앰코테크놀로지코리아':n='앰코테크놀로지코리아'
        names.append(n)
    result=[];errors=[]
    for i in range(0,len(names),6):
        chunk=names[i:i+6]
        query='('+' OR '.join('"'+n.replace('"','')+'"' for n in chunk)+') (반도체 OR semiconductor) when:7d'
        rss='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'ko','gl':'KR','ceid':'KR:ko'})
        try:
            result.extend(parse_news_rss(get_url(rss),companies))
        except Exception as exc:
            errors.append(f'RSS batch {i//6+1}: {type(exc).__name__}')
        time.sleep(.25)
    seen=set();unique=[]
    for item in sorted(result,key=lambda x:x['date'],reverse=True):
        ident=(item['title'].strip().lower(),item['url'])
        if ident in seen:continue
        seen.add(ident);unique.append(item)
    return unique[:350],errors

def child(elem,key):
    return (elem.findtext(key) or '').strip()
def parse_work24_xml(xml):
    root=ET.fromstring(xml)
    # A rejection or API error must never be mistaken for zero available positions.
    if root.find('.//error') is not None:
        raise ValueError('Work24 API returned an error')
    rows=[]
    for w in root.findall('.//wanted'):
        url=clean_url(child(w,'wantedInfoUrl') or child(w,'wantedMobileInfoUrl'))
        title=child(w,'title')
        if not title or not url:continue
        rows.append({'title':title[:250],'company':child(w,'company'),'date':child(w,'regDt'),
                     'deadline':child(w,'closeDt'),'location':child(w,'region'),
                     'salary':child(w,'sal'), 'url':url,'source':'고용24 OpenAPI'})
    return rows

def collect_work24(key):
    if not key:return [],['고용24 API 키 없음 — 실제 채용공고 수집 비활성']
    url='https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do'
    all_rows=[];errors=[]
    for keyword in ['반도체','반도체 장비','반도체 패키징','식각','증착']:
        qs={'authKey':key,'callTp':'L','returnType':'XML','startPage':1,'display':100,'regDate':'M-1','keyword':keyword}
        try:
            all_rows.extend(parse_work24_xml(get_url(url+'?'+urllib.parse.urlencode(qs))))
        except Exception as exc:errors.append(f'고용24 {keyword}: {type(exc).__name__}')
        time.sleep(.25)
    dedup={r['url']:r for r in all_rows}
    return list(dedup.values())[:250],errors

STALE_LOCK_SEC=2400   # 갱신은 보통 3분 안팎 → 40분 넘은 잠금 파일은 멈춘 것으로 보고 정리
def mark_interrupted(reason):
    cur=load_live();cur['status']='error';cur['lastAttempt']=timestamp();cur['errors']=[reason]
    save_live(cur);LOCK.unlink(missing_ok=True)
def recover_stale():
    """멈춘 갱신 정리: 오래된 update.lock 삭제, '갱신 중'으로 남은 상태를 오류로 표시. 정리했으면 True."""
    try:
        age=time.time()-LOCK.stat().st_mtime
    except OSError:
        age=None
    if age is not None and age>STALE_LOCK_SEC:
        mark_interrupted('이전 갱신이 %d분 넘게 끝나지 않아 중단 처리했습니다. 다음 갱신에서 다시 시도합니다.'%(age//60));return True
    if age is None and load_live().get('status')=='updating':
        mark_interrupted('이전 갱신이 도중에 종료되었습니다(서버 종료 등). 다음 갱신에서 다시 시도합니다.');return True
    return False
MIN_GAP_HOURS=5   # 6시간마다 도는 자동 갱신이 겹쳐 중복 실행되지 않도록 하는 최소 간격
def _recent(ts,hours=None):
    try:
        last=datetime.datetime.strptime(str(ts)[:19],'%Y-%m-%dT%H:%M:%S').replace(tzinfo=SEOUL)
    except (ValueError,TypeError):
        return False
    return datetime.timedelta(0)<=now()-last<datetime.timedelta(hours=hours or MIN_GAP_HOURS)

def notify_now(current):
    """새 공고·일정·뉴스 카톡 알림 (갱신 직후, 또는 GitHub 에서 최신 데이터를 받은 직후)."""
    from news_engine import ARCHIVE as _ARC, load_json as _lj
    _news=(_lj(_ARC,[]) or [])+(_lj(Path(__file__).resolve().parent/'tech-news.json',[]) or [])
    from kakao_notify import notify_updates
    import user_store
    notify_updates(current.get('jobs',[]),current.get('careerWatch'),user=user_store.load() or None,news=_news)

def run_update(force=False):
    current=load_live()
    if not force and _recent(current.get('lastSuccess')):
        return {'status':'skipped','reason':'최근 %d시간 안에 성공한 갱신이 이미 있습니다.'%MIN_GAP_HOURS}
    try:
        fd=os.open(str(LOCK),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
    except FileExistsError:
        # 40분 넘은 잠금은 멈춘 것으로 보고 정리한 뒤 다시 시도
        try:
            if time.time()-LOCK.stat().st_mtime>STALE_LOCK_SEC:
                recover_stale()
                return run_update(force=True)
        except OSError:pass
        return {'status':'busy'}
    try:
        current['status']='updating';current['startedAt']=timestamp()
        save_live(current)
        companies=load_company_list()
        news,news_errors=collect_news(companies)
        tech_status=update_news(backfill_count=40)
        tech_errors=tech_status.get("errors",[])
        tech_news=[]
        jobs,job_errors=collect_work24(load_env())
        # Do not wipe existing successful data if RSS provider temporarily fails.
        if news:current['news']=news
        if tech_news:
            prior=current.get('techNews',[])
            seen=set();mixed=[]
            for article in sorted(tech_news+prior,key=lambda n:n.get('date',''),reverse=True):
                key=(article.get('title','').lower(),article.get('date',''))
                if key not in seen and article.get('url'):
                    mixed.append(article);seen.add(key)
            current['techNews']=mixed[:500]
        if jobs:
            # Append newly verified 2026 listings to this year's history.
            # Deduplicate by source URL; don't erase prior notices once closed.
            prior=[j for j in current.get('jobs',[]) if str(j.get('date',''))>='2026']
            merged={j['url']:j for j in prior+jobs if j.get('url')}
            current['jobs']=sorted(merged.values(),key=lambda j:str(j.get('date','')),reverse=True)[:3000]
        # 기업 공식 채용 사이트 전용 수집기 + 나머지 기업 채용페이지 변경 감지
        col_errors,col_ok=[],0
        try:
            from job_collectors import run_collectors
            col_errors,col_ok=run_collectors(current)
        except Exception as exc:
            col_errors=['채용 수집기 실행 실패 - '+type(exc).__name__]
        try:
            from career_watch import run_watch
            current['careerWatch']=run_watch(companies)
        except Exception as exc:
            current['careerWatch']={'error':type(exc).__name__}
        try:
            notify_now(current)
        except Exception as exc:
            col_errors.append('카카오 알림 실패 - '+type(exc).__name__)
        current['jobCount']=len(current.get('jobs',[]))
        current['status']='partial' if (news_errors or tech_errors or col_errors or (load_env() and job_errors)) else 'ok'
        if news or tech_status.get('freshResults') or tech_status.get('backfillResults') or jobs or col_ok:current['lastSuccess']=timestamp()
        current['lastAttempt']=timestamp()
        current['errors']=(news_errors+tech_errors+job_errors+col_errors)[:30]
        current['techArchiveCount']=tech_status.get('articles',0)
        current['backfillRemaining']=tech_status.get('backfillRemaining',0)
        current['analysisDone']=tech_status.get('ai',0)
        current['newsCount']=len(current.get('news',[]))
        current['jobCount']=len(current.get('jobs',[]))
        if not news and not tech_status.get('freshResults') and not tech_status.get('backfillResults') and not jobs and not col_ok:
            current['status']='error' if news_errors else 'empty'
            current['errors'].append('검색 결과 없음 또는 일시적 접속 실패; 기존 데이터는 유지됩니다.')
        save_live(current)
        return {'status':current['status'],'news':len(current.get('news',[])),'techArchive':tech_status.get('articles',0),'backfillRemaining':tech_status.get('backfillRemaining',0),'jobs':len(current.get('jobs',[])),'errors':current.get('errors',[])}
    except Exception as exc:
        current['status']='error';current['errors']=[str(exc)[:250]];current['lastAttempt']=timestamp()
        save_live(current)
        return {'status':'error','error':str(exc)}
    finally:
        LOCK.unlink(missing_ok=True)

if __name__=='__main__':
    print(json.dumps(run_update(force='--force' in sys.argv),ensure_ascii=False,indent=2))
