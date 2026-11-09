// 화면 꾸밈용: 기업 이니셜 아바타, 메뉴 아이콘, 현황 차트 (외부 이미지·로고를 쓰지 않습니다)
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function avatar(name, size) {
    const n = String(name || '?').trim() || '?', ch = /[A-Za-z]/.test(n[0]) ? n.slice(0, 2).toUpperCase() : n[0];
    let h = 0; for (const c of n) h = (h * 31 + c.charCodeAt(0)) % 360;
    const sz = size || 34;
    return `<span class="avatar" style="width:${sz}px;height:${sz}px;font-size:${Math.round(sz * .42)}px;background:hsl(${h} 70% 94%);color:hsl(${h} 55% 32%)">${esc(ch)}</span>`;
  }
  const P = {
    home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
    tracker: 'M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z',
    prep: 'M4 20l1-4L16 5l3 3L8 19zM14 7l3 3',
    careerai: 'M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z',
    mine: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0',
    recruit: 'M4 8h16v11H4zM9 8V5h6v3M4 13h16',
    news: 'M5 4h11v16H5zM16 8h3v10a2 2 0 0 1-2 2M8 8h5M8 12h5M8 16h3',
    companies: 'M4 20V9l6-3v14M10 20V4l10 4v12M3 20h18M13 11h4M13 15h4',
    roles: 'M12 3l2.5 6 6.5.5-5 4.3 1.6 6.4L12 16.7 6.4 20.2 8 13.8 3 9.5 9.5 9z',
    salaries: 'M4 6h16v12H4zM12 9v6M9.5 10.5c0-1 5 -1 5 0s-5 2-5 3 5 1 5 0',
    products: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2',
    sources: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1'
  };
  const icon = (k, sz) => P[k] ? `<svg class="ico" width="${sz || 18}" height="${sz || 18}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${P[k]}"/></svg>` : '';

  function card(title, body, sub) { return `<section class="td-card vis-card"><div class="td-head"><h3>${title}</h3>${sub ? `<span class="subtitle">${sub}</span>` : ''}</div>${body}</section>`; }

  function funnel(apps, statuses) {
    const counts = statuses.map(s => apps.filter(a => a.status === s).length), max = Math.max(1, ...counts);
    if (!apps.length) return card('지원 단계', '<p class="subtitle">지원 현황에 공고를 추가하면 단계별 막대가 나옵니다.</p>');
    return card('지원 단계', `<div class="vis-bars">${statuses.map((s, i) => `<div class="vis-row"><span>${esc(s)}</span><div class="vis-track"><i style="width:${Math.round(counts[i] / max * 100)}%"></i></div><b>${counts[i]}</b></div>`).join('')}</div>`, `총 ${apps.length}건`);
  }

  function trend(tests) {
    const pts = (tests || []).filter(t => +t.total > 0 && t.date).map(t => ({ d: t.date, v: Math.round(+t.correct / +t.total * 100), k: t.kind })).sort((a, b) => a.d.localeCompare(b.d));
    if (pts.length < 2) return card('시험 정답률', '<p class="subtitle">시험 기록을 2건 이상 넣으면 추이 그래프가 나옵니다. (내 프로필·스펙 → 시험 기록)</p>');
    const W = 280, H = 110, x = i => 14 + i * (W - 28) / (pts.length - 1), y = v => 10 + (100 - v) / 100 * (H - 30);
    const line = pts.map((p, i) => `${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join(' ');
    const last = pts[pts.length - 1];
    return card('시험 정답률', `<svg viewBox="0 0 ${W} ${H}" class="vis-line" role="img" aria-label="시험 정답률 추이"><line x1="14" x2="${W - 14}" y1="${y(50)}" y2="${y(50)}" class="vis-grid"/><polyline points="${line}" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>${pts.map((p, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="3.4" fill="#fff" stroke="var(--accent)" stroke-width="2"><title>${esc(p.d)} ${esc(p.k)} ${p.v}%</title></circle>`).join('')}<text x="${W - 14}" y="${H - 4}" text-anchor="end" class="vis-txt">${esc(last.d.slice(5))} 최근 ${last.v}%</text><text x="14" y="${H - 4}" class="vis-txt">${esc(pts[0].d.slice(5))}</text></svg>`, `${pts.length}회`);
  }

  function calendar(events) {
    const n = new Date(), y = n.getFullYear(), m = n.getMonth(), first = new Date(y, m, 1).getDay(), days = new Date(y, m + 1, 0).getDate();
    const ym = y + '-' + String(m + 1).padStart(2, '0'), map = {};
    events.forEach(e => { if (e.date && e.date.startsWith(ym)) (map[+e.date.slice(8, 10)] = map[+e.date.slice(8, 10)] || []).push(e.label); });
    let cells = ['일', '월', '화', '수', '목', '금', '토'].map(d => `<span class="vis-dow">${d}</span>`).join('');
    for (let i = 0; i < first; i++) cells += '<span></span>';
    for (let d = 1; d <= days; d++) cells += `<span class="vis-day ${d === n.getDate() ? 'today' : ''} ${map[d] ? 'has' : ''}" ${map[d] ? `title="${esc(map[d].join(' / '))}"` : ''}>${d}</span>`;
    const cnt = Object.values(map).reduce((a, b) => a + b.length, 0);
    return card(`${m + 1}월 일정`, `<div class="vis-cal">${cells}</div>`, cnt ? `${cnt}건` : '일정 없음');
  }

  function dashboard(statuses) {
    const A = window.SEMI_PREP && window.SEMI_PREP.api; if (!A) return '';
    const s = A.S(), ev = [];
    (s.apps || []).forEach(a => { if (a.deadline) ev.push({ date: a.deadline, label: (a.company || '') + ' 마감' }); (a.stages || []).forEach(t => t.date && ev.push({ date: t.date, label: (a.company || '') + ' ' + (t.name || '전형') })); });
    (s.grad || []).forEach(g => g.deadline && ev.push({ date: g.deadline, label: (g.school || '') + ' 대학원 마감' }));
    return `<div class="td-grid vis-grid3">${funnel(s.apps || [], statuses)}${trend(s.tests)}${calendar(ev)}</div>`;
  }
  window.SEMI_VIS = { avatar, icon, dashboard, esc };
})();
