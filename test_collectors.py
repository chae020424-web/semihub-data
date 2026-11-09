"""오프라인 테스트: 2026-11-02에 각 사이트에서 실제로 관찰한 응답 모양을 샘플로 파서를 검증한다.
실행: python test_collectors.py   (인터넷 불필요)"""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import job_collectors as jc
import career_watch as cw

# 1) SK careers (실제 응답 필드 그대로)
SK = json.dumps({"success": True, "totalCount": 3, "list": [
    {"jobNoticeNo": 6656, "noticeID": "R262204", "title": "용인 부속의원 전문의 채용", "jobRole": "안전보건/보건관리",
     "recruitType": "무관", "workingType": "계약", "workingArea": "경기/인천", "corpName": "SK하이닉스",
     "start": "2026년 10월 12일(월)", "end": "2026년 11월 05일(목)"},
    {"jobNoticeNo": 6730, "noticeID": "R262278", "title": "SK실트론 공정기술 사무직 엔지니어 대졸신입 수시 채용",
     "jobRole": "제조/공정기술", "recruitType": "신입", "workingType": "정규", "workingArea": "경상",
     "corpName": "SK실트론", "start": "2026년 10월 21일(수)", "end": "2026년 11월 08일(일)"},
    {"jobNoticeNo": 6802, "noticeID": "R262350", "title": "통계 업무 담당자", "jobRole": "사무", "recruitType": "신입",
     "workingType": "계약", "workingArea": "광주", "corpName": "SK텔레콤", "start": "2026년 10월 27일(화)",
     "end": "2026년 11월 02일(월)"}]}, ensure_ascii=False)
r = jc.parse_sk(SK)
assert [j['company'] for j in r] == ['SK하이닉스', 'SK실트론'], r          # 반도체 계열만
assert r[1]['level'] == '신입' and r[1]['deadline'] == '2026-11-08' and r[1]['applyStart'] == '2026-10-21'
assert r[1]['url'].endswith('/Recruit/Detail/R262278') and r[1]['deadline'] == '2026-11-08'

# 2) 삼성 (실제 HTML 조각 구조)
LI = '''<li><div><div><div class="btnWrap"><button type="button" class="btnShare" data-value="9,001"><i>공유</i></button></div>
<a href="/#none"  data-value="9,001"><p class="company">  삼성전자 DS부문</p>
<h3 class="title">메모리 설계 신입사원 채용 </h3><p class="info"><span>
 신입
</span><span class="period"> 2026.11.02 ~ 2026.11.13 </span></p></a></div>
<div class="flagWrap"><span class="flag blue">D- 11</span><span class="flag grey">회로설계</span><span class="flag grey">공정</span></div></div></li>
<li><div><div><a href="/#none" data-value="23,407"><p class="company">  삼성바이오에피스</p><h3 class="title">경력 채용</h3>
<p class="info"><span> 경력 </span><span class="period"> 2026.11.02 ~ 2026.11.13 </span></p></a></div></div></li>'''
HTML = '<input type="hidden" class="divCnt" data-value="2"  data-max="1">' + LI
items, maxp = jc.parse_samsung(HTML)
assert maxp == 1 and len(items) == 1, items                               # 반도체 외 계열사 제외
s = items[0]
assert s['url'] == 'https://www.samsungcareers.com/hr/?no=9001' and s['deadline'] == '2026-11-13'
assert s['level'] == '신입' and '회로설계' in s['category'], s
assert jc.parse_samsung('<input class="divCnt" data-value="0"  data-max="0">')[0] == []   # 공고 0건

# 3) SK하이닉스 인재허브: 공고 없음 / 공고 있음 / 구조 해석 실패
EMPTY = ('<main><div class="sub-common-layout" ><div class="sub-common-layout-group" data-type="11">'
         '<div class="empty-content">곧 공개될 새로운 공고를 기대해 주세요.</div></div></div></main>')
assert jc.parse_hynix_hub(EMPTY) == []
FILLED = ('<main><div class="sub-common-layout" ><div class="sub-common-layout-group" data-type="11">'
          '<a href="/hub/ko/apply/job/123">2026년 11월 메모리 설계 신입</a></div>'
          '<div class="sub-common-layout-group" data-type="12"><div class="empty-content">곧 공개될</div></div></div></main>')
f = jc.parse_hynix_hub(FILLED)
assert len(f) == 1 and f[0]['url'] == 'https://talent.skhynix.com/hub/ko/apply/job/123', f
BROKEN = '<main><div class="sub-common-layout" ><div class="sub-common-layout-group">내용 있음</div></div></main>'
try:
    jc.parse_hynix_hub(BROKEN); raise SystemExit('구조 변경을 감지하지 못함')
except ValueError:
    pass

