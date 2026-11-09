"""카카오톡 '나에게 보내기' 알림.
설정: kakao_config.json 에 REST API 키를 넣고 `python kakao_notify.py auth` 로 한 번 로그인한다.
- 토큰은 kakao_token.json 에 저장되고 만료 전에 자동 갱신된다.
- 새 공고 / 채용 페이지 변경이 생기면 updater.py 가 notify_updates() 를 호출한다.
- 설정이 없으면 아무 것도 하지 않는다(수집은 정상 동작).
"""
from __future__ import annotations
import datetime, json, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / 'kakao_config.json'
TOKEN = BASE / 'kakao_token.json'
STATE = BASE / 'notify_state.json'
AUTH_URL = 'https://kauth.kakao.com/oauth/authorize'
TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
SEND_URL = 'https://kapi.kakao.com/v2/api/talk/memo/default/send'
APP_URL = 'http://127.0.0.1:8765/'
DEFAULT_REDIRECT = 'http://localhost:5000/callback'
MAX_TEXT = 200  # 카카오 text 템플릿 글자 수 제한


def _post(url, data, headers=None, timeout=15):
    body = urllib.parse.urlencode(data).encode()
    h = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise RuntimeError('HTTP %s %s' % (e.code, e.read().decode('utf-8', 'replace')[:200]))


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except Exception:
        return None


def load_config(path=CONFIG):
    c = _read(path)
    if not isinstance(c, dict) or not str(c.get('rest_api_key', '')).strip():
        return None
    return c


def configured(config_path=CONFIG, token_path=TOKEN):
    return bool(load_config(config_path)) and bool((_read(token_path) or {}).get('refresh_token'))


def _params(cfg, **kw):
    d = {'client_id': cfg['rest_api_key'].strip()}
    d.update(kw)
    if str(cfg.get('client_secret', '')).strip():
        d['client_secret'] = cfg['client_secret'].strip()
    return d


def _store(tok, r, now):
    tok = dict(tok or {})
    tok['access_token'] = r['access_token']
    tok['expires_at'] = now() + int(r.get('expires_in', 21600))
    if r.get('refresh_token'):
        tok['refresh_token'] = r['refresh_token']
    return tok


def auth_url(cfg):
    q = urllib.parse.urlencode({'client_id': cfg['rest_api_key'].strip(), 'redirect_uri': cfg.get('redirect_uri', DEFAULT_REDIRECT),
                                'response_type': 'code', 'scope': 'talk_message'})
    return AUTH_URL + '?' + q


def exchange_code(code, cfg, post=_post, token_path=TOKEN, now=time.time):
    r = post(TOKEN_URL, _params(cfg, grant_type='authorization_code', redirect_uri=cfg.get('redirect_uri', DEFAULT_REDIRECT), code=code))
    tok = _store({}, r, now)
    Path(token_path).write_text(json.dumps(tok, indent=1), encoding='utf-8')
    return tok


def access_token(cfg, post=_post, token_path=TOKEN, now=time.time):
    tok = _read(token_path)
    if not tok or not tok.get('refresh_token'):
        raise RuntimeError('카카오 로그인이 필요합니다 (setup_kakao_windows.bat)')
    if tok.get('access_token') and now() < tok.get('expires_at', 0) - 300:
        return tok['access_token']
    r = post(TOKEN_URL, _params(cfg, grant_type='refresh_token', refresh_token=tok['refresh_token']))
    tok = _store(tok, r, now)
    Path(token_path).write_text(json.dumps(tok, indent=1), encoding='utf-8')
    return tok['access_token']


def send(text, link=None, post=_post, config_path=CONFIG, token_path=TOKEN, now=time.time):
    cfg = load_config(config_path)
    if not cfg:
        raise RuntimeError('kakao_config.json 이 없거나 REST API 키가 비어 있습니다')
    at = access_token(cfg, post=post, token_path=token_path, now=now)
    url = link if isinstance(link, str) and link.startswith(('http://', 'https://')) else APP_URL
    tpl = {'object_type': 'text', 'text': text[:MAX_TEXT], 'link': {'web_url': url, 'mobile_web_url': url}, 'button_title': '열기'}
    r = post(SEND_URL, {'template_object': json.dumps(tpl, ensure_ascii=False)}, headers={'Authorization': 'Bearer ' + at})
    if r.get('result_code') not in (0, None):
        raise RuntimeError('전송 실패 result_code=%s' % r.get('result_code'))
    return True


# ---------- 업데이트 알림
def _jid(j):
    return str(j.get('id') or j.get('url') or '')


def build_message(new_jobs, changed):
    lines = []
    if new_jobs:
        lines.append('[SEMI-HUB] 새 공고 %d건' % len(new_jobs))
    if changed:
        lines.append('채용페이지 변경: ' + ', '.join(c.get('name') or '' for c in changed[:4]) + (' 외 %d곳' % (len(changed) - 4) if len(changed) > 4 else ''))
    if not new_jobs and not changed:
        return ''
    if not new_jobs:
        lines.insert(0, '[SEMI-HUB]')
    shown = 0
    for j in new_jobs:
        dl = j.get('deadline') or ('상시' if j.get('rolling') else '')
        line = '· %s %s%s' % (j.get('company', ''), (j.get('title') or '')[:24], (' ~' + dl[5:] if dl[:2] == '20' else (' ' + dl if dl else '')))
        if len('\n'.join(lines + [line])) > MAX_TEXT - 14:
            break
        lines.append(line); shown += 1
    if len(new_jobs) > shown:
        lines.append('외 %d건 · 앱에서 확인' % (len(new_jobs) - shown))
    return '\n'.join(lines)


