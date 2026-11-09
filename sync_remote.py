"""GitHub Actions 가 모아 둔 최신 데이터(live.json 등)를 노트북으로 받아 오는 모듈.
- 설정: remote_config.json {"repo": "계정/저장소", "branch": "main"} 또는 환경변수 SEMIHUB_REMOTE_REPO
- 공개 저장소는 인증 없이 받고, 비공개 저장소는 환경변수 SEMIHUB_GH_TOKEN(읽기 전용 토큰)을 사용
- 개인 데이터(user_data.json·카톡 토큰 등)는 내려받지도 올리지도 않는다."""
from __future__ import annotations
import datetime, json, os, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / 'remote_config.json'
FILES = ('live.json', 'news_archive.json', 'news_state.json', 'career_watch.json')


def settings():
    repo = os.environ.get('SEMIHUB_REMOTE_REPO', '').strip()
    branch = os.environ.get('SEMIHUB_REMOTE_BRANCH', '').strip()
    if not repo:
        try:
            c = json.loads(CONFIG.read_text(encoding='utf-8'))
            repo, branch = str(c.get('repo', '')).strip(), branch or str(c.get('branch', '')).strip()
        except (OSError, ValueError):
            pass
    repo = repo.strip('/ ')
    if repo.count('/') != 1 or any(ch in repo for ch in ' \\?#:') or repo.startswith(('.', '-')):
        return None
    return {'repo': repo, 'branch': branch or 'main'}


def configured():
    return settings() is not None


def _url(cfg, name):
    base = os.environ.get('SEMIHUB_REMOTE_BASE') or 'https://raw.githubusercontent.com/%s/%s/' % (cfg['repo'], cfg['branch'])
    return base.rstrip('/') + '/' + name


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'SEMI-HUB-sync', 'Cache-Control': 'no-cache'})
    tok = os.environ.get('SEMIHUB_GH_TOKEN', '').strip()
    if tok and url.startswith('https://raw.githubusercontent.com/'):
        req.add_header('Authorization', 'token ' + tok)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(30 * 1024 * 1024 + 1)
    if len(data) > 30 * 1024 * 1024:
        raise ValueError('too large')
    return data


def _ts(s):
    try:
        return datetime.datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _save(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.new')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def _key(a):
    return a.get('url') or (str(a.get('title', '')).lower(), a.get('date', ''))


def merge_archive(local, remote):
    """기사 보관함 합치기: 주소(없으면 제목+날짜) 기준으로 중복 제거, 같은 기사는 원격(AI 분석 포함 가능) 우선."""
    out = {}
    for a in (local or []) + (remote or []):
        if isinstance(a, dict) and _key(a):
            out[_key(a)] = a
    return sorted(out.values(), key=lambda a: str(a.get('date', '')), reverse=True)


def sync():
    """원격이 더 최신이면 받아서 합친다. 반환 {'status': 'synced'|'uptodate'|'busy'|'off'|'error', ...}"""
    cfg = settings()
    if not cfg:
        return {'status': 'off'}
    import updater
    if updater.LOCK.exists():
        return {'status': 'busy'}
    try:
        remote_live = json.loads(_get(_url(cfg, 'live.json')).decode('utf-8'))
        if not isinstance(remote_live, dict):
            raise ValueError('live.json 형식 오류')
        local_live = _load(updater.LIVE, {})
        rt, lt = _ts(remote_live.get('lastSuccess')), _ts(local_live.get('lastSuccess'))
        if rt is None or remote_live.get('status') == 'updating':
            return {'status': 'uptodate', 'reason': '원격에 완료된 데이터가 아직 없습니다.'}
        if lt is not None and rt <= lt:
            return {'status': 'uptodate', 'remote': remote_live.get('lastSuccess'), 'local': local_live.get('lastSuccess')}
        # 보조 파일 먼저 받고(실패하면 아무것도 바꾸지 않음), 마지막에 live.json 교체
        got = {}
        for name in ('news_archive.json', 'news_state.json', 'career_watch.json'):
            try:
                got[name] = json.loads(_get(_url(cfg, name)).decode('utf-8'))
            except Exception:
                pass
        if isinstance(got.get('news_archive.json'), list):
            from news_engine import ARCHIVE
            local_arch = _load(ARCHIVE, [])
            _save(ARCHIVE, merge_archive(local_arch if isinstance(local_arch, list) else [], got['news_archive.json']))
        if isinstance(got.get('news_state.json'), dict):
            from news_engine import STATE
            ls = _load(STATE, {})
            if len(got['news_state.json'].get('completed', [])) >= len(ls.get('completed', []) if isinstance(ls, dict) else []):
                _save(STATE, got['news_state.json'])
        if isinstance(got.get('career_watch.json'), dict):
            from career_watch import STATE as CW
            _save(CW, got['career_watch.json'])
        if local_live:
            _save(updater.LIVE.with_name('live.local.bak.json'), local_live)
        _save(updater.LIVE, remote_live)
        return {'status': 'synced', 'remote': remote_live.get('lastSuccess'), 'files': sorted(got)}
    except Exception as exc:
        return {'status': 'error', 'error': '%s: %s' % (type(exc).__name__, str(exc)[:160])}
