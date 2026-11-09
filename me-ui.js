/* 내 프로필 · 경험 은행 · 어학/자격 · 대학원 · 오늘 할 일 · 캘린더(.ics) · AI(뉴스 내 관점 / 모의 면접)
   prep-ui.js 의 저장소(S/save)를 공유한다. */
(function () {
  const P = window.SEMI_PREP; if (!P) return;
  const { S, save, esc, safe, uid, dday } = P.api;
  const $ = id => document.getElementById(id);
  const roles = () => (window.SEMI_ROLES && window.SEMI_ROLES.roles) || [];
  const cos = () => (window.SEMI_DB && window.SEMI_DB.companies) || [];
  const norm = s => String(s == null ? '' : s).toLowerCase().replace(/\s+/g, '');
  const today = () => { const n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); };
  const iso = d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  const ui = { exp: '', notifyMsg: '', aiMsg: '', mockOpen: {}, mockBusy: {}, insightBusy: {}, insightErr: {} };
  let rerender = () => {};

  // ---------- 프로필 / 매칭
  const prof = () => Object.assign({ level: '신입', roles: [], companies: [], skills: '', keywords: '' }, S().profile || {});
  const setProf = patch => { const s = S(); s.profile = Object.assign(prof(), patch); save(); };
  function terms(p) {
    const out = new Set();
    roles().filter(r => p.roles.includes(r.id)).forEach(r => String(r.tags || '').split(/\s+/).forEach(t => { if (t.length >= 2) out.add(t.toLowerCase()); }));
    String(p.keywords || '').split(/[,\s]+/).forEach(t => { if (t.length >= 2) out.add(t.toLowerCase()); });
    return [...out];
  }
  // 영문 짧은 키워드(예: ic)가 service 같은 단어 안에서 걸리지 않도록, 영문/숫자 키워드는 단어 경계로 비교한다
  function termIn(hay, t) {
    t = String(t).toLowerCase();
    if (/^[a-z0-9+.\-]+$/.test(t)) return new RegExp('(^|[^a-z0-9])' + t.replace(/[.+\-]/g, '\\$&') + '($|[^a-z0-9])').test(hay);
    return hay.replace(/\s+/g, '').includes(t.replace(/\s+/g, ''));
  }
  const cats = p => new Set(roles().filter(r => p.roles.includes(r.id)).map(r => r.category));
  const coNames = p => cos().filter(c => p.companies.includes(c.id)).map(c => norm(c.name));
  const hasFilter = p => !!(p.roles.length || p.companies.length || String(p.keywords).trim());
  function matchJob(j, p) {
    p = p || prof();
    const lv = String(j.level || '');
    if (p.level === '신입' && /경력/.test(lv) && !/신입/.test(lv)) return false;
    if (p.level === '경력' && /신입/.test(lv) && !/경력/.test(lv)) return false;
    if (!hasFilter(p)) return true;
    const co = norm(j.company), hay = [j.title, j.category, j.company].join(' ').toLowerCase();
    if (coNames(p).some(n => n && co && (co.includes(n) || n.includes(co)))) return true;
    return terms(p).some(t => termIn(hay, t));
  }
  function matchNews(n, p) {
    p = p || prof();
    if (!hasFilter(p)) return 0;
    let score = 0;
    const co = norm(n.company) + norm(n.source), hay = [n.title, n.summary, n.category].join(' ').toLowerCase();
    if (coNames(p).some(x => x && co.includes(x))) score += 3;
    if (cats(p).has(n.category)) score += 2;
    if (terms(p).some(t => termIn(hay, t))) score += 1;
    return score;
  }

  // ---------- 공통 UI
  const chip = (on, attr, label) => `<button type="button" class="me-chip ${on ? 'on' : ''}" ${attr}>${esc(label)}</button>`;
  const PRESET = ['삼성전자', 'SK하이닉스', 'DB하이텍', 'ASML', '도쿄일렉트론', 'Lam', 'Applied', 'KLA'];

  function profilePanel() {
    const p = prof(), cl = cos();
    const cats2 = [...new Set(roles().map(r => r.category))];
    const roleBlock = cats2.map(c => `<div class="me-group"><b>${esc(c)}</b><div class="me-chips">${roles().filter(r => r.category === c).map(r => chip(p.roles.includes(r.id), `data-me-role="${esc(r.id)}"`, r.name)).join('')}</div></div>`).join('');
    const presets = PRESET.map(n => cl.find(c => norm(c.name).includes(norm(n)))).filter(Boolean);
    const picked = cl.filter(c => p.companies.includes(c.id));
    return `<div class="note">여기서 정한 관심사로 <b>오늘 할 일, 뉴스 정렬, 공고 필터, 카톡 알림</b>이 모두 맞춰집니다. 아무것도 고르지 않으면 전체를 보여 줍니다.</div>
    <div class="panel"><h3>찾는 공고</h3><div class="me-chips">${['신입', '경력', '무관'].map(l => chip(p.level === l, `data-me-level="${l}"`, l)).join('')}</div></div>
    <div class="panel"><h3>관심 직무</h3>${roleBlock}</div>
    <div class="panel"><h3>관심 기업</h3><div class="me-chips">${picked.map(c => chip(true, `data-me-co="${esc(c.id)}"`, c.name + ' ×')).join('') || '<span class="subtitle">아직 없음</span>'}</div>
      <div class="filters"><input class="select" id="meCoSearch" list="meCoList" placeholder="기업 이름 검색 후 선택" style="flex:1 1 240px"><datalist id="meCoList">${cl.map(c => `<option value="${esc(c.name)}">`).join('')}</datalist></div>
      <div class="subtitle">자주 찾는 기업</div><div class="me-chips">${presets.filter(c => !p.companies.includes(c.id)).map(c => chip(false, `data-me-co="${esc(c.id)}"`, '+ ' + c.name)).join('')}</div></div>
    <div class="panel"><h3>내 기술·과목·툴</h3><textarea class="select pp-memo" id="meSkills" rows="3" placeholder="예: Verilog, Python, 디지털논리회로, 반도체소자, Vivado">${esc(p.skills)}</textarea>
      <h3 style="margin-top:14px">추가 키워드 (공고·뉴스 매칭용)</h3><input class="select" id="meKeywords" style="width:100%;max-width:none;box-sizing:border-box" placeholder="예: 설계, RTL, HBM, 패키지" value="${esc(p.keywords)}"></div>
    <div class="panel"><h3>카카오톡 알림 미리보기</h3><div class="subtitle">위 관심사 기준으로 지금 알림이 어떻게 가는지 확인합니다. 로컬 서버(start_semihub)로 접속했을 때만 동작합니다.</div>
      <div class="filters"><button class="button" id="meNotifyPreview">알림 미리보기</button><button class="button" id="meNotifyTest">카톡 테스트 전송</button></div>
      <pre class="me-pre" id="meNotifyOut">${esc(ui.notifyMsg)}</pre></div>
    <div class="panel"><h3>AI 취업전략 카톡 요약 (선택)</h3>
      <div class="subtitle">자동 갱신(6시간마다) 때, 최근 3일 안의 내 관심 뉴스를 AI가 3줄(200자 이내)로 요약해 카톡 "나와의 채팅"으로 보냅니다. 같은 기사는 한 번만, 하루 최대 4건입니다. 서버에 <b>GEMINI_API_KEY 환경변수</b>가 있어야 하고 카톡이 연결되어 있어야 합니다.</div>
      <label class="me-check"><input type="checkbox" id="meAiOn" ${p.aiDigest ? 'checked' : ''}> AI 요약 받기</label>
      <label class="me-check"><input type="checkbox" id="meAiConsent" ${p.aiConsent ? 'checked' : ''}> 내 기술·경험을 AI(Google Gemini)에 보내 더 맞춤으로 요약하는 데 동의합니다 (선택)</label>
      <div class="note notice-warning">동의하지 않으면 기사 제목·요약과 공고 정보만 AI에 보내고, 내 기술·경험은 보내지 않습니다. 체크를 끄면 즉시 중단됩니다. Gemini 무료 등급은 입력이 제품 개선에 쓰일 수 있습니다.</div>
      <div class="filters"><button class="button" id="meAiPreview">AI 요약 미리보기 (전송 안 함)</button></div>
      <pre class="me-pre" id="meAiOut">${esc(ui.aiMsg || '')}</pre></div>`;
  }

  // ---------- 경험 은행
  function expPanel() {
    const s = S(), list = s.exp || [];
    const f = [['situation', '상황 (어떤 배경/과제였나)'], ['task', '과제·목표 (내가 맡은 것)'], ['action', '행동 (내가 구체적으로 한 일)'], ['result', '결과 (수치·배운 점)']];
    return `<div class="note">프로젝트·수업·활동 경험을 STAR로 한 번만 정리해 두면 자소서와 면접 답변에서 계속 꺼내 쓸 수 있습니다. 자소서 보관함에서 "경험 넣기"로 가져갑니다.</div>
    <div class="panel"><h3>경험 추가</h3><div class="filters"><input class="select" id="meExpTitle" placeholder="경험 이름 (예: FPGA FIFO 설계 프로젝트)" style="flex:1 1 300px"><input class="select" id="meExpTags" placeholder="태그 (예: 설계, Verilog, 팀)" style="flex:1 1 200px"><button class="button primary" id="meExpAdd">추가</button></div></div>
    ${list.map(e => `<article class="pp-card"><div class="pp-card-top"><b>${esc(e.title)}</b><span class="tag">${esc(e.tags || '태그 없음')}</span></div>
      ${f.map(([k, l]) => `<label class="pp-field">${l}<textarea class="select pp-memo" rows="2" data-exp="${esc(e.id)}:${k}">${esc(e[k] || '')}</textarea></label>`).join('')}
      <div class="pp-card-mid"><button class="button" data-exp-del="${esc(e.id)}">삭제</button></div></article>`).join('') || '<div class="empty">아직 정리한 경험이 없습니다.</div>'}`;
  }
  const expText = e => `[${e.title}]\n상황: ${e.situation || ''}\n과제: ${e.task || ''}\n행동: ${e.action || ''}\n결과: ${e.result || ''}`;

  // ---------- 어학·자격
  function certExpiry(c) {
    const y = parseFloat(c.valid);
    if (!c.date || !(y > 0)) return null;
    const d = new Date(c.date + 'T00:00:00'); if (isNaN(d)) return null;
    d.setFullYear(d.getFullYear() + Math.floor(y)); if (y % 1) d.setMonth(d.getMonth() + Math.round((y % 1) * 12));
    return iso(d);
  }
  function certPanel() {
    const list = S().certs || [];
    return `<div class="note">점수 유효기간은 공고마다 인정 기간이 다를 수 있습니다. 아래 기본값(2년)은 예시이니 지원하는 공고 기준으로 고쳐서 쓰세요. 유효기간 0은 만료 없음입니다.</div>
    <div class="panel"><h3>어학·자격 추가</h3><div class="filters"><input class="select" id="meCertName" placeholder="이름 (예: TOEIC, OPIc, 전기기사)" style="flex:1 1 220px"><input class="select" id="meCertScore" placeholder="점수/등급" style="flex:0 1 130px"><input class="select" type="date" id="meCertDate" title="취득일"><input class="select" type="number" step="0.5" min="0" id="meCertValid" value="2" style="width:90px" title="유효기간(년)"><button class="button primary" id="meCertAdd">추가</button></div></div>
    ${list.map(c => { const ex = certExpiry(c), d = ex ? dday(ex) : null; return `<article class="pp-card ${d != null && d <= 90 ? 'pp-hot' : ''}"><div class="pp-card-top"><div><b>${esc(c.name)}</b> <span class="subtitle">${esc(c.score)}</span></div><span class="tag ${d != null && d <= 90 ? 'orange' : ''}">${ex ? (d < 0 ? '만료됨' : '만료까지 D-' + d) : '만료 없음/미입력'}</span></div>
      <div class="subtitle">취득 ${esc(c.date || '-')} · 유효 ${esc(c.valid)}년${ex ? ' · 만료일 ' + ex : ''}</div><div class="pp-card-mid"><button class="button" data-cert-del="${esc(c.id)}">삭제</button></div></article>`; }).join('') || '<div class="empty">등록한 어학·자격이 없습니다.</div>'}`;
  }

  // ---------- 대학원
  const GRAD_DOCS = ['지원서 작성', '연구계획서/자기소개서', '추천서', '성적·졸업(예정) 증명서', '어학 성적', '면접 준비'];
  function gradPanel() {
    const list = S().grad || [];
    return `<div class="note">대학원(계약학과 포함) 지원 일정과 서류를 취업 일정과 따로 관리합니다. 마감일은 캘린더 파일에도 포함됩니다.</div>
    <div class="panel"><h3>지원 추가</h3><div class="filters"><input class="select" id="meGradSchool" placeholder="학교" style="flex:1 1 160px"><input class="select" id="meGradProg" placeholder="학과/전공 (예: 시스템반도체공학)" style="flex:2 1 240px"><input class="select" type="date" id="meGradDl" title="접수 마감"><button class="button primary" id="meGradAdd">추가</button></div></div>
    ${list.map(g => { const d = dday(g.deadline); return `<article class="pp-card ${d != null && d >= 0 && d <= 7 ? 'pp-hot' : ''}"><div class="pp-card-top"><div><b>${esc(g.school)}</b> <span class="subtitle">${esc(g.program)}</span></div><span class="tag ${d != null && d >= 0 && d <= 7 ? 'orange' : ''}">${g.deadline ? (d < 0 ? '마감 지남' : d === 0 ? 'D-DAY' : 'D-' + d) : '마감일 없음'}</span></div>
      <div class="pp-card-mid"><label>접수 마감 <input class="select" type="date" value="${esc(g.deadline)}" data-grad-dl="${esc(g.id)}"></label><label>면접일 <input class="select" type="date" value="${esc(g.interview || '')}" data-grad-iv="${esc(g.id)}"></label></div>
      ${(g.docs || []).map((x, i) => `<label class="pp-check"><input type="checkbox" data-grad-doc="${esc(g.id)}:${i}" ${x.done ? 'checked' : ''}> ${esc(x.t)}</label>`).join('')}
      <textarea class="select pp-memo" rows="2" placeholder="메모 (지도교수 컨택, 연구실 관심 분야 등)" data-grad-note="${esc(g.id)}">${esc(g.note || '')}</textarea>
      <div class="pp-card-mid"><button class="button" data-grad-del="${esc(g.id)}">삭제</button></div></article>`; }).join('') || '<div class="empty">등록한 대학원 지원이 없습니다.</div>'}`;
  }

  // ---------- 캘린더(.ics)
  function icsEvents() {
    const s = S(), ev = [];
    (s.apps || []).forEach(a => {
      const nm = (a.company || '') + ' ' + (a.title || '');
      if (a.deadline) ev.push([a.deadline, '[지원 마감] ' + nm]);
      (a.stages || []).forEach(st => { if (st.date) ev.push([st.date, '[' + (st.name || '전형') + '] ' + nm]); });
    });
    (s.grad || []).forEach(g => { if (g.deadline) ev.push([g.deadline, '[대학원 마감] ' + g.school + ' ' + g.program]); if (g.interview) ev.push([g.interview, '[대학원 면접] ' + g.school]); });
    (s.certs || []).forEach(c => { const ex = certExpiry(c); if (ex) ev.push([ex, '[점수 만료] ' + c.name + ' ' + (c.score || '')]); });
    return ev.filter(e => /^\d{4}-\d{2}-\d{2}/.test(e[0]));
  }
  const icsEsc = t => String(t).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
  function fold(line) {
    const enc = new TextEncoder(); let out = '', cur = '', bytes = 0;
    for (const ch of line) { const b = enc.encode(ch).length; if (bytes + b > 70) { out += cur + '\r\n '; cur = ''; bytes = 1; } cur += ch; bytes += b; }
    return out + cur;
  }
  function buildICS() {
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//SEMI-HUB//KR', 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:SEMI-HUB 취업 일정'];
    icsEvents().forEach((e, i) => {
      const d = e[0].slice(0, 10), next = new Date(d + 'T00:00:00'); next.setDate(next.getDate() + 1);
      lines.push('BEGIN:VEVENT', 'UID:semihub-' + i + '-' + d.replace(/-/g, '') + '@local', 'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + d.replace(/-/g, ''), 'DTEND;VALUE=DATE:' + iso(next).replace(/-/g, ''), 'SUMMARY:' + icsEsc(e[1]),
        'BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + icsEsc(e[1]), 'TRIGGER:-P1D', 'END:VALARM', 'END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    return lines.map(fold).join('\r\n') + '\r\n';
  }
  function downloadICS() {
    const blob = new Blob([buildICS()], { type: 'text/calendar;charset=utf-8' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'semihub-schedule.ics';
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // ---------- 오늘 할 일
  function dueQuestions(n) {
    const D = window.SEMI_PREP_DATA; if (!D) return [];
    const s = S(), t = iso(today());
    const due = D.Q.filter(q => s.qsr && s.qsr[q.id] && s.qsr[q.id].due <= t);
    const fresh = D.Q.filter(q => !(s.qsr && s.qsr[q.id]) && s.qstat[q.id] !== 'know');
    return [...due, ...fresh].slice(0, n);
  }
  function nextRoad() {
    const p = prof(), s = S(), D = window.SEMI_PREP_DATA; if (!D) return null;
    const tracks = [...new Set(roles().filter(r => p.roles.includes(r.id)).map(r => r.track))];
    for (const t of tracks) { const i = (D.ROAD[t] || []).findIndex((_, k) => !s.road[t + ':' + k]); if (i >= 0) return { track: t, text: D.ROAD[t][i][1] }; }
    return null;
  }
  function todayPanel(live) {
    const av = (n, z) => window.SEMI_VIS ? window.SEMI_VIS.avatar(n, z) + ' ' : '';
    const p = prof(), s = S(), parts = [];
    const sec = (title, body, nav) => `<section class="td-card"><div class="td-head"><h3>${title}</h3>${nav ? `<button class="td-more" data-nav="${nav}">전체 →</button>` : ''}</div>${body}</section>`;
    const urgent = (s.apps || []).filter(a => !['최종합격', '불합격'].includes(a.status)).map(a => ({ a, d: dday(a.deadline) })).filter(x => x.d != null && x.d >= 0 && x.d <= 7).sort((x, y) => x.d - y.d);
    const stageSoon = []; (s.apps || []).forEach(a => (a.stages || []).forEach(st => { const d = dday(st.date); if (d != null && d >= 0 && d <= 7 && (!st.result || st.result === '대기')) stageSoon.push({ a, st, d }); }));
    const gradSoon = (s.grad || []).map(g => ({ g, d: dday(g.deadline) })).filter(x => x.d != null && x.d >= 0 && x.d <= 14);
    const items = [
      ...urgent.map(x => `<li>${av(x.a.company, 22)}<b>${esc(x.a.company)}</b> ${esc(x.a.title)} <span class="tag orange">${x.d === 0 ? 'D-DAY' : 'D-' + x.d}</span></li>`),
      ...stageSoon.map(x => `<li><b>${esc(x.a.company)}</b> ${esc(x.st.name || '전형')} <span class="tag orange">${x.d === 0 ? 'D-DAY' : 'D-' + x.d}</span></li>`),
      ...gradSoon.map(x => `<li><b>${esc(x.g.school)}</b> 대학원 마감 <span class="tag orange">D-${x.d}</span></li>`)];
    parts.push(sec('마감·일정 임박', items.length ? `<ul class="td-list">${items.join('')}</ul>` : '<p class="subtitle">7일 안에 다가오는 일정이 없습니다.</p>', 'tracker'));
    const jobs = (window.SEMI_JOBS_UI && window.SEMI_JOBS_UI.data ? window.SEMI_JOBS_UI.data(live) : []).filter(j => (!j.deadline || dday(j.deadline) == null || dday(j.deadline) >= 0) && matchJob(j, p) && !P.tracked(j.url)).sort((a, b) => (a.deadline || '9999').localeCompare(b.deadline || '9999')).slice(0, 4);
    parts.push(sec('내 관심 공고' + (hasFilter(p) ? '' : ' (프로필 미설정: 전체)'), jobs.length ? `<ul class="td-list">${jobs.map(j => `<li><b>${esc(j.company)}</b> <a href="${safe(j.url)}" target="_blank" rel="noopener noreferrer">${esc(String(j.title).slice(0, 40))}</a> <span class="tag">${esc(j.deadline ? '~' + j.deadline.slice(5) : (j.rolling ? '상시' : '마감 미표시'))}</span> <button class="button" data-track-add="1" data-co="${esc(j.company)}" data-ti="${esc(j.title)}" data-url="${esc(j.url)}" data-dl="${esc(j.deadline)}">추적</button></li>`).join('')}</ul>` : '<p class="subtitle">조건에 맞는 열린 공고가 아직 없습니다. 수집이 돌면 여기에 표시됩니다.</p>', 'recruit'));
    const news = (window.SEMI_TECH_UI && window.SEMI_TECH_UI.items ? window.SEMI_TECH_UI.items(live) : []).map(n => ({ n, sc: matchNews(n, p) })).filter(x => x.sc > 0).sort((a, b) => b.sc - a.sc || b.n.date.localeCompare(a.n.date)).slice(0, 3);
    parts.push(sec('내 관심 뉴스', news.length ? `<ul class="td-list">${news.map(x => `<li><span class="subtitle">${esc(x.n.date.slice(5))} ${esc(x.n.source)}</span><br><a href="${safe(x.n.url)}" target="_blank" rel="noopener noreferrer">${esc(String(x.n.title).slice(0, 60))}</a></li>`).join('')}</ul>` : '<p class="subtitle">' + (hasFilter(p) ? '관심 조건에 맞는 최근 뉴스가 없습니다.' : '프로필에서 관심 직무·기업을 고르면 맞춤 뉴스가 나옵니다.') + '</p>', 'news'));
    const qs = dueQuestions(3);
    parts.push(sec('오늘 복습할 질문', qs.length ? `<ul class="td-list">${qs.map(q => `<li>${esc(q.q)}</li>`).join('')}</ul><button class="button" data-nav="prep" data-me-prep="due">질문 풀러 가기</button>` : '<p class="subtitle">복습할 질문을 모두 마쳤습니다.</p>', null));
    const nr = nextRoad(), certsSoon = (S().certs || []).map(c => ({ c, ex: certExpiry(c) })).filter(x => x.ex && dday(x.ex) != null && dday(x.ex) <= 90 && dday(x.ex) >= 0);
    parts.push(sec('다음 준비', `${nr ? `<p>로드맵 다음 항목<br><b>${esc(nr.text)}</b></p>` : '<p class="subtitle">프로필에서 관심 직무를 고르면 다음 준비 항목이 나옵니다.</p>'}${certsSoon.length ? `<p class="subtitle">점수 만료 임박: ${certsSoon.map(x => esc(x.c.name) + ' D-' + dday(x.ex)).join(', ')}</p>` : ''}`, 'mine'));
    const intro = (!hasFilter(p) && !(s.apps || []).length) ? `<div class="note">처음이라면 <button class="button primary" data-nav="mine" data-me-tab="profile">내 프로필 설정하기</button> 로 관심 직무·기업을 고르면 아래 추천이 내 기준으로 바뀝니다.</div>` : '';
    const vis = window.SEMI_VIS ? window.SEMI_VIS.dashboard(window.SEMI_PREP.statuses) : '';
    return `${intro}${vis}<div class="td-grid">${parts.join('')}</div>`;
  }

  // ---------- AI 호출
  function post(path, body) {
    return fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(r => r.json().then(j => { if (!r.ok) throw new Error(j.error || ('오류 ' + r.status)); return j; }))
      .catch(e => { if (e instanceof TypeError) throw new Error('서버에 연결할 수 없습니다. start_semihub로 접속했는지 확인하세요.'); throw e; });
  }
  const profForAI = () => { const p = prof(); return { level: p.level, roles: roles().filter(r => p.roles.includes(r.id)).map(r => r.name), companies: cos().filter(c => p.companies.includes(c.id)).map(c => c.name), skills: String(p.skills).slice(0, 400), keywords: String(p.keywords).slice(0, 200), experiences: (S().exp || []).slice(0, 6).map(e => (e.title + ': ' + (e.action || '')).slice(0, 160)) }; };

  function insightBox(n) {
    const s = S(), v = (s.insight || {})[n.id], busy = ui.insightBusy[n.id], err = ui.insightErr[n.id];
    return `<div class="tech-dotted"><b>✦ 내 관점 분석</b><span>내 프로필 기준 · Gemini 추정(원문 확인 필요)</span></div>
      ${v ? `<div class="tech-learn-block me-insight">${esc(v)}</div>` : ''}${err ? `<div class="note notice-warning">${esc(err)}</div>` : ''}
      <button class="button" data-me-insight="${esc(n.id)}" ${busy ? 'disabled' : ''}>${busy ? '분석 중…' : v ? '다시 분석' : '내 관점으로 분석하기'}</button>`;
  }
  function mockBox(q) {
    if (!ui.mockOpen[q.id]) return `<button class="button" data-me-mock="${esc(q.id)}">AI 모의 면접</button>`;
    const m = (S().mock || {})[q.id] || {};
    return `<div class="pp-mock"><textarea class="select pp-memo" rows="4" id="meMockA-${esc(q.id)}" placeholder="면접에서 말하듯이 답해 보세요">${esc(m.a || '')}</textarea>
      <div class="pp-card-mid"><button class="button primary" data-me-mock-go="${esc(q.id)}" ${ui.mockBusy[q.id] ? 'disabled' : ''}>${ui.mockBusy[q.id] ? '평가 중…' : '평가받기'}</button><button class="button" data-me-mock="${esc(q.id)}">닫기</button></div>
      ${m.err ? `<div class="note notice-warning">${esc(m.err)}</div>` : ''}${m.fb ? `<div class="pp-answer">${esc(m.fb)}</div><div class="subtitle">AI 평가는 참고용이며 틀릴 수 있습니다.</div>` : ''}</div>`;
  }


  // ---------- 지원 전 체크리스트 (지원 현황 카드 안)
  const CHECK_ITEMS = ['공고 요건(학력·전공·우대사항) 확인', '직무에 맞춘 자소서 작성', '자소서 글자 수·오탈자 검토', '증빙 서류(성적·졸업·어학) 준비', '어학 성적 유효기간 확인', '프로젝트·포트폴리오 정리', '지원서 최종 제출'];
  function checkHints(a) {
    const out = [], s = S(), co = norm(a.company);
    const cv = (s.cover || []).filter(c => co && norm(c.company) && (norm(c.company).includes(co) || co.includes(norm(c.company))));
    out.push(cv.length ? `자소서 보관함에 ${esc(a.company)} 항목 ${cv.length}개 (작성된 것 ${cv.filter(c => (c.answer || '').trim()).length}개)` : '자소서 보관함에 이 기업 항목이 없습니다');
    const cs = (s.certs || []).map(c => ({ c, ex: certExpiry(c) })).filter(x => x.ex);
    if (a.deadline && cs.length) {
      const bad = cs.filter(x => x.ex < a.deadline).map(x => x.c.name);
      out.push(bad.length ? `⚠ 마감일 전에 만료되는 성적: ${esc(bad.join(', '))}` : '마감일까지 유효한 어학·자격이 있습니다');
    } else if (!cs.length) out.push('등록된 어학·자격이 없습니다 (내 프로필·스펙 → 어학·자격)');
    return out;
  }
  function checklist(a) {
    const ck = a.check || {}, done = CHECK_ITEMS.filter((_, i) => ck[i]).length;
    return `<details class="pp-stages"><summary>지원 전 체크 (${done}/${CHECK_ITEMS.length})</summary>
      ${CHECK_ITEMS.map((t, i) => `<label class="me-check"><input type="checkbox" data-chk="${esc(a.id)}:${i}" ${ck[i] ? 'checked' : ''}> ${esc(t)}</label>`).join('')}
      <div class="subtitle">${checkHints(a).map(h => '· ' + h).join('<br>')}</div></details>`;
  }

  // ---------- 시험 기록장 (인적성·코테)
  const TEST_KINDS = { 'GSAT(삼성)': ['언어논리', '수리논리', '추리', '시각적사고'], 'SKCT(SK)': ['언어이해', '자료해석', '창의수리', '언어추리', '수열추리'], '코딩테스트': ['구현', '그래프·탐색', 'DP', '자료구조', '수학', '문자열'], '기타': [] };
  const pct = (c, t) => t > 0 ? Math.round(c / t * 100) : null;
  function testStats(list) {
    const m = {};
    list.forEach(t => { const k = t.kind + ' · ' + (t.section || '전체'); const x = m[k] || (m[k] = { k, n: 0, c: 0, t: 0, min: 0 }); x.n++; x.c += +t.correct || 0; x.t += +t.total || 0; x.min += +t.minutes || 0; });
    return Object.values(m).map(x => Object.assign(x, { acc: pct(x.c, x.t), per: x.t ? Math.round(x.min * 60 / x.t) : null })).sort((a, b) => (a.acc == null ? 999 : a.acc) - (b.acc == null ? 999 : b.acc));
  }
  function testsPanel() {
    const list = (S().tests || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date))), st = testStats(list);
    const kind = ui.testKind || '코딩테스트';
    return `<div class="note">GSAT·SKCT·코딩테스트 결과를 영역별로 기록하면 <b>약한 영역</b>이 정답률 순으로 나옵니다. 영역 이름은 직접 입력해도 됩니다.</div>
    <div class="panel"><h3>시험 결과 추가</h3><div class="filters">
      <select class="select" id="meTKind">${Object.keys(TEST_KINDS).map(k => `<option ${k === kind ? 'selected' : ''}>${k}</option>`).join('')}</select>
      <input class="select" id="meTCo" placeholder="회사(선택)" style="flex:1 1 110px">
      <input class="select" id="meTDate" type="date" value="${iso(today())}">
      <input class="select" id="meTSec" list="meTSecList" placeholder="영역" style="flex:1 1 110px"><datalist id="meTSecList">${(TEST_KINDS[kind] || []).map(x => `<option value="${esc(x)}">`).join('')}</datalist>
      <input class="select" id="meTC" type="number" min="0" placeholder="맞은 수" style="width:90px"><input class="select" id="meTT" type="number" min="1" placeholder="전체 문항" style="width:100px"><input class="select" id="meTM" type="number" min="0" placeholder="걸린 분" style="width:90px">
      <input class="select" id="meTNote" placeholder="틀린 이유·메모" style="flex:2 1 200px"><button class="button primary" id="meTAdd">추가</button></div></div>
    <div class="panel"><h3>영역별 정답률 (낮은 순)</h3>${st.length ? `<table class="pp-table"><thead><tr><th>영역</th><th>횟수</th><th>정답률</th><th>문항당 시간</th></tr></thead><tbody>${st.map((x, i) => `<tr class="${i < 2 && x.acc != null && x.acc < 70 ? 'me-weak' : ''}"><td>${esc(x.k)}</td><td>${x.n}</td><td>${x.acc == null ? '-' : x.acc + '%'}</td><td>${x.per == null ? '-' : x.per + '초'}</td></tr>`).join('')}</tbody></table><div class="subtitle">정답률 70% 미만인 가장 약한 영역은 강조 표시됩니다.</div>` : '<div class="empty">아직 기록이 없습니다.</div>'}</div>
    <div class="panel"><h3>기록 (${list.length})</h3>${list.map(t => `<article class="pp-card"><div class="pp-card-top"><div><b>${esc(t.kind)}</b> <span class="subtitle">${esc(t.company || '')} ${esc(t.section || '')} · ${esc(t.date)}</span></div><span class="tag">${pct(+t.correct, +t.total) == null ? '-' : pct(+t.correct, +t.total) + '%'} (${esc(t.correct)}/${esc(t.total)})${t.minutes ? ' · ' + esc(t.minutes) + '분' : ''}</span></div>${t.note ? `<div class="subtitle">${esc(t.note)}</div>` : ''}<div class="pp-card-mid"><button class="button" data-test-del="${esc(t.id)}">삭제</button></div></article>`).join('') || '<div class="empty">기록이 없습니다.</div>'}</div>`;
  }

  // ---------- 백업·복구
  function backupTab() {
    const b = ui.backups, fmt = n => `${n.slice(0, 4)}-${n.slice(4, 6)}-${n.slice(6)}`;
    const srv = location.protocol === 'file:' ? '<div class="note notice-warning">서버 없이 열어서 PC 자동 백업을 볼 수 없습니다. start_semihub로 접속하세요.</div>'
      : b == null ? '<div class="subtitle">불러오는 중…</div>'
      : b.error ? `<div class="note notice-warning">${esc(b.error)}</div>`
      : `<table class="pp-table"><thead><tr><th>날짜</th><th>지원</th><th>자소서</th><th>경험</th><th></th></tr></thead><tbody>${b.list.map(x => `<tr><td>${fmt(x.name)}</td><td>${x.apps}</td><td>${x.cover}</td><td>${x.exp}</td><td><button class="button" data-bk-restore="${x.name}">이 날짜로 복원</button></td></tr>`).join('') || '<tr><td colspan="5">아직 자동 백업이 없습니다 (하루 한 번, 수정이 있는 날 생성)</td></tr>'}</tbody></table>`;
    return `<div class="note">복원하기 직전 상태는 브라우저에 사본으로 남깁니다. 날짜별 백업은 그날 <b>첫 수정 직전</b> 상태입니다.</div>
      <div class="panel"><h3>PC 자동 백업 (최근 30일)</h3><div class="subtitle" id="ppSync"></div>${srv}<div class="subtitle" id="meBkMsg">${esc(ui.bkMsg || '')}</div></div>
      <div class="panel"><h3>파일로 내보내기 / 가져오기</h3><div class="filters"><button class="button" id="ppExport">백업 파일 내려받기</button><label class="button">백업 파일 불러오기<input type="file" id="ppImport" accept="application/json,.json" hidden></label></div><div class="subtitle" id="ppBackupMsg"></div>
      <div class="subtitle">PC를 바꾸거나 다른 기기로 옮길 때 사용하세요.</div></div>`;
  }
  function loadBackups(render) {
    if (location.protocol === 'file:' || ui.backups !== undefined) return;
    ui.backups = null;
    fetch('/api/store/backups').then(r => r.json()).then(j => { ui.backups = { list: j.backups || [] }; }).catch(() => { ui.backups = { error: '서버에 연결할 수 없습니다.' }; }).then(render);
  }

  // ---------- 패널 / 바인딩
  const panels = { profile: profilePanel, exp: expPanel, certs: certPanel, grad: gradPanel, tests: testsPanel, backup: backupTab };
  function bind(render, tab) {
    rerender = render;
    if (tab !== 'backup') ui.bkSeen = false;
    const s = S(), on = (sel, fn) => document.querySelectorAll(sel).forEach(fn);
    on('[data-me-tab]', el => el.addEventListener('click', () => { P.ui.mineTab = el.dataset.meTab; }));
    on('[data-me-prep]', el => el.addEventListener('click', () => { P.ui.prepTab = 'q'; P.ui.qmode = el.dataset.mePrep; }));
    if (tab === 'profile') {
      on('[data-me-level]', el => el.onclick = () => { setProf({ level: el.dataset.meLevel }); render(); });
      on('[data-me-role]', el => el.onclick = () => { const p = prof(), id = el.dataset.meRole; setProf({ roles: p.roles.includes(id) ? p.roles.filter(x => x !== id) : [...p.roles, id] }); render(); });
      on('[data-me-co]', el => el.onclick = () => { const p = prof(), id = el.dataset.meCo; setProf({ companies: p.companies.includes(id) ? p.companies.filter(x => x !== id) : [...p.companies, id] }); render(); });
      const cs = $('meCoSearch'); if (cs) cs.onchange = () => { const c = cos().find(x => x.name === cs.value.trim()); if (c && !prof().companies.includes(c.id)) { setProf({ companies: [...prof().companies, c.id] }); render(); } };
      const sk = $('meSkills'); if (sk) sk.oninput = () => setProf({ skills: sk.value });
      const kw = $('meKeywords'); if (kw) kw.oninput = () => setProf({ keywords: kw.value });
      const ao = $('meAiOn'); if (ao) ao.onchange = () => setProf({ aiDigest: ao.checked });
      const ac = $('meAiConsent'); if (ac) ac.onchange = () => setProf({ aiConsent: ac.checked });
      const ap = $('meAiPreview'); if (ap) ap.onclick = () => { const o = $('meAiOut'); const sh = t => { ui.aiMsg = t; if (o) o.textContent = t; }; sh('AI가 요약하는 중… (최대 20초)'); post('/api/notify/ai-digest', {}).then(j => sh(j.text || '(요약할 최근 관심 뉴스가 없습니다. 관심 직무·기업·키워드를 고르고 뉴스를 수집하세요)')).catch(e => sh('오류: ' + e.message)); };
      const out = $('meNotifyOut');
      const show = t => { ui.notifyMsg = t; if (out) out.textContent = t; };
      const pv = $('meNotifyPreview'); if (pv) pv.onclick = () => { show('확인 중…'); post('/api/notify/preview', {}).then(j => show(j.text || '(보낼 알림이 없습니다)')).catch(e => show(e.message)); };
      const ts = $('meNotifyTest'); if (ts) ts.onclick = () => { show('전송 중…'); post('/api/notify/test', {}).then(() => show('테스트 메시지를 보냈습니다. 카톡 "나와의 채팅"을 확인하세요.')).catch(e => show(e.message)); };
    }
    if (tab === 'exp') {
      const add = $('meExpAdd'); if (add) add.onclick = () => { const t = $('meExpTitle').value.trim(); if (!t) return; (s.exp = s.exp || []).unshift({ id: uid(), title: t, tags: $('meExpTags').value.trim() }); save(); render(); };
      on('[data-exp]', el => el.oninput = () => { const [id, k] = el.dataset.exp.split(':'), e = (s.exp || []).find(x => x.id === id); if (e) { e[k] = el.value; save(); } });
      on('[data-exp-del]', el => el.onclick = () => { if (confirm('이 경험을 삭제할까요?')) { s.exp = s.exp.filter(x => x.id !== el.dataset.expDel); save(); render(); } });
    }
    if (tab === 'certs') {
      const add = $('meCertAdd'); if (add) add.onclick = () => { const n = $('meCertName').value.trim(); if (!n) return; (s.certs = s.certs || []).push({ id: uid(), name: n, score: $('meCertScore').value.trim(), date: $('meCertDate').value, valid: $('meCertValid').value || '0' }); save(); render(); };
      on('[data-cert-del]', el => el.onclick = () => { s.certs = s.certs.filter(x => x.id !== el.dataset.certDel); save(); render(); });
    }
    if (tab === 'grad') {
      const add = $('meGradAdd'); if (add) add.onclick = () => { const sc = $('meGradSchool').value.trim(); if (!sc) return; (s.grad = s.grad || []).push({ id: uid(), school: sc, program: $('meGradProg').value.trim(), deadline: $('meGradDl').value, interview: '', docs: GRAD_DOCS.map(t => ({ t, done: false })), note: '' }); save(); render(); };
      const g = id => (s.grad || []).find(x => x.id === id);
      on('[data-grad-dl]', el => el.onchange = () => { const x = g(el.dataset.gradDl); if (x) { x.deadline = el.value; save(); render(); } });
      on('[data-grad-iv]', el => el.onchange = () => { const x = g(el.dataset.gradIv); if (x) { x.interview = el.value; save(); } });
      on('[data-grad-doc]', el => el.onchange = () => { const [id, i] = el.dataset.gradDoc.split(':'), x = g(id); if (x) { x.docs[+i].done = el.checked; save(); } });
      on('[data-grad-note]', el => el.oninput = () => { const x = g(el.dataset.gradNote); if (x) { x.note = el.value; save(); } });
      on('[data-grad-del]', el => el.onclick = () => { if (confirm('이 대학원 지원을 삭제할까요?')) { s.grad = s.grad.filter(x => x.id !== el.dataset.gradDel); save(); render(); } });
    }
    if (tab === 'tests') {
      const k = $('meTKind'); if (k) k.onchange = () => { ui.testKind = k.value; render(); };
      const add = $('meTAdd'); if (add) add.onclick = () => {
        const t = +$('meTT').value; if (!(t > 0)) return;
        (s.tests = s.tests || []).unshift({ id: uid(), kind: $('meTKind').value, company: $('meTCo').value.trim(), date: $('meTDate').value, section: $('meTSec').value.trim(), correct: Math.min(+$('meTC').value || 0, t), total: t, minutes: +$('meTM').value || 0, note: $('meTNote').value.trim() });
        save(); render();
      };
      on('[data-test-del]', el => el.onclick = () => { s.tests = (s.tests || []).filter(x => x.id !== el.dataset.testDel); save(); render(); });
    }
    if (tab === 'backup') {
      if (!ui.bkSeen) { ui.backups = undefined; ui.bkSeen = true; } // 탭을 처음 열 때만 목록을 새로 받음
      loadBackups(render);
      on('[data-bk-restore]', el => el.onclick = () => {
        const name = el.dataset.bkRestore;
        fetch('/api/store/backup?name=' + encodeURIComponent(name)).then(r => r.json().then(j => { if (!r.ok) throw new Error(j.error || '복원 실패'); return j; })).then(j => {
          if (!confirm(name + ' 백업으로 되돌립니다. 지금 데이터는 브라우저에 사본으로 남깁니다. 계속할까요?')) return;
          try { localStorage.setItem('semihub.prep.v1.before-restore', JSON.stringify(S())); } catch (e) { /* ignore */ }
          P.api.adopt(j.data); save(); ui.bkMsg = name + ' 백업으로 복원했습니다.'; render();
        }).catch(e => { ui.bkMsg = e.message; render(); });
      });
    }
    on('[data-chk]', el => el.onchange = () => { const [id, i] = el.dataset.chk.split(':'), a = s.apps.find(x => x.id === id); if (a) { (a.check = a.check || {})[i] = el.checked; save(); const sm = el.closest('details').querySelector('summary'); sm.textContent = '지원 전 체크 (' + CHECK_ITEMS.filter((_, k) => a.check[k]).length + '/' + CHECK_ITEMS.length + ')'; } });
    const ic = $('meIcs'); if (ic) ic.onclick = downloadICS;
    on('[data-me-insight]', el => el.onclick = () => {
      const id = el.dataset.meInsight, n = (window.SEMI_TECH_UI.items(window.__semiLive || {}) || []).find(x => x.id === id); if (!n) return;
      ui.insightBusy[id] = true; ui.insightErr[id] = ''; render();
      post('/api/ai/personal', { title: n.title, summary: n.summary, source: n.source, date: n.date, category: n.category, profile: profForAI() })
        .then(j => { (s.insight = s.insight || {})[id] = j.analysis; save(); }).catch(e => { ui.insightErr[id] = e.message; })
        .then(() => { ui.insightBusy[id] = false; render(); });
    });
    on('[data-me-mock]', el => el.onclick = () => { ui.mockOpen[el.dataset.meMock] = !ui.mockOpen[el.dataset.meMock]; render(); });
    on('[data-me-mock-go]', el => el.onclick = () => {
      const id = el.dataset.meMockGo, q = (window.SEMI_PREP_DATA.Q || []).find(x => x.id === id), a = $('meMockA-' + id); if (!q || !a || !a.value.trim()) return;
      const m = ((s.mock = s.mock || {})[id] = { a: a.value, fb: '', err: '' }); save(); ui.mockBusy[id] = true; render();
      post('/api/ai/mock', { question: q.q, answer: a.value, reference: q.a, profile: profForAI() })
        .then(j => { m.fb = j.feedback; }).catch(e => { m.err = e.message; })
        .then(() => { ui.mockBusy[id] = false; save(); render(); });
    });
  }

  window.SEMI_ME = { panel: t => (panels[t] ? panels[t]() : ''), has: t => !!panels[t], bind, today: todayPanel, matchJob, matchNews, hasFilter, prof, insightBox, mockBox, downloadICS, buildICS, certExpiry, icsEvents, checklist };
})();