# 4) DB하이텍
assert jc.parse_dbhitek('{"code":"0","total":"0","code0":0,"list":null}') == []
d = jc.parse_dbhitek(json.dumps({"total": "1", "list": [{"seq": "5", "title": "공정기술 신입", "edate": "2026-11-20"}]}))
assert d[0]['deadline'] == '2026-11-20' and d[0]['id'] == 'db-5'

# 5) Eightfold (Lam / AMAT) — 실제 필드: id, name, locations, postedTs
EF = json.dumps({"data": {"count": 2, "positions": [
    {"id": 1099556585667, "name": "[신입/경력] Metrology Defect Inspection Engineer", "locations": ["KR-Yongin-03 (3259)"],
     "postedTs": 1792458885},
    {"id": 5, "name": "Engineer", "locations": ["MY-Kulim-02"], "postedTs": 1793348792}]}})
e, got, total = jc.parse_eightfold(EF, 'careers.lamresearch.com', 'lam', '램리서치 코리아')
assert len(e) == 1 and e[0]['rolling'] and e[0]['level'] == '신입' and e[0]['postedDate'].startswith('2026-'), e
assert e[0]['url'] == 'https://careers.lamresearch.com/careers/job/1099556585667' and total == 2

# 6) Workday (KLA)
WD = json.dumps({"total": 3, "jobPostings": [
    {"title": "Software Application Engineer", "locationsText": "Ansan, Korea", "postedOn": "17일 전 공고",
     "externalPath": "/job/Ansan-Korea/Software-Application-Engineer_2642241"},
    {"title": "Division Regional Development Applications Engineer", "locationsText": "2개 근무지",
     "postedOn": "공고 후 30일 이상 경과", "externalPath": "/job/Hwaseong-si-Korea/Division_2639689-5"},
    {"title": "US role", "locationsText": "San Jose, CA", "postedOn": "오늘", "externalPath": "/job/x"}]})
w, got, total = jc.parse_workday(WD, 'kla.wd1.myworkdayjobs.com', 'Search', 'kla', 'KLA 코리아')
assert len(w) == 2 and w[0]['postedDate'] and w[1]['postedDate'] == '' and '원문 확인' in w[1]['note'], w
assert w[0]['url'].startswith('https://kla.wd1.myworkdayjobs.com/en-US/Search/job/')

# 7) 러너: 성공한 수집기만 교체, 실패 시 이전 공고 유지, firstSeen 보존
def ok_fn():
    return jc.parse_sk(SK)
def bad_fn():
    raise OSError('blocked')
cur = {'jobs': [{'id': 'old', 'collector': 'samsung', 'title': '이전 삼성 공고', 'date': '2026-10-01'},
                {'id': 'w24', 'title': '고용24 공고', 'date': '2026-10-02'}]}
errs, okc = jc.run_collectors(cur, [('skcareers', 'SK', ok_fn), ('samsung', '삼성', bad_fn)])
assert okc == 1 and len(errs) == 1
ids = [j['id'] for j in cur['jobs']]
assert 'old' in ids and 'w24' in ids and 'sk-R262204' in ids                 # 실패한 쪽 공고·타 출처 공고 유지
assert cur['collectors']['samsung']['status'] == 'error' and cur['collectors']['skcareers']['count'] == 2
first = next(j for j in cur['jobs'] if j['id'] == 'sk-R262278')['firstSeen']
jc.run_collectors(cur, [('skcareers', 'SK', ok_fn)])
assert next(j for j in cur['jobs'] if j['id'] == 'sk-R262278')['firstSeen'] == first
assert sum(1 for j in cur['jobs'] if j.get('collector') == 'skcareers') == 2     # 중복 누적 없음

# 8) 변경 감지
body = '<html><body>' + ('채용 공고 안내 ' * 80) + '<script>var a=1</script></body></html>'
changed = body.replace('안내', '업데이트')
js = '<html><body><div id="app"></div><script>x</script></body></html>'
tmp = Path(tempfile.mkdtemp()) / 'w.json'
comps = [{'id': 'a', 'name': 'A사', 'career': 'https://a.example/c'}, {'id': 'b', 'name': 'B사', 'career': 'https://b.example/c'},
         {'id': 'samsung', 'name': '삼성', 'career': 'https://x'}, {'id': 'c', 'name': 'C사'}]