def notify_updates(jobs, watch_summary, state_path=STATE, sender=None, config_path=CONFIG, token_path=TOKEN,
                   user=None, news=None, today=None, profile=None, require_filter=False):
    """새 공고·채용페이지 변경·내 일정(D-day)·관심 뉴스를 카톡으로 보낸다.
    user(프로필 등)가 있으면 새 공고를 내 관심 조건으로 거르고 일정/뉴스 알림도 보낸다.
    반환: (보낸 새 공고 수, 보낸 변경 수) 또는 None(미설정)."""
    import personal_notify as pn
    if sender is None:
        if not configured(config_path, token_path):
            return None
        sender = lambda t, l=None: send(t, l, config_path=config_path, token_path=token_path)
    st = _read(state_path)
    first = st is None
    st = st if isinstance(st, dict) else {}
    seen, seen_ch = set(st.get('seen', [])), set(st.get('seenChanges', []))
    ids = {_jid(j) for j in jobs if _jid(j)}
    new = [] if first else [j for j in jobs if _jid(j) and _jid(j) not in seen]
    if user is not None:
        prof = profile or pn.make_profile(user)
        if require_filter and not prof['has']:
            new = []   # 관심 직무·기업을 정하지 않은 사용자에게는 공고 알림을 보내지 않음
        elif prof['has'] or prof['level'] != '무관':
            new = [j for j in new if pn.match_job(j, prof)]
    new.sort(key=lambda j: (0 if j.get('collector') else 1, j.get('deadline') or '9999'))
    changed = [] if first else [c for c in (watch_summary or {}).get('changed', []) if '%s@%s' % (c.get('id'), c.get('changedAt')) not in seen_ch]
    msg = build_message(new, changed)
    if msg:
        link = new[0].get('url') if len(new) == 1 and not changed else None
        sender(msg, link)  # 실패하면 예외 → 상태를 저장하지 않아 다음 실행에서 다시 시도
    # 먼저 공고 상태를 저장 (뒤의 개인 알림이 실패해도 공고는 다시 보내지 않도록)
    st['seen'] = sorted(seen | ids)
    st['seenChanges'] = sorted(seen_ch | {'%s@%s' % (c.get('id'), c.get('changedAt')) for c in (watch_summary or {}).get('changed', [])})
    Path(state_path).write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    if user is not None and not first:
        try:
            pn.notify_personal(user, news, st, sender, today=today, jobs=jobs)
        finally:
            Path(state_path).write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    return len(new), len(changed)


# ---------- CLI
def diagnose_config(path=CONFIG):
    """kakao_config.json 이 왜 안 읽히는지 사람이 알 수 있게 설명한다."""
    p = Path(path)
    if not p.exists():
        return 'kakao_config.json 파일이 없습니다. setup_kakao_windows.bat 을 다시 실행하세요.'
    try:
        raw = p.read_bytes().decode('utf-8-sig')
    except UnicodeDecodeError:
        return '파일 인코딩 문제입니다. 메모장에서 다른 이름으로 저장 → 인코딩을 UTF-8로 선택해 저장하세요.'
    try:
        c = json.loads(raw)
    except json.JSONDecodeError as e:
        return ('kakao_config.json 형식이 틀렸습니다 (%d번째 줄 근처: %s).\n'
                '확인할 것: 줄 끝 쉼표(마지막 줄 제외), 따옴표는 반드시 " (스마트 따옴표 “ ” 금지), 중괄호 { } 짝.' % (e.lineno, e.msg))
    if not isinstance(c, dict):
        return 'kakao_config.json 은 { 로 시작하는 형식이어야 합니다.'
    key = str(c.get('rest_api_key', '')).strip()
    if not key or '여기에' in key:
        return 'rest_api_key 에 REST API 키를 붙여넣지 않았습니다.'
    return '알 수 없는 설정 문제입니다.'


def _cli():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'help'
    cfg = load_config()
    if cmd in ('auth', 'test') and not cfg:
        print(diagnose_config())
        return 1
    if cmd == 'auth':
        print('1) 아래 주소를 브라우저에서 열어 로그인·동의하세요.\n\n' + auth_url(cfg) + '\n')
        print('2) 이동된 주소(localhost:5000/callback?code=... 페이지는 열리지 않아도 됩니다) 전체를 복사해 아래에 붙여넣으세요.')
        s = input('주소 또는 code: ').strip()
        code = urllib.parse.parse_qs(urllib.parse.urlparse(s).query).get('code', [s])[0]
        exchange_code(code, cfg)
        send('[SEMI-HUB] 카카오톡 알림이 연결되었습니다.')
        print('연결 완료. 카톡 "나와의 채팅"을 확인하세요.')
        return 0
    if cmd == 'test':
        send('[SEMI-HUB] 테스트 알림입니다.')
        print('전송했습니다.')
        return 0
    print('사용법: python kakao_notify.py auth | test')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(_cli())
    except Exception as exc:
        print('오류:', exc)
        sys.exit(1)
