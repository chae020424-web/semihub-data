"""전용 수집기가 없는 기업의 채용 페이지 '변경 감지'.

공고를 파싱하지는 않는다. 페이지의 텍스트 지문(해시)이 바뀌면 '채용 페이지가 업데이트됨'으로 표시한다.
- 숫자를 제거한 텍스트로 해시를 만들어 날짜·조회수 같은 잡음을 줄인다.
- 서버에서 HTML로 렌더링하지 않는(자바스크립트로 목록을 그리는) 페이지는 본문이 거의 비어 있어
  감지가 불가능하므로 'js_only'로 표시한다. 이 경우 자동 감지는 되지 않는다.
- 상태는 career_watch.json 에 저장되고, 요약은 live.json 의 careerWatch 항목으로 들어간다.
"""
from __future__ import annotations
import datetime, hashlib, json, re, time
from pathlib import Path

from job_collectors import http, SEOUL, PRECISE_COMPANY_IDS

BASE = Path(__file__).resolve().parent
STATE = BASE / 'career_watch.json'
MIN_TEXT = 400          # 이보다 짧은 본문이면 JS 렌더링 페이지로 본다
KEEP_DAYS = 14          # '변경됨' 표시를 유지하는 기간


def page_text(html):
    h = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', html)
    h = re.sub(r'(?s)<!--.*?-->', ' ', h)
    t = re.sub(r'<[^>]+>', ' ', h)
    t = re.sub(r'&[a-z#0-9]+;', ' ', t)
    t = re.sub(r'\d+', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def fingerprint(html):
    t = page_text(html)
    return hashlib.sha1(t[:200000].encode('utf-8')).hexdigest(), len(t)


def check_one(url, prev, fetch=http, now=None):
    now = now or datetime.datetime.now(SEOUL)
    ts = now.strftime('%Y-%m-%dT%H:%M:%S+09:00')
    rec = dict(prev or {})
    rec['url'] = url
    rec['checkedAt'] = ts
    try:
        html = fetch(url, timeout=15, retries=1)
    except Exception as exc:
        rec['status'] = 'error'
        rec['error'] = type(exc).__name__
        return rec
    digest, n = fingerprint(html)
    rec['error'] = ''
    rec['len'] = n
    if n < MIN_TEXT:
        rec['status'] = 'js_only'
        return rec
    if prev and prev.get('hash') and prev.get('status') in ('ok', 'changed') and prev['hash'] != digest:
        rec['status'] = 'changed'
        rec['changedAt'] = ts
    else:
        rec['status'] = 'ok' if not (prev and prev.get('status') == 'changed' and _recent(prev.get('changedAt'), now)) else 'changed'
        if rec['status'] == 'changed':
            rec['changedAt'] = prev.get('changedAt')
    rec['hash'] = digest
    return rec


def _recent(ts, now):
    try:
        d = datetime.datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=SEOUL)
        return (now - d).days < KEEP_DAYS
    except Exception:
        return False


def run_watch(companies, fetch=http, state_path=STATE, sleep=1.0):
    state = {}
    try:
        state = json.loads(Path(state_path).read_text(encoding='utf-8'))
    except Exception:
        pass
    now = datetime.datetime.now(SEOUL)
    summary = {'checkedAt': now.strftime('%Y-%m-%dT%H:%M:%S+09:00'), 'total': 0, 'ok': 0, 'jsOnly': 0,
               'error': 0, 'noUrl': 0, 'changed': []}
    for c in companies:
        cid = c.get('id')
        if cid in PRECISE_COMPANY_IDS:
            continue
        url = c.get('career')
        if not (isinstance(url, str) and url.startswith('https://')):
            summary['noUrl'] += 1
            continue
        summary['total'] += 1
        rec = check_one(url, state.get(cid), fetch=fetch, now=now)
        rec['name'] = c.get('name')
        state[cid] = rec
        if rec['status'] == 'changed':
            summary['changed'].append({'id': cid, 'name': c.get('name'), 'url': url, 'changedAt': rec.get('changedAt')})
        elif rec['status'] == 'js_only':
            summary['jsOnly'] += 1
        elif rec['status'] == 'error':
            summary['error'] += 1
        else:
            summary['ok'] += 1
        time.sleep(sleep)
    Path(state_path).write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8')
    return summary


if __name__ == '__main__':
    comps = json.loads((BASE / 'companies.json').read_text(encoding='utf-8'))['companies']
    s = run_watch(comps)
    print({k: v for k, v in s.items() if k != 'changed'}, '변경됨:', [c['name'] for c in s['changed']])