pages = {'https://a.example/c': body, 'https://b.example/c': js}
fetch = lambda url, **k: pages[url]
s1 = cw.run_watch(comps, fetch=fetch, state_path=tmp, sleep=0)
assert (s1['total'], s1['ok'], s1['jsOnly'], s1['noUrl'], s1['changed']) == (2, 1, 1, 1, []), s1   # 정밀 수집 기업은 제외
pages['https://a.example/c'] = changed
s2 = cw.run_watch(comps, fetch=fetch, state_path=tmp, sleep=0)
assert [c['name'] for c in s2['changed']] == ['A사'], s2
s3 = cw.run_watch(comps, fetch=fetch, state_path=tmp, sleep=0)
assert [c['name'] for c in s3['changed']] == ['A사']                          # 변경 표시는 일정 기간 유지
def boom(url, **k): raise OSError('x')
s4 = cw.run_watch(comps, fetch=boom, state_path=tmp, sleep=0)
assert s4['error'] == 2, s4


# 9) ASML — 2026-11-02에 관찰한 실제 필드 구조
ASML_RAW = json.dumps({"total": 2, "items": [
    {"id": "J-00356475", "job_id": "J-00356475", "name": "CS DUV UIR PIMI coordinator", "job_country": "Korea, Republic of",
     "job_location": "Hwasung, Korea", "job_date_posted": "2026-11-02T00:00:00", "job_teams": ["Customer Support"],
     "job_experience_levels": ["4-9 years"], "job_type": "Fix",
     "url": "https://www.asml.com/en/careers/find-your-job/cs-duv-uir-pimi-coordinator-j00356"},
    {"id": "J-1", "job_id": "J-1", "name": "Graduate Engineer", "job_country": "Netherlands", "job_experience_levels": ["0-3 years"]},
    {"id": "J-2", "job_id": "J-2", "name": "Junior Process Engineer", "job_country": "Korea, Republic of",
     "job_location": "Pyeong-Taek, Korea", "job_date_posted": "2026-10-30T00:00:00", "job_experience_levels": ["0-3 years"],
     "url": "https://www.asml.com/en/careers/find-your-job/x"}]})
a = jc.parse_asml(ASML_RAW)
assert [x['id'] for x in a] == ['asml-J-00356475', 'asml-J-2'], a                       # 한국만
assert a[0]['postedDate'] == '2026-11-02' and a[0]['level'] == '경력' and a[0]['rolling'] and a[0]['category'] == 'Customer Support'
assert a[1]['level'] == '신입'

# 9-1) 폴백 순서: Playwright 미설치 → 일반 HTTP / 둘 다 실패 → 사유가 합쳐진 오류
def no_pw(): raise ImportError('playwright')
def plain_ok(): return ASML_RAW
assert len(jc.collect_asml(fetch_pw=no_pw, fetch_plain=plain_ok)) == 2
def pw_fail(): raise TimeoutError('slow')
assert len(jc.collect_asml(fetch_pw=pw_fail, fetch_plain=plain_ok)) == 2                # Playwright 실패해도 HTTP로 성공
def plain_bad(): raise OSError('403')
try:
    jc.collect_asml(fetch_pw=no_pw, fetch_plain=plain_bad); raise SystemExit('실패를 숨김')
except RuntimeError as e:
    assert 'Playwright 미설치' in str(e) and 'HTTP OSError' in str(e), e
assert len(jc.collect_asml(fetch_pw=lambda: ASML_RAW, fetch_plain=plain_bad)) == 2       # Playwright 성공 시 HTTP 불사용

# 9-2) 실제 Chromium(Playwright) 경로: 사이트 응답을 가짜로 대체하고 토큰·헤더·필터·페이지네이션을 검증
try:
    import playwright.sync_api  # noqa
    have_pw = True
except ImportError:
    have_pw = False
if have_pw:
    seen = {'token': 0, 'search': []}
    def mk(n, start):
        return [{"id": "J-%d" % (start + i), "job_id": "J-%d" % (start + i), "name": "Job %d" % (start + i),
                 "job_country": "Korea, Republic of", "job_location": "Hwasung, Korea",
                 "job_date_posted": "2026-11-01T00:00:00", "job_teams": ["CS"], "job_experience_levels": ["4-9 years"],
                 "url": "https://www.asml.com/j/%d" % (start + i)} for i in range(n)]
    def setup(page):
        def page_h(route):
            route.fulfill(status=200, content_type='text/html', body='<html><body>asml</body></html>')
        def token_h(route):
            req = route.request
            assert req.method == 'POST' and 'json' in req.headers.get('content-type', ''), req.headers
            seen['token'] += 1
            route.fulfill(status=200, content_type='application/json', body='{"accessToken":"TKN","accessTokenExpiry":1}')
        def search_h(route):
            req = route.request
            cors = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*'}
            if req.method == 'OPTIONS':
                route.fulfill(status=204, headers=cors); return
            assert req.headers.get('authorization') == 'Bearer TKN', req.headers
            body = json.loads(req.post_data)
            s = body['widget']['items'][0]['search']
            assert s['filter']['filters'][0] == {'name': 'job_country', 'values': ['Korea, Republic of'], 'type': 'anyOf'}
            seen['search'].append(s['offset'])
            items = mk(25, 0) if s['offset'] == 0 else mk(5, 25)
            route.fulfill(status=200, content_type='application/json', headers=cors,
                          body=json.dumps({"widgets": [{"total_item": 30, "content": items}]}))
        page.route('https://www.asml.com/en/careers/find-your-job', page_h)
        page.route('https://www.asml.com/api/search-token', token_h)
        page.route('https://discover-euc1.sitecorecloud.io/**', search_h)
    raw = jc._asml_playwright(setup=setup, timeout_ms=20000)
    got = jc.parse_asml(raw)
    assert len(got) == 30 and seen['search'] == [0, 25] and seen['token'] == 1, (len(got), seen)
    print('Playwright 경로 검증 OK (30건, 2페이지, 토큰 1회)')
