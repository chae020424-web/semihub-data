"""내 프로필(user_data.json) 기준 개인화 알림.
- match_job / match_news : 화면(me-ui.js)의 매칭 규칙과 같은 규칙의 파이썬 버전
- dday_alerts            : 지원 현황·전형 일정·대학원 마감 D-3 / D-1 알림 (중복 방지)
- news_digest            : 하루 한 번, 내 관심 뉴스 요약
"""
from __future__ import annotations
import datetime, json, re
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAX_TEXT = 200
ACTIVE = ('관심', '준비중', '지원예정', '')  # 마감 알림을 보낼 지원 상태


def _load(name):
    try:
        return json.loads((BASE / name).read_text(encoding='utf-8-sig'))
    except Exception:
        return {}


def norm(s):
    return re.sub(r'\s+', '', str(s if s is not None else '')).lower()


def make_profile(user, roles=None, companies=None):
    """user_data → 매칭용 프로필. roles/companies 는 테스트에서 주입 가능."""
    p = dict({'level': '신입', 'roles': [], 'companies': [], 'skills': '', 'keywords': ''}, **((user or {}).get('profile') or {}))
    roles = roles if roles is not None else _load('roles.json').get('roles', [])
    companies = companies if companies is not None else _load('companies.json').get('companies', [])
    mine = [r for r in roles if r.get('id') in p['roles']]
    terms = set()
    for r in mine:
        for t in str(r.get('tags') or '').split():
            if len(t) >= 2:
                terms.add(t.lower())
    for t in re.split(r'[,\s]+', str(p.get('keywords') or '')):
        if len(t) >= 2:
            terms.add(t.lower())
    return {'level': p['level'], 'terms': sorted(terms), 'cats': {r.get('category') for r in mine},
            'companies': [norm(c.get('name')) for c in companies if c.get('id') in p['companies']],
            'roleNames': [r.get('name') for r in mine], 'has': bool(p['roles'] or p['companies'] or str(p['keywords']).strip())}


def term_in(hay, t):
    t = t.lower()
    if re.fullmatch(r'[a-z0-9+.\-]+', t):
        return re.search(r'(^|[^a-z0-9])' + re.escape(t) + r'($|[^a-z0-9])', hay) is not None
    return re.sub(r'\s+', '', hay).find(re.sub(r'\s+', '', t)) >= 0


def match_job(j, p):
    lv = str(j.get('level') or '')
    if p['level'] == '신입' and '경력' in lv and '신입' not in lv:
        return False
    if p['level'] == '경력' and '신입' in lv and '경력' not in lv:
        return False
    if not p['has']:
        return True
    co = norm(j.get('company'))
    hay = ' '.join(str(j.get(k) or '') for k in ('title', 'category', 'company')).lower()
    if any(n and co and (n in co or co in n) for n in p['companies']):
        return True
    return any(term_in(hay, t) for t in p['terms'])


def match_news(n, p):
    if not p['has']:
        return 0
    score = 0
    co = norm(n.get('company')) + norm(n.get('source'))
    hay = ' '.join(str(n.get(k) or '') for k in ('title', 'summary', 'category')).lower()
    if any(x and x in co for x in p['companies']):
        score += 3
    if n.get('category') in p['cats']:
        score += 2
    if any(term_in(hay, t) for t in p['terms']):
        score += 1
    return score


def _date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def cert_expiry(c):
    d = _date(c.get('date'))
    try:
        y = float(c.get('valid'))
    except Exception:
        return None
    if not d or y <= 0:
        return None
    months = int(y) * 12 + round((y % 1) * 12)
    m = d.month - 1 + months
    yr, mo = d.year + m // 12, m % 12 + 1
    day = d.day
    while True:
        try:
            return datetime.date(yr, mo, day).isoformat()
        except ValueError:
            day -= 1


