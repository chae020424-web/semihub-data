"""기업 공식 채용 사이트 전용 수집기 (표준 라이브러리만 사용).

- 파서(parse_*)와 통신(fetch)을 분리해 오프라인 테스트가 가능하다.
- 하루 1회, 개인 학습용 저빈도 호출만 한다. 사이트가 막으면 해당 수집기만 '오류'로 표시하고
  이전에 수집한 공고는 지우지 않는다.
- 직접 실행: python job_collectors.py  → 수집기별 결과를 화면에 출력(live.json은 건드리지 않음)
"""
from __future__ import annotations
import datetime, html as htmlmod, json, re, time, urllib.error, urllib.parse, urllib.request

SEOUL = datetime.timezone(datetime.timedelta(hours=9))
UA = 'Mozilla/5.0 (compatible; SEMI-HUB/6.0 personal job-board reader; once a day)'
OFFICIAL = '기업 공식 채용 공고'
SK_SEMI = re.compile(r'하이닉스|실트론|키파운드리|플라즈마|트리켐|엔펄스|머티리얼즈|hynix', re.I)
SAMSUNG_SEMI = re.compile(r'삼성전자|삼성전기')


def today():
    return datetime.datetime.now(SEOUL).date()


def clean(s):
    s = htmlmod.unescape(re.sub(r'<[^>]+>', ' ', str(s or '')))
    return re.sub(r'\s+', ' ', s).strip()


def http(url, data=None, headers=None, timeout=20, retries=2):
    body = None
    if data is not None:
        if isinstance(data, bytes):
            body = data
        elif isinstance(data, (dict, list)):
            body = urllib.parse.urlencode(data, doseq=True).encode('utf-8')
        else:
            body = str(data).encode('utf-8')
    h = {'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'ko,en;q=0.8'}
    h.update(headers or {})
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=h, method='POST' if body is not None else 'GET')
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(3_000_000).decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
        time.sleep(2 * (attempt + 1))
    raise last


def kdate(s):
    """'2026년 11월 02일(월)' / '2026.11.02' / '2026-11-02' → '2026-11-02'"""
    s = str(s or '')
    m = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', s) or re.search(r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', s)
    return '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3))) if m else ''


def guess_level(title):
    t = title.lower()
    if '신입' in t or 'new grad' in t or 'entry' in t:
        return '신입'
    if '인턴' in t or 'intern' in t:
        return '인턴'
    if '경력' in t or 'senior' in t or 'experienced' in t:
        return '경력'
    return '미분류'


def job(collector, company, title, url, *, jid, deadline='', posted='', start='', level='미분류',
        category='', location='', rolling=False, note=''):
    return {'id': jid, 'collector': collector, 'company': company, 'title': clean(title)[:250], 'url': url,
            'deadline': deadline, 'postedDate': posted, 'applyStart': start, 'level': level,
            'category': category, 'location': location, 'rolling': rolling, 'note': note,
            'source': OFFICIAL, 'dateBasis': '공고 등록일' if posted else ('접수 시작일' if start else '수집 확인일')}


# ── SK그룹 (skcareers.com) : 하이닉스·실트론·키파운드리 등 반도체 계열만 ──────────────
def parse_sk(raw):
    d = json.loads(raw)
    if not d.get('success'):
        raise ValueError('SK careers 응답 success=false')
    out = []
    for x in d.get('list', []):
        corp = x.get('corpName', '')
        if not SK_SEMI.search(corp):
            continue
        nid = x.get('noticeID')
        out.append(job('skcareers', corp, x.get('title', ''), 'https://www.skcareers.com/Recruit/Detail/%s' % nid,
                       jid='sk-%s' % nid, deadline=kdate(x.get('end')), start=kdate(x.get('start')),
                       level=x.get('recruitType') or '미분류', category=x.get('jobRole', ''),
                       location=x.get('workingArea', ''), note=x.get('workingType', '')))
    return out