else:
    print('Playwright 미설치 — 브라우저 경로 테스트 생략')


# 10) TEL(recruiter.co.kr) — 2026-11-02에 관찰한 실제 항목 텍스트
TEL_ITEMS = [
    {"href": "/career/jobs/130249", "text": "접수마감\n도쿄일렉트론코리아 2026 하반기 경력사원 채용\n공채 경력\n일반채용\n경력\n2026.10.05 ~ \n2026.10.18 23:59"},
    {"href": "/career/jobs/130160", "text": "접수마감\n도쿄일렉트론코리아 2026 하반기 채용연계형 인턴사원 채용\n공채 신입\n일반채용\n신입\n2026.10.05 ~ \n2026.10.18 23:59"},
    {"href": "/career/jobs/777", "text": "접수중\n상시 채용 필드엔지니어\n경력\n2026.11.01 ~"},
    {"href": "/career/faq", "text": "무관한 링크"}]
tel = jc.parse_recruiter(TEL_ITEMS, 'tel.recruiter.co.kr', 'tel', '도쿄일렉트론코리아')
assert [x['id'] for x in tel] == ['tel-130249', 'tel-130160', 'tel-777'], tel
assert tel[0]['deadline'] == '2026-10-18' and tel[0]['applyStart'] == '2026-10-05' and tel[0]['level'] == '경력' and not tel[0]['rolling']
assert tel[1]['level'] == '신입' and tel[1]['url'] == 'https://tel.recruiter.co.kr/career/jobs/130160'
assert tel[2]['rolling'] and tel[2]['deadline'] == ''                                      # 마감일 없는 접수중 공고는 상시 처리
# Playwright 미설치 시 명확한 오류
def no_pw2(): raise ImportError('x')
try:
    jc.collect_recruiter('tel.recruiter.co.kr', 'tel', '도쿄일렉트론코리아', fetch=no_pw2); raise SystemExit('숨김')
except RuntimeError as e:
    assert 'Playwright 필요' in str(e)

if have_pw:
    LIST_HTML = """<html><body><div>접수상태 필터</div><div id="root"></div><script>
      setTimeout(()=>{document.getElementById('root').innerHTML=
        '<a href="/career/jobs/55" class="RecruitList_list-item__x"><div><span>접수중</span></div><p>2026 하반기 PE 신입 채용</p><div><p>신입</p></div><div>2026.11.03 ~ <div>2026.11.20 23:59</div></div></a>'},800)
    </script></body></html>"""
    def tel_setup(page):
        page.route('https://tel.recruiter.co.kr/career/home',
                   lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=LIST_HTML))
    items = jc._recruiter_playwright('tel.recruiter.co.kr', setup=tel_setup, timeout_ms=20000)
    got = jc.parse_recruiter(items, 'tel.recruiter.co.kr', 'tel', '도쿄일렉트론코리아')
    assert len(got) == 1 and got[0]['deadline'] == '2026-11-20' and got[0]['level'] == '신입', got   # 늦게 렌더링돼도 읽음
    EMPTY_HTML = '<html><body><div>접수상태 필터</div></body></html>'
    def empty_setup(page):
        page.route('https://tel.recruiter.co.kr/career/home', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=EMPTY_HTML))
    assert jc._recruiter_playwright('tel.recruiter.co.kr', setup=empty_setup, timeout_ms=20000) == []   # 공고 0건 = 정상
    BROKEN_HTML = '<html><body>error</body></html>'
    def broken_setup(page):
        page.route('https://tel.recruiter.co.kr/career/home', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=BROKEN_HTML))
    try:
        jc._recruiter_playwright('tel.recruiter.co.kr', setup=broken_setup, timeout_ms=20000); raise SystemExit('로드 실패를 0건으로 오인')
    except RuntimeError:
        pass
    print('TEL Playwright 경로 검증 OK (지연 렌더링·0건·로드 실패 구분)')

print('TEST PASS (collectors + watch + asml + tel)')