def dday_alerts(user, today, seen=()):
    """[(키, 한 줄 문구)]. D-3, D-1 에 한 번씩. 키로 중복 방지."""
    out = []
    seen = set(seen)

    def add(kind, ident, label, d, extra=''):
        dt = _date(d)
        if not dt:
            return
        left = (dt - today).days
        if left in (3, 1):
            key = '%s:%s:%s:%d' % (kind, ident, dt.isoformat(), left)
            if key not in seen:
                out.append((key, '· D-%d %s%s' % (left, label, extra)))

    user = user or {}
    for a in user.get('apps') or []:
        if a.get('status') in ACTIVE:
            add('app', a.get('id') or a.get('company'), '%s %s 마감' % (a.get('company', ''), (a.get('title') or '')[:16]), a.get('deadline'))
        for i, s in enumerate(a.get('stages') or []):
            if not s.get('result') or s.get('result') in ('대기', '예정', ''):
                add('stage', '%s#%d' % (a.get('id') or a.get('company'), i), '%s %s' % (a.get('company', ''), s.get('name', '전형')), s.get('date'))
    for g in user.get('grad') or []:
        add('grad', g.get('id') or g.get('school'), '%s %s 원서' % (g.get('school', ''), g.get('program', '')), g.get('deadline'))
        add('gradi', g.get('id') or g.get('school'), '%s 면접' % g.get('school', ''), g.get('interview'))
    for c in user.get('certs') or []:
        add('cert', c.get('id') or c.get('name'), '%s 유효기간 만료' % c.get('name', ''), cert_expiry(c))
    return out


def dday_message(items):
    if not items:
        return ''
    lines = ['[SEMI-HUB] 일정 알림']
    for _, t in items:
        if len('\n'.join(lines + [t])) > MAX_TEXT:
            lines.append('외 %d건 · 앱에서 확인' % (len(items) - (len(lines) - 1)))
            break
        lines.append(t)
    return '\n'.join(lines)


def news_digest(news, p, today, limit=3, days=3):
    """최근 days 일 이내 기사 중 내 관심 점수가 높은 순. 반환 (문구, 기사 id 목록)."""
    if not p['has']:
        return '', []
    scored = []
    for n in news or []:
        d = _date(n.get('date'))
        if d and 0 <= (today - d).days <= days:
            s = match_news(n, p)
            if s >= 2:
                scored.append((s, n.get('date') or '', n))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = [x[2] for x in scored[:limit]]
    if not top:
        return '', []
    lines = ['[SEMI-HUB] 내 관심 뉴스 %d건' % len(scored)]
    for n in top:
        line = '· ' + str(n.get('title') or '')[:42]
        if len('\n'.join(lines + [line])) > MAX_TEXT - 12:
            break
        lines.append(line)
    if len(scored) > len(lines) - 1:
        lines.append('앱에서 전체 보기')
    return '\n'.join(lines), [str(n.get('id') or n.get('url') or n.get('title')) for n in top]


def preview(user, news, jobs, today=None, roles=None, companies=None):
    """보낼 알림을 미리 보기 (상태를 바꾸지 않음)."""
    today = today or datetime.date.today()
    p = make_profile(user, roles, companies)
    parts = []
    mine = [j for j in jobs or [] if match_job(j, p)]
    if mine:
        parts.append('[내 관심 공고 %d건 / 전체 %d건]\n' % (len(mine), len(jobs)) + '\n'.join('· %s %s' % (j.get('company', ''), (j.get('title') or '')[:30]) for j in mine[:4]))
    dm = dday_message(dday_alerts(user, today))
    if dm:
        parts.append(dm)
    nm, _ = news_digest(news, p, today)
    if nm:
        parts.append(nm)
    return '\n\n'.join(parts)


def notify_personal(user, news, state, sender, today=None, roles=None, companies=None, jobs=None):
    """D-day 알림과 뉴스 요약을 보낸다. state(dict)에 중복 방지 기록을 갱신. 반환 (일정 수, 뉴스 수)."""
    today = today or datetime.date.today()
    p = make_profile(user, roles, companies)
    items = dday_alerts(user, today, state.get('dday', []))
    sent_d = 0
    if items:
        sender(dday_message(items), None)
        state['dday'] = sorted(set(state.get('dday', [])) | {k for k, _ in items})[-400:]
        sent_d = len(items)
    sent_n = 0
    if state.get('digestDate') != today.isoformat():
        msg, ids = news_digest(news, p, today)
        if msg:
            fresh = [i for i in ids if i not in state.get('digestIds', [])]
            if fresh:
                sender(msg, None)
                state['digestIds'] = (state.get('digestIds', []) + ids)[-200:]
                sent_n = len(ids)
        state['digestDate'] = today.isoformat()
    try:   # 선택 기능: AI 취업전략 요약(켠 사용자만). 실패해도 다른 알림에는 영향 없음
        import ai_digest
        ai_digest.run(user, news, jobs, state, sender, today)
    except Exception as e:
        print('[SEMI-HUB ai-digest] skipped:', type(e).__name__, str(e)[:120])
    return sent_d, sent_n
