"""고용24 API 키가 어떤 호출을 허용하는지 확인한다. 키는 환경변수 WORK24_API_KEY 에서만 읽고 출력하지 않는다."""
import os, sys, urllib.parse, urllib.request, urllib.error

KEY = os.environ.get('WORK24_API_KEY', '').strip()
if not KEY:
    print('WORK24_API_KEY 환경변수가 없습니다. 환경변수를 등록하고 터미널을 새로 연 뒤 다시 실행하세요.')
    sys.exit(1)

URL = 'https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do'
qs = {'authKey': KEY, 'callTp': 'L', 'returnType': 'XML', 'startPage': 1, 'display': 3, 'regDate': 'M-1', 'keyword': '반도체'}
req = urllib.request.Request(URL + '?' + urllib.parse.urlencode(qs), headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        status, body = r.status, r.read().decode('utf-8', 'replace')
except urllib.error.HTTPError as e:
    status, body = e.code, e.read().decode('utf-8', 'replace')
except Exception as e:
    print('접속 실패:', type(e).__name__, str(e).replace(KEY, '***')[:200]); sys.exit(1)
print('HTTP', status)
print(body.replace(KEY, '***')[:1200])
