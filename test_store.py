import json, tempfile, datetime, threading, urllib.request, urllib.error
from pathlib import Path
import user_store as u
d = Path(tempfile.mkdtemp()); st = d/'u.json'; bk = d/'b'
t0 = datetime.date(2026, 11, 1)
assert u.save({'_ts': 100, 'apps': [1]}, st, bk, t0)[0] == 'ok'
assert u.load(st)['apps'] == [1] and not list(bk.glob('*')) if bk.exists() else True   # 첫 저장은 백업할 원본 없음
assert u.save({'_ts': 90, 'apps': [2]}, st, bk, t0)[0] == 'conflict' and u.load(st)['apps'] == [1]   # 오래된 데이터 거절
assert u.save({'_ts': 200, 'apps': [3]}, st, bk, t0)[0] == 'ok'
assert (bk/'user_data-20261101.json').exists() and json.loads((bk/'user_data-20261101.json').read_text())['apps'] == [1]
u.save({'_ts': 300, 'apps': [4]}, st, bk, t0); assert json.loads((bk/'user_data-20261101.json').read_text())['apps'] == [1]  # 같은 날 두 번째는 백업 유지
for i in range(40): u.save({'_ts': 1000+i}, st, bk, t0 + datetime.timedelta(days=i+1))
assert len(list(bk.glob('user_data-*.json'))) <= u.KEEP
assert u.save('x', st, bk)[0] == 'invalid' and u.save({'_ts': 5000, 'x': 'a'*2_100_000}, st, bk)[0] == 'invalid'
st.write_bytes(b'\xef\xbb\xbf{"_ts": 1}'); assert u.load(st) == {'_ts': 1}      # BOM 허용
st.write_text('깨진 파일'); assert u.load(st) == {}                              # 손상 파일은 빈 데이터로
# HTTP 라우트
import server
u.STORE = d/'http.json'; u.BACKUPS = d/'hb'
orig_save = u.save; u.save = lambda inc, store=u.STORE, backups=u.BACKUPS, today=None: orig_save(inc, store, backups, today)
orig_load = u.load; u.load = lambda store=u.STORE: orig_load(store)
srv = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler); port = srv.server_address[1]; server.PORT = port
threading.Thread(target=srv.serve_forever, daemon=True).start()
def call(method, body=None, origin=None, host=None):
    req = urllib.request.Request('http://127.0.0.1:%d/api/store' % port, data=None if body is None else json.dumps(body).encode(), method=method, headers={'Content-Type': 'application/json'})
    if origin: req.add_header('Origin', origin)
    if host: req.add_header('Host', host)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, (json.loads(e.read() or b'null') if e.headers.get('Content-Type', '').startswith('application/json') else None)
assert call('GET') == (200, {'data': {}})
assert call('POST', {'data': {'_ts': 10, 'apps': ['a']}})[0] == 200
assert call('GET')[1]['data']['apps'] == ['a']
c = call('POST', {'data': {'_ts': 5, 'apps': ['old']}}); assert c[0] == 409 and c[1]['data']['apps'] == ['a']
assert call('POST', {'data': {'_ts': 11}}, origin='http://evil.example')[0] == 403
assert call('GET', origin='http://evil.example')[0] == 403
assert call('POST', {'data': {'_ts': 11}}, host='evil.example')[0] == 403
assert call('POST', {'nodata': 1})[0] == 400
srv.shutdown(); print('TEST PASS store')

# --- 백업 목록/읽기 (v7.1)
import datetime as _dt, tempfile as _tf
_d = Path(_tf.mkdtemp()); _s = _d/'u.json'; _b = _d/'b'
u.save({'_ts': 1, 'apps': [{'id': 'a'}], 'cover': [], 'exp': []}, _s, _b, _dt.date(2026, 11, 1))
u.save({'_ts': 2, 'apps': [{'id': 'a'}, {'id': 'b'}]}, _s, _b, _dt.date(2026, 11, 2))
_l = u.list_backups(_b); assert [x['name'] for x in _l] == ['20261102'] and _l[0]['apps'] == 1, _l
assert u.read_backup('20261102', _b)['apps'] == [{'id': 'a'}]
assert u.read_backup('../../etc', _b) is None and u.read_backup('2026110', _b) is None and u.read_backup('20250101', _b) is None
print('TEST PASS backups')
