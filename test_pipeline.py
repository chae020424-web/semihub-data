"""오프라인 회귀 테스트: 네트워크 없이 RSS 파싱·중복 제거·재시도·연도 처리 확인. 실행: python test_pipeline.py"""
import sys, io, datetime, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import news_engine as n

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>SK hynix HBM4 mass production begins - Reuters</title><link>https://news.google.com/rss/articles/abc</link><pubDate>Fri, 30 Oct 2026 03:00:00 GMT</pubDate><description>HBM4 TSV</description><source url="https://reuters.com">Reuters</source></item>
<item><title>삼성전자 하이브리드 본딩 장비 도입</title><link>https://news.google.com/rss/articles/def</link><pubDate>Mon, 02 Nov 2026 01:00:00 GMT</pubDate><description>패키징</description></item>
<item><title>Unrelated cooking news</title><link>https://x.com/1</link><pubDate>Mon, 02 Nov 2026 01:00:00 GMT</pubDate><description>soup</description></item>
<item><title>HBM old news</title><link>https://x.com/2</link><pubDate>Wed, 01 Jan 2025 01:00:00 GMT</pubDate><description>HBM</description></item>
</channel></rss>""".encode("utf-8")

rows = n.parse_feed(RSS, query_name="t")
assert len(rows) == 2, rows                     # 무관 기사·2025년 기사 제외
assert rows[0]["category"] == "메모리·HBM" and rows[0]["source"] == "Reuters"
assert rows[1]["category"] == "첨단 패키징"
a, added = n.merge([], rows); b, added2 = n.merge(a, rows)
assert len(a) == 2 and len(added) == 2 and len(b) == 2 and not added2   # 중복 제거

calls = []
class R:
    def __enter__(s): return s
    def __exit__(s, *x): pass
    def read(s, k): return b"ok"
def fake(req, timeout=0):
    calls.append(1)
    if len(calls) < 3: raise urllib.error.HTTPError("u", 429, "x", {}, io.BytesIO())
    return R()
urllib.request.urlopen = fake; n.time.sleep = lambda x: None
assert n.fetch("https://x") == b"ok" and len(calls) == 3                # 429 재시도

assert len(n.monthly_tasks()) > 0
print("TEST PASS")
