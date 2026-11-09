"""개인 데이터(지원 현황·자소서·노트·프로필 등)를 PC의 JSON 파일에 저장한다.
- 파일: user_data.json  (브라우저 저장소가 지워져도 남는다)
- 자동 백업: 하루 한 번 user_backups/ 에 복사본을 만들고 최근 30개만 보관
- 충돌 규칙: 클라이언트가 보낸 _ts(마지막 수정 시각, ms)가 서버 것보다 오래되면 거절(409)하고 서버 데이터를 돌려준다.
"""
from __future__ import annotations
import datetime, json, os, threading
from pathlib import Path

BASE = Path(__file__).resolve().parent
STORE = BASE / 'user_data.json'
BACKUPS = BASE / 'user_backups'
MAX_BYTES = 2_000_000
KEEP = 30
_lock = threading.Lock()


def _read(path):
    try:
        d = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def load(store=STORE):
    d = _read(store)
    return d if d is not None else {}


def _ts(d):
    try:
        return int(d.get('_ts', 0))
    except Exception:
        return 0


def _backup(store, backups, today):
    if not Path(store).exists():
        return
    Path(backups).mkdir(exist_ok=True)
    dst = Path(backups) / ('user_data-%s.json' % today.strftime('%Y%m%d'))
    if not dst.exists():
        dst.write_bytes(Path(store).read_bytes())
    old = sorted(Path(backups).glob('user_data-*.json'))
    for p in old[:-KEEP]:
        try:
            p.unlink()
        except Exception:
            pass


def save(incoming, store=STORE, backups=BACKUPS, today=None):
    """반환: (status, 서버에 있는 데이터). status: 'ok' | 'conflict' | 'invalid'"""
    if not isinstance(incoming, dict):
        return 'invalid', load(store)
    raw = json.dumps(incoming, ensure_ascii=False)
    if len(raw.encode('utf-8')) > MAX_BYTES:
        return 'invalid', load(store)
    with _lock:
        cur = load(store)
        if cur and _ts(incoming) < _ts(cur):
            return 'conflict', cur
        today = today or datetime.date.today()
        try:
            _backup(store, backups, today)  # 덮어쓰기 전의 파일을 그날의 백업으로 보관
        except Exception:
            pass
        tmp = Path(str(store) + '.tmp')
        tmp.write_text(raw, encoding='utf-8')
        os.replace(tmp, store)
        return 'ok', incoming


def list_backups(backups=BACKUPS):
    """최근 백업 목록 (최신순). 각 항목: 날짜(name), 크기, 지원/자소서/경험 개수."""
    out = []
    for p in sorted(Path(backups).glob('user_data-*.json'), reverse=True)[:KEEP]:
        d = _read(p) or {}
        n = p.stem.replace('user_data-', '')
        out.append({'name': n, 'size': p.stat().st_size, 'apps': len(d.get('apps') or []),
                    'cover': len(d.get('cover') or []), 'exp': len(d.get('exp') or [])})
    return out


def read_backup(name, backups=BACKUPS):
    """name 은 YYYYMMDD 8자리만 허용 (경로 조작 방지). 없으면 None."""
    if not (isinstance(name, str) and len(name) == 8 and name.isdigit()):
        return None
    return _read(Path(backups) / ('user_data-%s.json' % name))
