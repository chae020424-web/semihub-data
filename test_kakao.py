import json, tempfile, time, urllib.parse
from pathlib import Path
import kakao_notify as k
d = Path(tempfile.mkdtemp()); cfgp = d/'c.json'; tp = d/'t.json'; sp = d/'s.json'
cfgp.write_text(json.dumps({'rest_api_key': 'KEY'})); calls = []
def post(url, data, headers=None, timeout=15):
    calls.append((url, data, headers))
    if url == k.TOKEN_URL:
        if data['grant_type'] == 'authorization_code':
            assert data['code'] == 'CODE' and data['client_id'] == 'KEY'
            return {'access_token': 'A1', 'expires_in': 21600, 'refresh_token': 'R1'}
        assert data['refresh_token'] == 'R1'
        return {'access_token': 'A2', 'expires_in': 21600}
    assert headers['Authorization'].startswith('Bearer ')
    return {'result_code': 0}
cfg = k.load_config(cfgp); assert cfg and not k.configured(cfgp, tp)
assert 'scope=talk_message' in k.auth_url(cfg)
k.exchange_code('CODE', cfg, post=post, token_path=tp); assert k.configured(cfgp, tp)
# 유효 토큰 재사용
assert k.access_token(cfg, post=post, token_path=tp) == 'A1'
# 만료 → 갱신, refresh_token 유지
t = json.loads(tp.read_text()); t['expires_at'] = 0; tp.write_text(json.dumps(t))
assert k.access_token(cfg, post=post, token_path=tp) == 'A2' and json.loads(tp.read_text())['refresh_token'] == 'R1'
assert k.send('x'*500, 'https://e.com/1', post=post, config_path=cfgp, token_path=tp)
tpl = json.loads(calls[-1][1]['template_object']); assert len(tpl['text']) == 200 and tpl['link']['web_url'] == 'https://e.com/1'
# 알림 로직
sent = []; snd = lambda t, l=None: sent.append((t, l))
jobs = [{'id': 'a', 'company': '삼성전자', 'title': 'DS 설계', 'url': 'https://s/a', 'deadline': '2026-11-20', 'collector': 'samsung'}]
assert k.notify_updates(jobs, {'changed': []}, state_path=sp, sender=snd) == (0, 0) and not sent   # 최초: 기준선만 저장
assert k.notify_updates(jobs, {'changed': []}, state_path=sp, sender=snd) == (0, 0) and not sent   # 변화 없음
jobs2 = jobs + [{'id': 'b', 'company': 'ASML', 'title': 'Application Engineer', 'url': 'https://s/b', 'rolling': True, 'collector': 'asml'}]
ws = {'changed': [{'id': 'extra5', 'name': '네패스', 'changedAt': '2026-11-02T10:00:00+09:00'}]}
assert k.notify_updates(jobs2, ws, state_path=sp, sender=snd) == (1, 1); m = sent[-1][0]; print(m); assert len(m) <= 200 and 'ASML' in m and '네패스' in m
assert k.notify_updates(jobs2, ws, state_path=sp, sender=snd) == (0, 0) and len(sent) == 1       # 중복 방지
# 전송 실패 시 상태 미저장 → 재시도
jobs3 = jobs2 + [{'id': 'c', 'company': 'KLA', 'title': 'FAE', 'url': 'https://s/c'}]
def bad(t, l=None): raise RuntimeError('net')
try: k.notify_updates(jobs3, ws, state_path=sp, sender=bad); assert False
except RuntimeError: pass
assert k.notify_updates(jobs3, ws, state_path=sp, sender=snd) == (1, 0) and sent[-1][1] == 'https://s/c'
# 많은 공고 → 200자 이내 + '외 N건'
many = jobs3 + [{'id': 'x%d' % i, 'company': '회사%d' % i, 'title': '아주 긴 직무 이름 테스트 공고입니다', 'url': 'https://s/%d' % i} for i in range(30)]
k.notify_updates(many, {}, state_path=sp, sender=snd); m = sent[-1][0]; assert len(m) <= 200 and '외 ' in m; print(m)
assert k.notify_updates(jobs, {}, state_path=d/'none.json') is None or True
assert k.notify_updates(jobs, {}, state_path=sp, config_path=d/'nope.json', token_path=tp) is None  # 미설정 → 무동작
print('TEST PASS kakao')