def collect_skcareers(fetch=http):
    raw = fetch('https://www.skcareers.com/Recruit/GetRecruitList',
                data={'sort': '2', 'searchText': '', 'corpCode': '', 'jobRole': '', 'recruitType': '',
                      'workingType': '', 'workingRegion': ''},
                headers={'Referer': 'https://www.skcareers.com/Recruit', 'Origin': 'https://www.skcareers.com',
                         'X-Requested-With': 'XMLHttpRequest',
                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
    return parse_sk(raw)


# ── 삼성 (samsungcareers.com) : 삼성전자·삼성전기만 ──────────────────────────────
def parse_samsung(h):
    m = re.search(r'class="divCnt"[^>]*data-max="(\d+)"', h)
    maxp = int(m.group(1)) if m else 0
    out = []
    for li in re.findall(r'<li>(.*?)</li>', h, re.S):
        comp = re.search(r'<p class="company">(.*?)</p>', li, re.S)
        title = re.search(r'<h3 class="title">(.*?)</h3>', li, re.S)
        seq = re.search(r'<a [^>]*data-value="([\d,]+)"', li)
        if not (comp and title and seq):
            continue
        company = clean(comp.group(1))
        if not SAMSUNG_SEMI.search(company):
            continue
        per = re.search(r'(\d{4}\.\d\d\.\d\d)\s*~\s*(\d{4}\.\d\d\.\d\d)', li)
        typ = re.search(r'<p class="info">\s*<span>(.*?)</span>', li, re.S)
        flags = [clean(f) for f in re.findall(r'<span class="flag grey">(.*?)</span>', li, re.S)]
        no = seq.group(1).replace(',', '')
        out.append(job('samsung', company, title.group(1), 'https://www.samsungcareers.com/hr/?no=%s' % no,
                       jid='sam-%s' % no, deadline=kdate(per.group(2)) if per else '',
                       start=kdate(per.group(1)) if per else '', level=clean(typ.group(1)) if typ else '미분류',
                       category=', '.join(flags[:4]), note='삼성 채용 사이트 공고'))
    return out, maxp


def collect_samsung(fetch=http):
    out, page = [], 1
    while page <= 30:
        h = fetch('https://www.samsungcareers.com/hr/list.data',
                  data={'currentPageNo': page, 'intNo': 0, 'strVal': '', 'strTxt': '', 'strKey': '',
                        'strOrderBy': '', 'strEntity': ''},
                  headers={'Referer': 'https://www.samsungcareers.com/hr/', 'X-Requested-With': 'XMLHttpRequest',
                           'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})
        items, maxp = parse_samsung(h)
        out += items
        if page >= maxp:
            break
        page += 1
    return out


# ── SK하이닉스 인재허브 (talent.skhynix.com) : 서버 렌더링 HTML ───────────────────
def parse_hynix_hub(h, base='https://talent.skhynix.com'):
    start = h.find('sub-common-layout"')
    end = h.find('</main>')
    seg = h[start:end] if start >= 0 else ''
    if not seg:
        raise ValueError('SK하이닉스 인재허브 페이지 구조를 찾지 못함')
    out = []
    for g in seg.split('sub-common-layout-group')[1:]:
        if 'empty-content' in g:
            continue
        found = 0
        for m in re.finditer(r'<a\s[^>]*href="([^"#][^"]*)"[^>]*>(.*?)</a>', g, re.S):
            title = clean(m.group(2))
            if not title:
                continue
            found += 1
            url = urllib.parse.urljoin(base, htmlmod.unescape(m.group(1)))
            out.append(job('hynix_hub', 'SK하이닉스', title, url, jid='hy-' + re.sub(r'\W+', '', url)[-40:],
                           note='SK hynix Talent Hub 모집 중 공고(마감일은 원문 확인)'))
        if not found:
            raise ValueError('SK하이닉스 인재허브: 공고가 있는데 목록 구조를 해석하지 못함 — 원문 확인 필요')
    return out


def collect_hynix_hub(fetch=http):
    return parse_hynix_hub(fetch('https://talent.skhynix.com/hub/ko/apply/job'))


# ── DB하이텍 (dbhitek-recruit.com) ────────────────────────────────────────────
def _first(r, *keys):
    for k in keys:
        if r.get(k):
            return str(r[k])
    return ''


def parse_dbhitek(raw):
    d = json.loads(raw)
    rows = d.get('list') or []
    if int(d.get('total') or 0) == 0 or not rows:
        return []
    out = []
    for r in rows:
        title = _first(r, 'title', 'subject', 'rc_title', 'recruit_title', 'name') if isinstance(r, dict) else ''
        if not title:
            raise ValueError('DB하이텍: 응답 필드를 해석하지 못함 — 원문 확인 필요')
        jid = _first(r, 'seq', 'idx', 'no', 'rc_seq', 'id') or re.sub(r'\W+', '', title)[:30]
        out.append(job('dbhitek', 'DB하이텍', title, 'https://dbhitek-recruit.com/#%s' % jid, jid='db-%s' % jid,
                       deadline=kdate(_first(r, 'edate', 'end_date', 'e_date', 'rc_edate', 'close_date')),
                       start=kdate(_first(r, 'sdate', 'start_date', 's_date', 'rc_sdate', 'open_date')),
                       level=_first(r, 'type', 'rc_type', 'career') or '미분류', note='DB하이텍 채용 사이트'))
    return out


def collect_dbhitek(fetch=http):
    raw = fetch('https://dbhitek-recruit.com/_interface/recruit_list.php', data={'page': 1},
                headers={'Referer': 'https://dbhitek-recruit.com/', 'X-Requested-With': 'XMLHttpRequest'})
    return parse_dbhitek(raw)


# ── Eightfold 공개 검색 API (Lam Research, Applied Materials) ──────────────────
def parse_eightfold(raw, host, collector, company):
    d = json.loads(raw)
    data = d.get('data') or d
    out = []
    for p in data.get('positions', []):
        locs = p.get('locations') or []
        if locs and not any(re.search(r'KR|KOR|Korea|한국', str(l)) for l in locs):
            continue
        ts = p.get('postedTs')
        posted = datetime.datetime.fromtimestamp(ts, SEOUL).strftime('%Y-%m-%d') if ts else ''
        title = p.get('name', '')
        out.append(job(collector, company, title, 'https://%s/careers/job/%s' % (host, p.get('id')),
                       jid='%s-%s' % (collector, p.get('id')), posted=posted, level=guess_level(title),
                       category=p.get('department') or '', location=', '.join(map(str, locs)), rolling=True,
                       note='마감일 미표시(상시 모집)'))
    return out, len(data.get('positions', [])), int(data.get('count') or 0)


def collect_eightfold(host, domain, collector, company, fetch=http, cap=300):
    out, start = [], 0
    while start < cap:
        q = urllib.parse.urlencode({'domain': domain, 'query': '', 'location': 'South Korea', 'start': start,
                                    'sort_by': 'timestamp'})
        raw = fetch('https://%s/api/pcsx/search?%s' % (host, q),
                    headers={'Accept': 'application/json', 'Referer': 'https://%s/careers' % host})
        items, got, total = parse_eightfold(raw, host, collector, company)
        out += items
        start += got
        if not got or start >= total:
            break
    return out


# ── Workday (KLA) ──────────────────────────────────────────────────────────
def rel_date(s):
    s = str(s or '')
    if re.search(r'오늘|today', s, re.I):
        return today().isoformat()
    if re.search(r'어제|yesterday', s, re.I):
        return (today() - datetime.timedelta(days=1)).isoformat()
    m = re.search(r'(\d+)\s*(?:일|days?)\s*(?:전|ago)', s, re.I)
    if m and not re.search(r'이상|\+', s):
        return (today() - datetime.timedelta(days=int(m.group(1)))).isoformat()
    return ''


def parse_workday(raw, host, site, collector, company):
    d = json.loads(raw)
    out = []
    for p in d.get('jobPostings', []):
        loc = p.get('locationsText', '')
        if not re.search(r'Korea|한국|근무지|locations', loc, re.I):
            continue
        multi = bool(re.search(r'근무지|locations', loc, re.I))
        title = p.get('title', '')
        path = p.get('externalPath', '')
        out.append(job(collector, company, title, 'https://%s/en-US/%s%s' % (host, site, path),
                       jid='%s-%s' % (collector, re.sub(r'\W+', '', path)[-40:]), posted=rel_date(p.get('postedOn')),
                       level=guess_level(title), location=loc, rolling=True,
                       note='근무지 여러 곳 — 한국 포함 여부는 원문 확인' if multi else '마감일 미표시(상시 모집)'))
    return out, len(d.get('jobPostings', [])), int(d.get('total') or 0)


def collect_workday(host, tenant, site, collector, company, fetch=http, cap=200):
    out, offset = [], 0
    while offset < cap:
        body = json.dumps({'appliedFacets': {}, 'limit': 20, 'offset': offset, 'searchText': 'Korea'})
        raw = fetch('https://%s/wday/cxs/%s/%s/jobs' % (host, tenant, site), data=body,
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        items, got, total = parse_workday(raw, host, site, collector, company)
        out += items
        offset += got
        if not got or offset >= total:
            break
    return out


# ── ASML 코리아 (Playwright 우선, 없으면 일반 HTTP) ─────────────────────────────
# 사이트 구조(2026-11-02 확인): /api/search-token 에서 토큰 발급 → Sitecore Search(discover)에 POST 조회.
ASML_PAGE = 'https://www.asml.com/en/careers/find-your-job'
ASML_TOKEN_URL = 'https://www.asml.com/api/search-token'
ASML_SEARCH_URL = 'https://discover-euc1.sitecorecloud.io/discover/v2/126200477'
ASML_COUNTRY = 'Korea, Republic of'
ASML_PAGE_SIZE = 25

_ASML_JS = """
async ({tokenUrl, searchUrl, template, size, cap}) => {
  const tr = await fetch(tokenUrl, {method: 'POST', headers: {'content-type': 'application/json'}, body: '{}'});
  if (!tr.ok) throw new Error('token ' + tr.status);
  const tk = await tr.json();
  const items = []; let offset = 0, total = null;
  while (offset < cap) {
    template.widget.items[0].search.offset = offset;
    const r = await fetch(searchUrl, {method: 'POST', headers: {'accept': 'application/json',
      'content-type': 'application/json', 'authorization': 'Bearer ' + tk.accessToken}, body: JSON.stringify(template)});
    if (!r.ok) throw new Error('search ' + r.status);
    const w = ((await r.json()).widgets || [])[0] || {};
    const got = w.content || [];
    total = w.total_item;
    items.push(...got);
    offset += size;
    if (!got.length || offset >= (total || 0)) break;
  }
  return JSON.stringify({total, items});
}
"""


def _asml_template():
    return {'context': {'page': {'uri': ASML_PAGE}, 'locale': {'country': 'us', 'language': 'en'}},
            'widget': {'items': [{'entity': 'content', 'rfk_id': 'asml_job_search',
                                  'search': {'limit': ASML_PAGE_SIZE, 'offset': 0, 'content': {},
                                             'filter': {'type': 'and', 'filters': [
                                                 {'name': 'job_country', 'values': [ASML_COUNTRY], 'type': 'anyOf'}]}}}]}}


def _asml_playwright(setup=None, timeout_ms=45000):
    """실제 크롬(Playwright)으로 ASML 페이지를 연 뒤, 그 페이지 안에서 토큰 발급·검색을 수행한다."""
    from playwright.sync_api import sync_playwright   # 미설치면 ImportError
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale='en-US')
            if setup:
                setup(page)
            page.goto(ASML_PAGE, wait_until='domcontentloaded', timeout=timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass            # 광고·분석 스크립트 때문에 networkidle이 안 올 수 있음 — 검색에는 영향 없음
            return page.evaluate(_ASML_JS, {'tokenUrl': ASML_TOKEN_URL, 'searchUrl': ASML_SEARCH_URL,
                                            'template': _asml_template(), 'size': ASML_PAGE_SIZE, 'cap': 200})
        finally:
            browser.close()


def _asml_plain():
    """Playwright 없이 같은 흐름을 일반 HTTP로 수행(사이트가 스크립트 요청을 막으면 실패할 수 있음)."""
    hdr = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Referer': ASML_PAGE,
           'Origin': 'https://www.asml.com'}
    tk = json.loads(http(ASML_TOKEN_URL, data='{}', headers=hdr))['accessToken']
    items, offset, total, tpl = [], 0, None, _asml_template()
    while offset < 200:
        tpl['widget']['items'][0]['search']['offset'] = offset
        h2 = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + tk,
              'Origin': 'https://www.asml.com', 'Referer': ASML_PAGE}
        w = (json.loads(http(ASML_SEARCH_URL, data=json.dumps(tpl), headers=h2)).get('widgets') or [{}])[0]
        got = w.get('content') or []
        total = w.get('total_item')
        items += got
        offset += ASML_PAGE_SIZE
        if not got or offset >= (total or 0):
            break
    return json.dumps({'total': total, 'items': items})


def parse_asml(raw):
    d = json.loads(raw)
    out = []
    for it in d.get('items', []):
        if ASML_COUNTRY not in str(it.get('job_country', '')):
            continue
        jid = it.get('job_id') or it.get('id')
        lv = ', '.join(it.get('job_experience_levels') or [])
        level = '신입' if re.search(r'(^|[^\d])0\s*-|graduate|entry', lv, re.I) else ('경력' if lv else guess_level(it.get('name', '')))
        out.append(job('asml', 'ASML 코리아', it.get('name', ''), it.get('url') or ASML_PAGE, jid='asml-%s' % jid,
                       posted=kdate(it.get('job_date_posted')), level=level,
                       category=', '.join(it.get('job_teams') or []), location=it.get('job_location', ''),
                       rolling=True, note='경력 요건 %s · 마감일 미표시' % (lv or '미표시')))
    return out


def collect_asml(fetch_pw=_asml_playwright, fetch_plain=_asml_plain):
    """Playwright가 있으면 그것으로, 없거나 실패하면 일반 HTTP로 시도. 둘 다 실패하면 오류(이전 결과는 유지됨)."""
    notes = []
    if fetch_pw is not None:
        try:
            return parse_asml(fetch_pw())
        except ImportError:
            notes.append('Playwright 미설치(install_playwright_windows.bat 실행 시 더 안정적)')
        except Exception as exc:
            notes.append('Playwright %s: %s' % (type(exc).__name__, str(exc)[:80]))
    try:
        return parse_asml(fetch_plain())
    except Exception as exc:
        notes.append('HTTP %s: %s' % (type(exc).__name__, str(exc)[:80]))
        raise RuntimeError(' / '.join(notes))


# ── recruiter.co.kr 계열 채용 사이트 (도쿄일렉트론코리아 등) : 화면 렌더링 → Playwright 필수 ───
# 공고 API가 사이트 인증을 요구하므로, 실제 브라우저로 목록 화면을 열어 DOM에서 읽는다.
_RECRUITER_JS = """() => [...document.querySelectorAll('a[href*="/career/jobs/"]')]
    .map(a => ({href: a.getAttribute('href'), text: a.innerText}))"""


def _recruiter_playwright(host, setup=None, timeout_ms=45000):
    from playwright.sync_api import sync_playwright   # 미설치면 ImportError
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale='ko-KR')
            if setup:
                setup(page)
            page.goto('https://%s/career/home' % host, wait_until='domcontentloaded', timeout=timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass
            try:
                page.wait_for_selector('a[href*="/career/jobs/"]', timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(1000)
            items = page.evaluate(_RECRUITER_JS)
            if not items and not page.get_by_text('접수상태').count():
                raise RuntimeError('채용 목록 화면이 로드되지 않음(공고 0건인지 구분 불가)')
            return items
        finally:
            browser.close()


def parse_recruiter(items, host, collector, company):
    out = []
    for it in items:
        m = re.search(r'/career/jobs/(\d+)', it.get('href', ''))
        if not m:
            continue
        text = it.get('text', '')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        status = lines[0] if lines and re.fullmatch(r'(접수|상시|마감|채용|모집)\S*', lines[0]) else ''
        rest = lines[1:] if status else lines
        title = rest[0] if rest else ''
        if not title:
            continue
        dates = re.findall(r'\d{4}\.\d{2}\.\d{2}', text)
        tags = ' '.join(l for l in rest[1:] if not re.search(r'\d{4}\.\d{2}\.\d{2}', l))
        level = '신입' if re.search('신입|인턴', title + ' ' + tags) else ('경력' if '경력' in title + ' ' + tags else '미분류')
        closed = status.startswith('접수마감') or status.startswith('마감')
        out.append(job(collector, company, title, 'https://%s/career/jobs/%s' % (host, m.group(1)),
                       jid='%s-%s' % (collector, m.group(1)), deadline=kdate(dates[1]) if len(dates) > 1 else '',
                       start=kdate(dates[0]) if dates else '', level=level, category=tags[:60],
                       rolling=(len(dates) < 2 and not closed),
                       note=('%s · ' % status if status else '') + '%s 채용 사이트' % company))
    return out


def collect_recruiter(host, collector, company, fetch=None):
    fetch = fetch or (lambda: _recruiter_playwright(host))
    try:
        items = fetch()
    except ImportError:
        raise RuntimeError('%s: Playwright 필요 (install_playwright_windows.bat 실행)' % company)
    return parse_recruiter(items, host, collector, company)


COLLECTORS = [
    ('tel', '도쿄일렉트론코리아', lambda: collect_recruiter('tel.recruiter.co.kr', 'tel', '도쿄일렉트론코리아')),
    ('asml', 'ASML 코리아', collect_asml),
    ('samsung', '삼성전자 DS·삼성전기', collect_samsung),
    ('skcareers', 'SK하이닉스·실트론·키파운드리 등 (SK그룹 채용)', collect_skcareers),
    ('hynix_hub', 'SK하이닉스 인재허브', collect_hynix_hub),
    ('dbhitek', 'DB하이텍', collect_dbhitek),
    ('lam', '램리서치 코리아', lambda: collect_eightfold('careers.lamresearch.com', 'lamresearch.com', 'lam', '램리서치 코리아')),
    ('amat', '어플라이드머티어리얼즈 코리아',
     lambda: collect_eightfold('careers.appliedmaterials.com', 'appliedmaterials.com', 'amat', '어플라이드머티어리얼즈 코리아')),
    ('kla', 'KLA 코리아', lambda: collect_workday('kla.wd1.myworkdayjobs.com', 'kla', 'Search', 'kla', 'KLA 코리아')),
]
# 전용 수집기가 있는 기업 id(companies.json). 이 기업들은 변경 감지 대상에서 제외한다.
PRECISE_COMPANY_IDS = {'samsung', 'sk', 'extra1', 'extra33', 'extra45', 'extra86', 'extra87', 'extra88', 'extra89', 'extra90'}


def run_collectors(current, collectors=None):
    """live.json(current)의 jobs를 갱신한다. 성공한 수집기의 이전 결과만 교체하고, 실패하면 이전 결과를 유지한다.
    반환: (오류 문자열 리스트, 성공한 수집기 수)"""
    collectors = collectors or COLLECTORS
    ts = datetime.datetime.now(SEOUL).strftime('%Y-%m-%dT%H:%M:%S+09:00')
    jobs = list(current.get('jobs', []))
    first = {j.get('id'): j.get('firstSeen') for j in jobs if j.get('id') and j.get('firstSeen')}
    status = dict(current.get('collectors', {}))
    errors, ok = [], 0
    for key, label, fn in collectors:
        prev_count = sum(1 for j in jobs if j.get('collector') == key)
        try:
            items = fn()
        except Exception as exc:
            msg = '%s: %s' % (type(exc).__name__, str(exc)[:140])
            status[key] = {'label': label, 'status': 'error', 'error': msg, 'checkedAt': ts, 'count': prev_count,
                           'lastOk': status.get(key, {}).get('lastOk')}
            errors.append('%s 수집 실패 — %s' % (label, msg))
            continue
        jobs = [j for j in jobs if j.get('collector') != key]
        for j in items:
            j['firstSeen'] = first.get(j['id']) or today().isoformat()
            j['date'] = j.get('postedDate') or j.get('applyStart') or j['firstSeen']
        jobs += items
        status[key] = {'label': label, 'status': 'ok', 'error': '', 'checkedAt': ts, 'count': len(items), 'lastOk': ts}
        ok += 1
        time.sleep(1)
    current['jobs'] = jobs
    current['collectors'] = status
    return errors, ok


if __name__ == '__main__':
    for key, label, fn in COLLECTORS:
        try:
            items = fn()
            print('[OK ] %-10s %-32s %3d건' % (key, label, len(items)))
            for j in items[:3]:
                print('      -', j['company'], '|', j['title'][:50], '|', j['deadline'] or ('상시' if j['rolling'] else '-'))
        except Exception as exc:
            print('[ERR] %-10s %-32s %s: %s' % (key, label, type(exc).__name__, str(exc)[:160]))
