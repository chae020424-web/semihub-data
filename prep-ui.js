/* 취업 준비 도구: 지원 현황 · 면접 준비(질문은행/로드맵/기업 노트) · 내 스펙·진로(갭 분석/취업 vs 대학원)
   데이터는 이 브라우저의 localStorage에만 저장됩니다. 백업(내보내기/가져오기) 기능 제공. */
(function () {
  const D = window.SEMI_PREP_DATA;
  const KEY = 'semihub.prep.v1';
  const noSync = () => location.protocol === 'file:';
  const STATUSES = ['관심', '준비중', '서류제출', '서류합격', '코테·인적성', '면접', '최종합격', '불합격'];
  let mem = null; // localStorage 불가 시 메모리 저장
  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, x => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[x]));
  const safe = u => /^https?:\/\//i.test(String(u || '')) ? esc(u) : '#';
  const $ = id => document.getElementById(id);
  const blank = () => ({ _ts: 0, apps: [], qstat: {}, road: {}, notes: {}, ans: {}, spec: {}, career: {}, cover: [], profile: {}, exp: [], certs: [], grad: [], insight: {}, mock: {}, qsr: {}, tests: [] });

  function load() {
    if (mem) return mem;
    let d = null;
    try { d = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { d = null; }
    mem = Object.assign(blank(), d && typeof d === 'object' ? d : {});
    return mem;
  }
  // ---- 저장: localStorage(즉시) + 서버 파일(user_data.json, 로컬 서버 실행 시)
  let syncState = 'local', syncTimer = null, onAdopt = null, inited = false;
  const isEmpty = d => JSON.stringify(Object.assign(blank(), d, { _ts: 0 })) === JSON.stringify(blank());
  function badge() {
    const el = document.getElementById('ppSync');
    if (el) el.textContent = { synced: '서버 파일에 저장됨 (user_data.json, 매일 자동 백업)', local: '이 브라우저에만 저장 중 (로컬 서버로 접속하면 PC 파일에도 저장됩니다)', error: '서버 저장 실패 — 브라우저에는 저장됨. 서버가 켜져 있는지 확인하세요' }[syncState];
  }
  function adopt(d) {
    const m = load();
    Object.keys(m).forEach(k => delete m[k]);
    Object.assign(m, blank(), d);
    try { localStorage.setItem(KEY, JSON.stringify(m)); } catch (e) { /* ignore */ }
    if (onAdopt) onAdopt();
  }
  function push() {
    if (noSync()) return;
    fetch('/api/store', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ data: load() }) })
      .then(r => r.json().then(j => ({ s: r.status, j })))
      .then(x => { if (x.s === 200) syncState = 'synced'; else if (x.s === 409 && x.j && x.j.data) { adopt(x.j.data); syncState = 'synced'; } else syncState = 'error'; badge(); })
      .catch(() => { syncState = 'error'; badge(); });
  }
  function save() {
    const m = load(); m._ts = Date.now();
    let ok = true;
    try { localStorage.setItem(KEY, JSON.stringify(m)); } catch (e) { ok = false; }
    clearTimeout(syncTimer); syncTimer = setTimeout(push, 700);
    return ok;
  }
  function initSync() {
    if (inited || noSync()) return;
    inited = true;
    fetch('/api/store').then(r => r.json()).then(j => {
      const srv = (j && j.data) || {}, m = load();
      if (!isEmpty(srv) && (isEmpty(m) || (srv._ts || 0) > (m._ts || 0))) {
        if (!isEmpty(m)) { try { localStorage.setItem(KEY + '.replaced-backup', JSON.stringify(m)); } catch (e) { /* ignore */ } } // 덮어쓰기 전 로컬 사본 보관
        adopt(srv); syncState = 'synced';
      }
      else if (!isEmpty(m)) { if (!m._ts) m._ts = Date.now(); save(); }
      else syncState = 'synced';
      badge();
    }).catch(() => { syncState = 'error'; badge(); });
  }
  const S = () => load();

  const ui = { view: 'board', focus: '', cvq: '', prepTab: 'q', mineTab: 'profile', area: 'all', qmode: 'all', open: {}, role: '', noteCo: '', msg: '' };

  // ---------- 날짜
  const isoToday = () => { const n = new Date(); return n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0'); };
  const INTERVALS = [0, 1, 3, 7, 14, 30]; // 알겠음을 누를수록 복습 간격이 늘어남(일)
  function schedule(id, known) {
    const s = S(), cur = s.qsr[id] || { box: 0 }, box = known ? Math.min(cur.box + 1, INTERVALS.length - 1) : 0;
    const d = new Date(); d.setDate(d.getDate() + INTERVALS[box]);
    s.qsr[id] = { box, due: d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') };
  }
  const today = () => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };
  function dday(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || ''));
    if (!m) return null;
    return Math.round((new Date(+m[1], +m[2] - 1, +m[3]) - today()) / 86400000);
  }
  const ddayLabel = n => n == null ? '마감일 없음' : n < 0 ? '마감 지남' : n === 0 ? 'D-DAY' : 'D-' + n;
  const FINAL = ['최종합격', '불합격'];
  const STAGES = ['서류', '인적성(GSAT 등)', '코딩테스트', '직무면접', '임원면접', '1차 면접', '2차 면접', '최종', '기타'];
  function dueSoon(days) {
    return S().apps.filter(a => !FINAL.includes(a.status) && ['관심', '준비중'].includes(a.status)).map(a => ({ a, d: dday(a.deadline) }))
      .filter(x => x.d != null && x.d >= 0 && x.d <= (days || 3)).sort((x, y) => x.d - y.d);
  }

  // ---------- 지원 현황
  function uid() { return 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function addApp(o) {
    const s = S();
    if (o.url && s.apps.some(a => a.url === o.url)) return false;
    s.apps.push({ id: uid(), company: o.company || '', title: o.title || '', url: o.url || '', deadline: o.deadline || '', status: o.status || '관심', memo: '', addedAt: new Date().toISOString().slice(0, 10) });
    save(); return true;
  }
  function tracked(url) { return !!url && S().apps.some(a => a.url === url); }

  function banner() {
    const due = dueSoon(3);
    if (!due.length) return '';
    return `<div class="note notice-warning pp-banner"><b>마감 임박 ${due.length}건</b> · ` + due.map(x => `${esc(x.a.company)} ${esc(x.a.title)} (${ddayLabel(x.d)})`).join(' / ') + ` <button class="button" data-nav="tracker">지원 현황 보기</button></div>`;
  }

  function trackerPage(ctx) {
    const s = S();
    const list = s.apps.slice().sort((a, b) => {
      const fa = FINAL.includes(a.status) ? 1 : 0, fb = FINAL.includes(b.status) ? 1 : 0;
      if (fa !== fb) return fa - fb;
      const da = dday(a.deadline), db = dday(b.deadline);
      return (da == null ? 9999 : da < 0 ? 5000 - da : da) - (db == null ? 9999 : db < 0 ? 5000 - db : db);
    });
    const count = st => s.apps.filter(a => a.status === st).length;
    const stats = STATUSES.map(st => `<span class="pill">${st} <b>${count(st)}</b></span>`).join('');
    const board = () => `<div class="kb">${STATUSES.map(st => {
      const items = list.filter(a => a.status === st);
      return `<div class="kb-col" data-kb-col="${st}"><div class="kb-head"><span>${st}</span><b>${items.length}</b></div>${items.map(a => {
        const d = dday(a.deadline), hot = d != null && d >= 0 && d <= 3;
        return `<div class="kb-card ${hot ? 'pp-hot' : ''}" draggable="true" data-kb="${esc(a.id)}"><div class="kb-top">${window.SEMI_VIS ? window.SEMI_VIS.avatar(a.company, 28) : ''}<div><b>${esc(a.company || '(회사 미입력)')}</b><div class="subtitle">${esc(String(a.title || '').slice(0, 28))}</div></div></div>
          <div class="kb-foot">${FINAL.includes(a.status) ? '' : `<span class="tag ${hot ? 'orange' : ''}">${ddayLabel(d)}</span>`}<select class="select kb-sel" data-app-status="${esc(a.id)}" title="상태 변경">${STATUSES.map(s2 => `<option ${s2 === a.status ? 'selected' : ''}>${s2}</option>`).join('')}</select><button class="button kb-more" data-kb-open="${esc(a.id)}" title="자세히">⋯</button></div></div>`;
      }).join('') || '<div class="kb-empty">비어 있음</div>'}</div>`;
    }).join('')}</div>`;
    const shown = ui.view === 'list' && ui.focus ? list.filter(a => a.id === ui.focus) : list;
    const rows = shown.map(a => {
      const d = dday(a.deadline), cls = d != null && d >= 0 && d <= 3 ? 'pp-hot' : d != null && d < 0 ? 'pp-past' : '';
      return `<article class="pp-card ${cls}" data-app="${esc(a.id)}">
        <div class="pp-card-top"><div class="pp-who">${window.SEMI_VIS ? window.SEMI_VIS.avatar(a.company, 30) : ''}<b>${esc(a.company || '(회사 미입력)')}</b> <span class="subtitle">${esc(a.title)}</span></div><span class="tag ${d != null && d >= 0 && d <= 3 ? 'orange' : ''}">${FINAL.includes(a.status) ? a.status : ddayLabel(d)}</span></div>
        <div class="pp-card-mid"><label>상태 <select class="select" data-app-status="${esc(a.id)}">${STATUSES.map(st => `<option ${st === a.status ? 'selected' : ''}>${st}</option>`).join('')}</select></label>
        <label>마감 <input class="select" type="date" value="${esc(a.deadline)}" data-app-deadline="${esc(a.id)}"></label>
        ${a.url ? `<a class="button" href="${safe(a.url)}" target="_blank" rel="noopener noreferrer">공고 ↗</a>` : ''}
        <button class="button" data-app-del="${esc(a.id)}">삭제</button></div>
        <details class="pp-stages" ${(a.stages || []).length ? 'open' : ''}><summary>전형 일정·시험·후기 (${(a.stages || []).length})</summary>
        ${(a.stages || []).map((st, i) => `<div class="pp-stage"><select class="select" data-st-name="${esc(a.id)}:${i}">${STAGES.map(n => `<option ${n === st.name ? 'selected' : ''}>${n}</option>`).join('')}</select><input class="select" type="date" value="${esc(st.date || '')}" data-st-date="${esc(a.id)}:${i}"><select class="select" data-st-res="${esc(a.id)}:${i}">${['대기', '합격', '불합격'].map(n => `<option ${n === (st.result || '대기') ? 'selected' : ''}>${n}</option>`).join('')}</select><button class="button" data-st-del="${esc(a.id)}:${i}">×</button><textarea class="select pp-memo" rows="2" placeholder="유형·후기·질문받은 것" data-st-note="${esc(a.id)}:${i}">${esc(st.note || '')}</textarea></div>`).join('')}
        <button class="button" data-st-add="${esc(a.id)}">+ 전형 단계 추가</button></details>
        ${window.SEMI_ME ? window.SEMI_ME.checklist(a) : ''}
        <textarea class="select pp-memo" rows="2" placeholder="메모 (준비할 것 등)" data-app-memo="${esc(a.id)}">${esc(a.memo)}</textarea></article>`;
    }).join('') || '<div class="empty">아직 추적 중인 공고가 없습니다. 채용공고 탭의 “지원 추적” 버튼이나 아래 폼으로 추가하세요.</div>';
    return ctx.header('지원 현황', '공고별 상태·마감 D-day를 한곳에서 관리합니다 (이 브라우저에 저장)') + banner() +
      `<div class="panel"><div class="tags">${stats}</div></div>
      <div class="panel"><h3>공고 직접 추가</h3><div class="filters">
        <input class="select" id="ppCo" placeholder="회사" style="flex:1 1 150px"><input class="select" id="ppTitle" placeholder="직무/공고명" style="flex:2 1 220px">
        <input class="select" id="ppUrl" placeholder="공고 링크(https://…)" style="flex:2 1 220px"><input class="select" id="ppDl" type="date" title="마감일">
        <button class="button primary" id="ppAdd">추가</button></div><div class="subtitle" id="ppAddMsg">${esc(ui.msg)}</div></div>
      <div class="filters"><button class="button" id="meIcs">📅 캘린더(.ics)로 내려받기</button><span class="subtitle">마감·전형일·대학원·점수 만료일이 구글/애플 캘린더에 들어갑니다</span></div>
      <div class="filters"><button class="button ${ui.view === 'board' ? 'primary' : ''}" data-kb-view="board">보드</button><button class="button ${ui.view === 'list' && !ui.focus ? 'primary' : ''}" data-kb-view="list">목록·상세</button>${ui.focus ? '<button class="button" data-kb-view="list">← 전체 목록</button>' : ''}<span class="subtitle">${ui.view === 'board' ? '카드를 끌어서 다른 열에 놓으면 상태가 바뀝니다 (모바일은 카드의 상태 선택 사용)' : ''}</span></div>
      ${ui.view === 'board' ? (s.apps.length ? board() : rows) : `<div class="pp-list">${rows}</div>`}` + backupPanel();
  }

  function backupPanel() {
    return `<div class="panel"><h3>내 데이터 백업</h3><div class="subtitle" id="ppSync"></div><div class="subtitle">로컬 서버(start_semihub)로 접속하면 모든 데이터가 PC의 user_data.json에 저장되고 하루 한 번 user_backups 폴더에 백업됩니다. 아래 백업 파일은 다른 PC로 옮길 때 쓰세요.</div>
      <div class="filters"><button class="button" id="ppExport">백업 파일 내려받기</button><label class="button">백업 파일 불러오기<input type="file" id="ppImport" accept="application/json" hidden></label></div><div class="subtitle" id="ppBackupMsg"></div></div>`;
  }

  // ---------- 면접 준비
  function tabs(cur, items, attr) {
    return `<div class="filters pp-tabs">${items.map(([k, l]) => `<button class="button ${cur === k ? 'primary' : ''}" ${attr}="${k}">${l}</button>`).join('')}</div>`;
  }

  function qPanel() {
    const s = S(); let qs = D.Q.filter(q => ui.area === 'all' || q.area === ui.area);
    const tdy = isoToday();
    if (ui.qmode === 'due') qs = qs.filter(q => (s.qsr[q.id] && s.qsr[q.id].due <= tdy) || (!s.qsr[q.id] && s.qstat[q.id] !== 'know'));
    if (ui.qmode === 'unknown') qs = qs.filter(q => s.qstat[q.id] !== 'know');
    if (ui.qmode === 'know') qs = qs.filter(q => s.qstat[q.id] === 'know');
    const known = D.Q.filter(q => s.qstat[q.id] === 'know').length;
    const areaOpts = `<option value="all">전체 분야</option>` + Object.keys(D.AREAS).map(k => `<option value="${k}" ${ui.area === k ? 'selected' : ''}>${D.AREAS[k]} (${D.Q.filter(q => q.area === k).length})</option>`).join('');
    const items = qs.map(q => {
      const st = s.qstat[q.id], open = !!ui.open[q.id];
      return `<article class="pp-card"><div class="pp-card-top"><b>${esc(q.q)}</b><span class="tag">${esc(D.AREAS[q.area])}</span></div>
        ${open ? `<p class="pp-answer">${esc(q.a)}</p>` : ''}
        <div class="pp-card-mid"><button class="button" data-q-toggle="${q.id}">${open ? '답 숨기기' : '답 보기'}</button>
        <button class="button ${st === 'know' ? 'primary' : ''}" data-q-mark="${q.id}:know">알겠음</button>
        <button class="button ${st === 'unknown' ? 'primary' : ''}" data-q-mark="${q.id}:unknown">모르겠음</button>${s.qsr[q.id] ? `<span class="tag">다음 복습 ${esc(s.qsr[q.id].due.slice(5))}</span>` : ''}</div>${window.SEMI_ME ? window.SEMI_ME.mockBox(q) : ''}</article>`;
    }).join('') || '<div class="empty">조건에 맞는 질문이 없습니다.</div>';
    return `<div class="note">개념 설명은 교재 수준의 일반 지식으로 정리한 것이며, 실제 면접 출제나 회사별 정답을 보장하지 않습니다. 먼저 스스로 답해본 뒤 “답 보기”를 누르세요. “모르겠음”만 모아 반복하세요. 진행 <b>${known}/${D.Q.length}</b></div>
      <div class="filters"><select class="select" id="ppArea">${areaOpts}</select>
      <select class="select" id="ppQmode"><option value="all" ${ui.qmode === 'all' ? 'selected' : ''}>전체</option><option value="due" ${ui.qmode === 'due' ? 'selected' : ''}>오늘 복습할 것</option><option value="unknown" ${ui.qmode === 'unknown' ? 'selected' : ''}>모르겠음·미확인만</option><option value="know" ${ui.qmode === 'know' ? 'selected' : ''}>알겠음만</option></select></div>${items}`;
  }

  function roleTracks() {
    const roles = (window.SEMI_ROLES && window.SEMI_ROLES.roles) || [];
    return roles;
  }
  function roadFor(track) { return (D.ROAD[track] || []).map((r, i) => ({ id: track + ':' + i, type: r[0], text: r[1] })); }
  const TYPE = { course: '수강', skill: '역량', project: '경험', doc: '정리' };

  function roadPanel() {
    const s = S(), roles = roleTracks();
    const tracks = Object.keys(D.ROAD);
    const label = { process: '공정', device: '소자', equipment: '장비', packaging: '패키징', design: '설계', analysis: '시험·분석·품질', data: '데이터·SW', materials: '소재·EHS' };
    const cur = ui.road || 'design';
    const items = roadFor(cur), done = items.filter(i => s.road[i.id]).length;
    const rl = roles.filter(r => r.track === cur).map(r => esc(r.name)).join(' · ');
    return `<div class="filters">${tracks.map(t => `<button class="button ${cur === t ? 'primary' : ''}" data-road-track="${t}">${label[t]}</button>`).join('')}</div>
      <div class="panel"><h3>${label[cur]} 트랙 준비 체크리스트 <span class="tag">${done}/${items.length}</span></h3>
      <div class="pp-bar"><i style="width:${items.length ? Math.round(done / items.length * 100) : 0}%"></i></div>
      <div class="subtitle">${rl ? '관련 직무: ' + rl : ''}</div>
      ${items.map(i => `<label class="pp-check"><input type="checkbox" data-road="${i.id}" ${s.road[i.id] ? 'checked' : ''}><span class="tag">${TYPE[i.type]}</span> ${esc(i.text)}</label>`).join('')}
      <div class="subtitle" style="margin-top:10px">체크리스트는 일반적인 준비 항목이며, 지원 회사의 공고 요건을 최우선으로 하세요.</div></div>`;
  }

  function notesPanel() {
    const s = S(), cos = (window.SEMI_DB && window.SEMI_DB.companies) || [];
    const withNotes = Object.keys(s.notes).filter(k => (s.notes[k] || '').trim());
    const cur = ui.noteCo, c = cos.find(x => x.id === cur);
    return `<div class="filters"><input class="select" id="ppNoteSearch" list="ppCoList" placeholder="회사 이름으로 노트 열기" value="${esc(c ? c.name : '')}" style="flex:1 1 240px"><datalist id="ppCoList">${cos.map(x => `<option value="${esc(x.name)}">`).join('')}</datalist></div>
      ${c ? `<div class="panel"><h3>${esc(c.name)} 노트</h3><textarea class="select pp-memo" id="ppNote" rows="8" placeholder="지원 동기, 주력 제품/공정, 최근 이슈, 면접에서 말할 포인트, 궁금한 점…">${esc(s.notes[c.id] || '')}</textarea><div class="subtitle">입력하면 자동 저장됩니다.</div></div>` : '<div class="empty">회사를 선택하면 노트를 쓸 수 있습니다.</div>'}
      ${withNotes.length ? `<div class="panel"><h3>노트가 있는 회사</h3><div class="tags">${withNotes.map(id => { const co = cos.find(x => x.id === id); return `<button class="button" data-note-open="${esc(id)}">${esc(co ? co.name : id)}</button>`; }).join('')}</div></div>` : ''}`;
  }


  // ---------- 자소서 보관함
  const cnt = t => { const a = Array.from(String(t || '').replace(/\r\n/g, '\n')); return [a.length, a.filter(c => !/\s/.test(c)).length]; };
  function cvCounter(c) {
    const [w, n] = cnt(c.answer), lim = +c.limit || 0, over = lim && w > lim;
    return `<span class="${over ? 'pp-over' : ''}">공백 포함 <b>${w}</b>${lim ? ' / ' + lim : ''}자 · 공백 제외 <b>${n}</b>자${over ? ' · ' + (w - lim) + '자 초과' : ''}</span>`;
  }
  function cvItems() {
    const s = S(), q = (ui.cvq || '').trim().toLowerCase();
    const list = (s.cover || []).filter(c => !q || [c.company, c.question, c.answer].join(' ').toLowerCase().includes(q));
    return list.map(c => `<article class="pp-card" data-cv="${esc(c.id)}">
      <div class="pp-card-top"><div><b>${esc(c.company || '(회사 미입력)')}</b> <span class="subtitle">${esc(c.question)}</span></div><span class="subtitle" id="ppCnt-${esc(c.id)}">${cvCounter(c)}</span></div>
      <textarea class="select pp-memo" rows="8" data-cv-ans="${esc(c.id)}" placeholder="답변을 작성하세요">${esc(c.answer)}</textarea>
      <div class="pp-card-mid"><label>글자 수 제한 <input class="select" type="number" min="0" style="width:90px" value="${esc(c.limit)}" data-cv-limit="${esc(c.id)}"></label>
      ${(S().exp || []).length ? `<select class="select" data-cv-exp="${esc(c.id)}" style="max-width:190px"><option value="">경험 넣기…</option>${S().exp.map(e => `<option value="${esc(e.id)}">${esc(e.title)}</option>`).join('')}</select>` : ''}<button class="button" data-cv-copy="${esc(c.id)}">복사</button><button class="button" data-cv-del="${esc(c.id)}">삭제</button></div></article>`).join('')
      || '<div class="empty">' + (q ? '검색 결과가 없습니다.' : '아직 저장한 문항이 없습니다. 위에서 추가하세요.') + '</div>';
  }
  function coverPanel() {
    return `<div class="note">회사별 자소서 문항과 답변을 저장하고, 다른 회사 문항에 재사용할 때 아래 검색으로 찾아 복사하세요. 글자 수 기준(공백·줄바꿈 처리)은 회사 지원 화면마다 달라서, 제출 직전에는 해당 화면에서 다시 확인하세요.</div>
      <div class="panel"><h3>문항 추가</h3><div class="filters">
      <input class="select" id="ppCvCo" placeholder="회사" style="flex:1 1 140px"><input class="select" id="ppCvQ" placeholder="문항 (예: 지원 동기 및 포부)" style="flex:3 1 260px">
      <input class="select" id="ppCvLimit" type="number" min="0" placeholder="글자 수 제한" value="1000" style="flex:0 1 120px"><button class="button primary" id="ppCvAdd">추가</button></div></div>
      <div class="filters"><input class="select" id="ppCvSearch" placeholder="회사·문항·답변 내용으로 검색 (재사용할 답변 찾기)" value="${esc(ui.cvq)}" style="flex:1 1 300px"></div>
      <div id="ppCvList">${cvItems()}</div>`;
  }
  function bindCover() {
    const s = S(), root = $('ppCvList'); if (!root) return;
    const add = $('ppCvAdd');
    if (add) add.onclick = () => {
      const co = $('ppCvCo').value.trim(), q = $('ppCvQ').value.trim(); if (!co && !q) return;
      s.cover.unshift({ id: uid(), company: co, question: q, limit: parseInt($('ppCvLimit').value, 10) || 0, answer: '', updatedAt: new Date().toISOString().slice(0, 10) });
      save(); ui.cvq = ''; rerender();
    };
    const sr = $('ppCvSearch');
    if (sr) sr.oninput = () => { ui.cvq = sr.value; root.innerHTML = cvItems(); bindItems(); };
    function bindItems() {
      root.querySelectorAll('[data-cv-ans]').forEach(el => el.oninput = () => {
        const c = s.cover.find(x => x.id === el.dataset.cvAns); if (!c) return;
        c.answer = el.value; c.updatedAt = new Date().toISOString().slice(0, 10); save();
        const sp = $('ppCnt-' + c.id); if (sp) sp.innerHTML = cvCounter(c);
      });
      root.querySelectorAll('[data-cv-limit]').forEach(el => el.oninput = () => {
        const c = s.cover.find(x => x.id === el.dataset.cvLimit); if (!c) return;
        c.limit = parseInt(el.value, 10) || 0; save();
        const sp = $('ppCnt-' + c.id); if (sp) sp.innerHTML = cvCounter(c);
      });
      root.querySelectorAll('[data-cv-del]').forEach(el => el.onclick = () => {
        if (!confirm('이 문항을 삭제할까요? 작성한 답변도 함께 삭제됩니다.')) return;
        s.cover = s.cover.filter(x => x.id !== el.dataset.cvDel); save(); root.innerHTML = cvItems(); bindItems();
      });
      root.querySelectorAll('[data-cv-exp]').forEach(el => el.onchange = () => {
        const c = s.cover.find(x => x.id === el.dataset.cvExp), e = (s.exp || []).find(x => x.id === el.value); if (!c || !e) return;
        c.answer = (c.answer ? c.answer + '\n\n' : '') + [e.situation, e.task, e.action, e.result].filter(Boolean).join(' '); save(); root.innerHTML = cvItems(); bindItems();
      });
      root.querySelectorAll('[data-cv-copy]').forEach(el => el.onclick = () => {
        const c = s.cover.find(x => x.id === el.dataset.cvCopy); if (!c) return;
        const done = () => { el.textContent = '복사됨 ✓'; setTimeout(() => { el.textContent = '복사'; }, 1500); };
        try { navigator.clipboard.writeText(c.answer).then(done, () => { const ta = root.querySelector('[data-cv-ans="' + c.id + '"]'); ta.select(); document.execCommand('copy'); done(); }); }
        catch (e) { const ta = root.querySelector('[data-cv-ans="' + c.id + '"]'); ta.select(); try { document.execCommand('copy'); done(); } catch (e2) { el.textContent = '직접 선택해 복사하세요'; } }
      });
    }
    bindItems();
  }

  function prepPage(ctx) {
    const body = ui.prepTab === 'q' ? qPanel() : ui.prepTab === 'road' ? roadPanel() : ui.prepTab === 'cover' ? coverPanel() : notesPanel();
    return ctx.header('면접 준비', '기술면접 질문은행 · 자소서 보관함 · 직무 로드맵 · 기업별 노트') +
      tabs(ui.prepTab, [['q', '기술면접 질문은행'], ['cover', '자소서 보관함'], ['road', '직무 로드맵'], ['notes', '기업 노트']], 'data-prep-tab') + body;
  }

  // ---------- 내 스펙·진로
  const SPEC_FIELDS = [['gpa', '학점 (예: 3.8 / 4.5)'], ['eng', '영어 성적 (예: TOEIC 850, OPIc IH)'], ['courses', '수강한 핵심 과목 (쉼표로 구분)'], ['projects', '프로젝트·인턴·연구 경험'], ['certs', '자격증·툴 (예: 전기기사, Verilog, Python)']];

  function gapPanel() {
    const s = S(), roles = roleTracks();
    if (!ui.role && window.SEMI_ME) { const pr = window.SEMI_ME.prof().roles; if (pr.length) ui.role = pr[0]; }
    const r = roles.find(x => x.id === ui.role) || null;
    const opts = `<option value="">직무를 선택하세요</option>` + roles.map(x => `<option value="${esc(x.id)}" ${r && r.id === x.id ? 'selected' : ''}>${esc(x.category)} · ${esc(x.name)}</option>`).join('');
    let res = '';
    if (r) {
      const items = roadFor(r.track), done = items.filter(i => s.road[i.id]), todo = items.filter(i => !s.road[i.id]);
      const spec = (s.spec.courses || '') + ' ' + (s.spec.projects || '') + ' ' + (s.spec.certs || '') + ' ' + ((s.profile && s.profile.skills) || '') + ' ' + (s.exp || []).map(e => e.title + ' ' + (e.tags || '') + ' ' + (e.action || '')).join(' ');
      const prepTerms = String(r.prep || '').split(/[,·\/]|\s{2,}/).map(t => t.trim()).filter(t => t.length > 1);
      const hit = prepTerms.filter(t => spec.toLowerCase().includes(t.toLowerCase().replace(/\s*이해$/, '')));
      res = `<div class="panel"><h3>${esc(r.name)}</h3><p class="subtitle">${esc(r.work)}</p>
        <p><b>직무가 요구하는 준비(직무 설명 기준)</b><br>${esc(r.prep)}</p>
        <p><b>입력한 스펙과 겹치는 키워드</b> ${hit.length ? hit.map(h => `<span class="pill">${esc(h)}</span>`).join('') : '<span class="subtitle">겹치는 키워드 없음 (스펙·프로필·경험 은행에 쓴 단어와 비교한 단순 일치)</span>'}</p>
        <p><b>로드맵 진행</b> ${done.length}/${items.length}</p>
        ${todo.length ? `<p><b>아직 안 한 항목</b></p><ul>${todo.map(i => `<li>[${TYPE[i.type]}] ${esc(i.text)}</li>`).join('')}</ul>` : '<p>로드맵 항목을 모두 완료했습니다.</p>'}
        <div class="subtitle">서류 합격 기준(학점·어학 커트라인)은 회사가 공개하지 않으므로 이 도구는 점수 판정을 하지 않습니다. 공고의 자격 요건과 직접 비교하세요.</div></div>`;
    }
    return `<div class="panel"><h3>내 스펙 입력</h3>${SPEC_FIELDS.map(([k, l]) => `<label class="pp-field">${l}<input class="select" data-spec="${k}" value="${esc(s.spec[k] || '')}"></label>`).join('')}<div class="subtitle">입력하면 자동 저장됩니다.</div></div>
      <div class="filters"><select class="select" id="ppRole" style="flex:1 1 280px">${opts}</select></div>${res}`;
  }

  const CDEF = { y1: 5000, y2: 6500, stipend: 1000, tuition: 0, grow: 0 };
  function careerCalc(c) {
    const o = Object.assign({}, CDEF, c), rows = []; let a = 0, b = 0, be = null;
    for (let t = 1; t <= 10; t++) {
      a += o.y1 * Math.pow(1 + o.grow / 100, t - 1);
      b += t <= 2 ? o.stipend - o.tuition : o.y2 * Math.pow(1 + o.grow / 100, t - 3);
      rows.push([t, Math.round(a), Math.round(b)]);
      if (be == null && b >= a) be = t;
    }
    return { rows, be };
  }
  function careerPanel() {
    const s = S(), c = Object.assign({}, CDEF, s.career), r = careerCalc(c);
    const f = [['y1', '학사 취업 시 연 소득 (만원)'], ['y2', '석사 후 취업 시 연 소득 (만원)'], ['stipend', '석사 재학 중 연 수입 (인건비·장학, 만원)'], ['tuition', '석사 재학 중 연 지출 (등록금 본인부담 등, 만원)'], ['grow', '연 소득 상승률 (%)']];
    return `<div class="note">이 계산기는 <b>직접 입력한 값만</b>으로 누적 소득을 비교합니다. 기본값은 예시일 뿐 실제 연봉 정보가 아닙니다. 석사 과정은 2년으로 가정하며 세금·복지·학비 지원 여부, 직무별 석사 우대, 군 복무는 반영하지 않습니다.</div>
      <div class="panel">${f.map(([k, l]) => `<label class="pp-field">${l}<input class="select" type="number" step="any" data-career="${k}" value="${esc(c[k])}"></label>`).join('')}</div>
      <div class="panel"><h3>누적 소득 비교 (만원)</h3><div class="subtitle">${r.be ? `석사 경로의 누적 소득이 ${r.be}년차에 취업 경로를 넘어섭니다.` : '10년 안에는 석사 경로가 취업 경로를 넘지 못합니다.'}</div>
      <table class="pp-table"><thead><tr><th>년차</th><th>학사 취업</th><th>석사 후 취업</th><th>차이</th></tr></thead><tbody>${r.rows.map(x => `<tr><td>${x[0]}</td><td>${x[1].toLocaleString()}</td><td>${x[2].toLocaleString()}</td><td>${(x[2] - x[1]).toLocaleString()}</td></tr>`).join('')}</tbody></table></div>
      <div class="panel"><h3>숫자 밖에서 따져볼 것</h3><ul><li>지원하려는 직무 공고가 석사 이상을 요구하거나 우대하는가 (연구개발·설계 직무는 공고마다 다름)</li><li>학부 연구실 경험, 관심 세부 분야(소자/공정/회로)가 분명한가</li><li>지도교수·연구실의 기업 연계 및 진출 실적</li><li>학업 지속 의지와 체력, 시간·기회비용</li></ul></div>`;
  }

  function minePage(ctx) {
    return ctx.header('내 프로필·스펙', '관심 직무·기업 설정 · 경험 정리 · 갭 분석 · 어학/자격 · 대학원 · 진로 비교') +
      tabs(ui.mineTab, [['profile', '내 프로필·관심'], ['exp', '경험 은행'], ['gap', '직무 갭 분석'], ['certs', '어학·자격'], ['grad', '대학원'], ['tests', '시험 기록'], ['career', '취업 vs 대학원'], ['backup', '백업·복구']], 'data-mine-tab') +
      (window.SEMI_ME && window.SEMI_ME.has(ui.mineTab) ? window.SEMI_ME.panel(ui.mineTab) : ui.mineTab === 'career' ? careerPanel() : gapPanel());
  }

  // ---------- 뉴스 → 1분 면접 답변
  function answerBox(id) {
    const v = S().ans[id] || '';
    return `<div class="tech-dotted"><b>✎ 나의 1분 면접 답변</b><span>이 기사로 면접에서 말할 내용을 적어두세요 (자동 저장)</span></div><textarea class="select pp-memo" id="ppAns" data-ans="${esc(id)}" rows="5" placeholder="① 이슈 한 줄 요약 ② 기술적 의미 ③ 내 직무/지원 회사와의 연결">${esc(v)}</textarea>`;
  }
  function bindAnswer(root) {
    const t = (root || document).querySelector('#ppAns');
    if (t) t.oninput = () => { const s = S(); s.ans[t.dataset.ans] = t.value; save(); };
  }

  // ---------- 바인딩
  let rerender = null;
  function bind(render0, page) {
    const render = () => setTimeout(render0, 0); // 입력 이벤트 도중 DOM을 교체하지 않도록 지연
    rerender = render;
    onAdopt = render;
    initSync();
    const on = (sel, fn) => document.querySelectorAll(sel).forEach(fn);
    const s = S();
    if (page === 'tracker') {
      const add = $('ppAdd');
      if (add) add.onclick = () => {
        const co = $('ppCo').value.trim(), ti = $('ppTitle').value.trim(), url = $('ppUrl').value.trim(), dl = $('ppDl').value;
        if (!co && !ti) { ui.msg = '회사 또는 공고명을 입력하세요.'; $('ppAddMsg').textContent = ui.msg; return; }
        if (url && !/^https?:\/\//i.test(url)) { $('ppAddMsg').textContent = '링크는 http(s)://로 시작해야 합니다.'; return; }
        const ok = addApp({ company: co, title: ti, url, deadline: dl });
        ui.msg = ok ? '추가했습니다.' : '이미 같은 링크의 공고가 있습니다.'; render();
      };
      on('[data-kb-view]', el => el.onclick = () => { ui.view = el.dataset.kbView; ui.focus = ''; render(); });
      on('[data-kb-open]', el => el.onclick = () => { ui.view = 'list'; ui.focus = el.dataset.kbOpen; render(); window.scrollTo(0, 0); });
      on('.kb-card', el => { el.ondragstart = e => { e.dataTransfer.setData('text/plain', el.dataset.kb); e.dataTransfer.effectAllowed = 'move'; el.classList.add('drag'); }; el.ondragend = () => el.classList.remove('drag'); });
      on('.kb', kb => { kb.ondragover = e => { const r = kb.getBoundingClientRect(); if (e.clientX < r.left + 70) kb.scrollLeft -= 18; else if (e.clientX > r.right - 70) kb.scrollLeft += 18; }; });
      on('.kb-col', col => {
        col.ondragover = e => { e.preventDefault(); col.classList.add('over'); };
        col.ondragleave = () => col.classList.remove('over');
        col.ondrop = e => { e.preventDefault(); col.classList.remove('over'); const a = s.apps.find(x => x.id === e.dataTransfer.getData('text/plain')); if (a && a.status !== col.dataset.kbCol) { a.status = col.dataset.kbCol; save(); render(); } };
      });
      on('[data-app-status]', el => el.onchange = () => { const a = s.apps.find(x => x.id === el.dataset.appStatus); if (a) { a.status = el.value; save(); render(); } });
      on('[data-app-deadline]', el => el.onchange = () => { const a = s.apps.find(x => x.id === el.dataset.appDeadline); if (a) { a.deadline = el.value; save(); render(); } });
      on('[data-app-memo]', el => el.oninput = () => { const a = s.apps.find(x => x.id === el.dataset.appMemo); if (a) { a.memo = el.value; save(); } });
      on('[data-app-del]', el => el.onclick = () => { if (confirm('이 공고를 지원 현황에서 삭제할까요?')) { s.apps = s.apps.filter(x => x.id !== el.dataset.appDel); save(); render(); } });
      const sa = (id, i) => { const a = s.apps.find(x => x.id === id); return a && a.stages && a.stages[+i]; };
      on('[data-st-add]', el => el.onclick = () => { const a = s.apps.find(x => x.id === el.dataset.stAdd); if (a) { (a.stages = a.stages || []).push({ name: '서류', date: '', result: '대기', note: '' }); save(); render(); } });
      on('[data-st-name]', el => el.onchange = () => { const [id, i] = el.dataset.stName.split(':'), x = sa(id, i); if (x) { x.name = el.value; save(); } });
      on('[data-st-date]', el => el.onchange = () => { const [id, i] = el.dataset.stDate.split(':'), x = sa(id, i); if (x) { x.date = el.value; save(); render(); } });
      on('[data-st-res]', el => el.onchange = () => { const [id, i] = el.dataset.stRes.split(':'), x = sa(id, i); if (x) { x.result = el.value; save(); } });
      on('[data-st-note]', el => el.oninput = () => { const [id, i] = el.dataset.stNote.split(':'), x = sa(id, i); if (x) { x.note = el.value; save(); } });
      on('[data-st-del]', el => el.onclick = () => { const [id, i] = el.dataset.stDel.split(':'), a = s.apps.find(x => x.id === id); if (a && confirm('이 전형 단계를 삭제할까요?')) { a.stages.splice(+i, 1); save(); render(); } });
      bindBackup(render);
      badge();
    }
    if (page === 'prep') {
      on('[data-prep-tab]', el => el.onclick = () => { ui.prepTab = el.dataset.prepTab; render(); });
      const ar = $('ppArea'); if (ar) ar.onchange = () => { ui.area = ar.value; render(); };
      const qm = $('ppQmode'); if (qm) qm.onchange = () => { ui.qmode = qm.value; render(); };
      on('[data-q-toggle]', el => el.onclick = () => { ui.open[el.dataset.qToggle] = !ui.open[el.dataset.qToggle]; render(); });
      on('[data-q-mark]', el => el.onclick = () => { const [id, v] = el.dataset.qMark.split(':'); const was = s.qstat[id] === v; s.qstat[id] = was ? '' : v; if (was) delete s.qsr[id]; else schedule(id, v === 'know'); save(); render(); });
      on('[data-road-track]', el => el.onclick = () => { ui.road = el.dataset.roadTrack; render(); });
      on('[data-road]', el => el.onchange = () => { s.road[el.dataset.road] = el.checked; save(); render(); });
      const ns = $('ppNoteSearch');
      if (ns) ns.onchange = () => { const c = ((window.SEMI_DB && window.SEMI_DB.companies) || []).find(x => x.name === ns.value.trim()); if (c) { ui.noteCo = c.id; render(); } };
      on('[data-note-open]', el => el.onclick = () => { ui.noteCo = el.dataset.noteOpen; render(); });
      bindCover();
      const nt = $('ppNote'); if (nt) nt.oninput = () => { s.notes[ui.noteCo] = nt.value; save(); };
    }
    if (page === 'mine') {
      on('[data-mine-tab]', el => el.onclick = () => { ui.mineTab = el.dataset.mineTab; render(); });
      if (window.SEMI_ME) window.SEMI_ME.bind(render, ui.mineTab);
      if (ui.mineTab === 'backup') { bindBackup(render); badge(); }
      on('[data-spec]', el => { el.oninput = () => { s.spec[el.dataset.spec] = el.value; save(); }; el.onchange = () => render(); });
      const ro = $('ppRole'); if (ro) ro.onchange = () => { ui.role = ro.value; render(); };
      on('[data-career]', el => el.onchange = () => { const v = parseFloat(el.value); s.career[el.dataset.career] = isFinite(v) ? v : 0; save(); render(); });
    }
  }

  function bindBackup() {
    const ex = $('ppExport');
    if (ex) ex.onclick = () => {
      const blob = new Blob([JSON.stringify({ app: 'semihub-prep', version: 1, exportedAt: new Date().toISOString(), data: S() }, null, 1)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = 'semihub-backup-' + new Date().toISOString().slice(0, 10) + '.json'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
    const im = $('ppImport');
    if (im) im.onchange = () => {
      const f = im.files && im.files[0]; if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        const msg = $('ppBackupMsg');
        try {
          const j = JSON.parse(rd.result);
          if (!j || j.app !== 'semihub-prep' || typeof j.data !== 'object') throw new Error('형식');
          if (!confirm('현재 저장된 데이터를 백업 파일 내용으로 바꿉니다. 계속할까요?')) return;
          adopt(j.data); save(); rerender && rerender();
        } catch (e) { if (msg) msg.textContent = '백업 파일 형식이 올바르지 않습니다.'; }
      };
      rd.readAsText(f);
    };
  }

  // 공고 카드의 '지원 추적' 버튼: 목록이 다시 그려져도 동작하도록 문서 전체에서 위임 처리
  document.addEventListener('click', ev => {
    const el = ev.target.closest && ev.target.closest('[data-track-add]'); if (!el || el.disabled) return;
    const d = el.dataset;
    addApp({ company: d.co, title: d.ti, url: d.url, deadline: /^\d{4}-\d{2}-\d{2}/.test(d.dl || '') ? d.dl.slice(0, 10) : '' });
    el.textContent = '추적 중 ✓'; el.disabled = true;
  });

  window.SEMI_PREP = {
    pages: { tracker: trackerPage, prep: prepPage, mine: minePage },
    api: { S, save, esc, safe, uid, dday, adopt }, ui,
    statuses: STATUSES, bind, banner, dueSoon, addApp, tracked, answerBox, bindAnswer, careerCalc, dday, _state: S
  };
})();
