/* SEMI-HUB AI Career Path · 뉴스 → 직무 → 실제 채용공고 → 역량 격차.
   LLM은 서버에서만 호출하며, 근거 자료·사용자 동의 없이는 역량을 확정하지 않음. */
(() => {
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=v=>/^https:\/\/[a-z\d.-]+(?:[\/?#:]|$)/i.test(String(v||''))?esc(v):'#';
const el=id=>document.getElementById(id);
const state={newsUrl:'',search:'',role:'',company:'',jobUrl:'',showPast:true,jobText:'',experience:'',consent:false,keyOpen:false,busy:false,requestId:0,analysis:null,error:'',sources:null};
const roles=()=>window.SEMI_ROLES?.roles||[];
const companies=()=>window.SEMI_DB?.companies||[];
const profile=()=>window.SEMI_ME?.prof?.()||{level:'신입',roles:[],companies:[],skills:'',keywords:''};
const store=()=>window.SEMI_PREP?.api?.S?.()||{};
const dateKST=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const norm=v=>String(v||'').toLowerCase().replace(/\s+/g,' ').trim();
const excerpt=(s,max=135)=>String(s||'').length>max?String(s).slice(0,max)+'…':String(s||'');
const themePatterns={
 hbm:/\bhbm\b|hbm\d|dram|d램|디램|메모리|memory|고대역폭/i,
 package:/패키징|패키지|package|packaging|bonding|본딩|tsv|인터포저|interposer|적층|2\.5d|3d.ic|chiplet|칩렛|pkg|warpage/i,
 process:/공정|양산|process|manufactur|생산기술|yield|수율|fab|파운드리|foundry|production/i,
 etch:/식각|etch|plasma|플라즈마|chamber|챔버/i,
 deposition:/증착|deposition|ald|cvd|pvd|박막|thin.film/i,
 litho:/노광|lithograph|euv|duv|photo|포토|리소그래피/i,
 equipment:/설비|반도체 장비|equipment|fse|field.service|customer.support|maintenance|유지보수/i,
 test:/검사|계측|검증|테스트|inspection|metrology|test|quality|품질|reliab|신뢰성/i,
 design:/설계|design|asic|soc|vlsi|rtl|eda|cadence/i,
 power:/전력반도체|전력소자|sic|gan|power.semiconductor/i,
 ai:/ai반도체|ai.chip|gpu|npu|인공지능 반도체/i
};
const themes=t=>Object.entries(themePatterns).filter(([,r])=>r.test(String(t||''))).map(([k])=>k);
const common=(a,b)=>a.filter(v=>b.includes(v));
function newsItems(live){
 const items=window.SEMI_TECH_UI?.items?.(live)||[];
 const p=profile(),rNames=roles().filter(r=>(p.roles||[]).includes(r.id)).map(r=>r.name);
 const cNames=companies().filter(c=>(p.companies||[]).includes(c.id)).map(c=>c.name);
 const interests=[...rNames,...cNames,...String(p.keywords||'').split(/[,;\n]+/)].map(norm).filter(x=>x.length>=2);
 return items.filter(n=>/^https:\/\//.test(n.url||'')).map(n=>({n,points:interests.reduce((s,k)=>s+(norm([n.title,n.summary,n.category].join(' ')).includes(k)?2:0),0)}))
 .sort((a,b)=>b.points-a.points || String(b.n.date||'').localeCompare(String(a.n.date||''))).map(x=>x.n);
}
function visibleNews(live){
 const all=newsItems(live),q=norm(state.search);
 const list=q?all.filter(n=>norm([n.title,n.summary,n.company,n.category,n.source].join(' ')).includes(q)):all;
 return list.slice(0,220);
}
function currentNews(live){const list=visibleNews(live);return list.find(n=>n.url===state.newsUrl)||list[0]||null}
function relatedRoles(n){
 const nTags=themes([n?.title,n?.summary,n?.category].join(' '));
 const saved=profile().roles||[];
 return roles().map(r=>{const words=themes([r.name,r.tags,r.work,r.description].join(' '));let score=common(words,nTags).length*4;
 if(saved.includes(r.id))score+=2;
 const t=norm(n?.title);for(const k of [r.name,String(r.name).split(' ')[0]])if(k.length>=3 && t.includes(norm(k)))score+=3;
 return {r,score}}).sort((a,b)=>b.score-a.score||a.r.name.localeCompare(b.r.name,'ko'));
}
function roleFor(n){return roles().find(r=>r.id===state.role)||relatedRoles(n)[0]?.r||null}
function namedCompanies(text){
 const t=norm(text);return companies().filter(c=>{
  const name=norm(c.name);return name.length>=3 && (t.includes(name) || (name.includes('sk하이닉스')&&t.includes('sk hynix')) || (name.includes('삼성전자')&&t.includes('samsung electronics')));
 }).map(c=>c.name);
}
function scoredJobs(live,n,r){
 const all=window.SEMI_JOBS_UI?.data?.(live)||[];
 const nText=[n?.title,n?.summary,n?.category].join(' '),nTags=themes(nText);
 const rText=[r?.name,r?.tags,r?.work,r?.prep].join(' '),rTags=themes(rText);
 const newsCompanies=namedCompanies(nText);const selectedCompany=companies().find(c=>c.id===state.company)?.name;
 const today=dateKST(),p=profile();
 return all.filter(j=>/^https:\/\//.test(j.url||'')).filter(j=>state.showPast || !j.deadline || j.deadline>=today)
 .map(j=>{
  const text=[j.title,j.category,j.note].join(' '),jobTags=themes(text);
  const shared=common(nTags,jobTags),rShared=common(rTags,jobTags);
  const companyHit=newsCompanies.some(c=>norm(j.company).includes(norm(c))||norm(c).includes(norm(j.company)));
  const chosenCompany=selectedCompany && norm(j.company).includes(norm(selectedCompany));
  let score=shared.length*7+rShared.length*4+(companyHit?6:0)+(chosenCompany?2:0);
  if(state.role && rShared.length)score+=2;
  if((p.level==='신입')&&/경력/.test(j.level||'')&&!/신입/.test(j.level||''))score-=2;
  const why=[companyHit?'뉴스에 언급된 기업':null,shared.length?'공통 기술: '+shared.slice(0,2).map(x=>themeLabels[x]).join('·'):null,rShared.length?'선택 직무와 분야 연관':null].filter(Boolean);
  const relevant=shared.length>0 || (companyHit && rShared.length>0) || (rShared.length>0 && nTags.length===0 && companyHit);
  return {j,score,why:why.join(' · '),relevant,deadlinePassed:!!j.deadline&&j.deadline<today};
 }).filter(x=>x.relevant && x.score>=5)
 .sort((a,b)=>b.score-a.score||Number(a.deadlinePassed)-Number(b.deadlinePassed)||String(b.j.date||'').localeCompare(String(a.j.date||'')))
 .slice(0,5);
}
const themeLabels={hbm:'HBM·메모리',package:'패키징',process:'공정·양산',etch:'식각',deposition:'증착',litho:'노광',equipment:'장비',test:'검사·품질',design:'설계',power:'전력반도체',ai:'AI 반도체'};
function pickedJob(jobs){return jobs.find(x=>x.j.url===state.jobUrl)||jobs[0]||null}
const cleanNews=n=>({title:n.title,company:n.company,date:n.date,source:n.source,url:n.url,summary:n.summary,category:n.category});
const cleanJob=x=>({title:x.j.title,company:x.j.company,date:x.j.date,source:x.j.source,url:x.j.url,category:x.j.category,level:x.j.level,deadline:x.j.deadline,note:x.j.note,match_reason:x.why,status:x.deadlinePassed?'마감일 경과':x.j.deadline?'마감일 미경과(접수 중 보장 아님)':'마감일 미확인'});
function evidence(live){
 const n=currentNews(live),r=n?roleFor(n):null,jobOptions=n?scoredJobs(live,n,r):[],chosen=pickedJob(jobOptions);
 const jobs=chosen?[chosen,...jobOptions.filter(x=>x!==chosen)].slice(0,4):[];
 return {n,r,jobOptions,chosen,news:n?[cleanNews(n)]:[],jobs:jobs.map(cleanJob),role:r?{name:r.name,description:r.description,work:r.work,prep:r.prep,source:r.source,status:r.status}:null};
}
function userProfile(){
 const p=state.consent?profile():{};
 const rolesSaved=roles().filter(x=>(p.roles||[]).includes(x.id)).map(x=>x.name);
 const names=companies().filter(x=>(p.companies||[]).includes(x.id)).map(x=>x.name);
 const exp=state.consent?(store().exp||[]).slice(0,6).map(x=>[x.title,x.action,x.result].filter(Boolean).join(' / ').slice(0,280)):[];
 if(state.experience.trim())exp.push('이번 분석에 직접 입력한 경험: '+state.experience.trim().slice(0,1600));
 return {level:p.level||'',roles:rolesSaved,companies:names,skills:state.consent?String(p.skills||'').slice(0,600):'',keywords:state.consent?String(p.keywords||'').slice(0,280):'',experiences:exp};
}
function profileStatus(){const p=profile(),exp=(store().exp||[]).length;
 return [p.skills?'보유 역량 등록됨':'보유 역량 미등록',exp?'저장 경험 '+exp+'건':'저장 경험 없음',state.consent?'분석에 제공 동의':'프로필 분석 동의 필요'].join(' · ');
}
function sourceItem(src,id){return `<div class="ca-source-item"><span class="ca-source-id">${id}</span><div class="ca-source-content"><a href="${safe(src.url)}" target="_blank" rel="noopener noreferrer">${esc(src.title)}</a><span>${esc(src.company||src.source||'출처 미확인')} · ${esc(src.date||'날짜 미확인')}${src.deadline?' · 마감 '+esc(src.deadline):''}</span></div></div>`;}
function sourceBlock(src){const news=(src?.news||[]).map((x,i)=>sourceItem(x,`N${i+1}`)).join('');const jobs=(src?.jobs||[]).map((x,i)=>sourceItem(x,`J${i+1}`)).join('');
 return `<div class="ca-sources">${news}${jobs}${!(news||jobs)?'<p class="ca-hint">연결할 자료가 없습니다.</p>':''}</div>`;
}
function invalidate(){state.analysis=null;state.error='';state.sources=null;state.requestId++;state.busy=false;}
function newsPicker(live,e){const news=visibleNews(live),n=e.n;
 return `<section class="panel ca-flow-panel"><div class="ca-section-title"><span class="ca-step">01</span><div><h3>관심 있는 뉴스를 선택하세요</h3><p>선택한 기사 하나가 전체 분석의 출발점이 됩니다.</p></div></div>
 <label class="ca-label" for="caNewsSearch">뉴스 검색</label><input id="caNewsSearch" class="input ca-search" type="search" placeholder="HBM, 패키징, 기업명, 공정 기술 등" value="${esc(state.search)}" />
 <label class="ca-label" for="caNews">분석할 기사 · 검색 결과 ${news.length}건${news.length===220?' (최대 220건 표시)':''}</label>
 <select id="caNews" class="select ca-select" ${news.length?'':'disabled'}>${news.map(x=>`<option value="${esc(x.url)}" ${x.url===n?.url?'selected':''}>${esc((x.date||'날짜 미확인')+' · '+excerpt(x.title,110))}</option>`).join('')}</select>
 ${n?`<div class="ca-selected-news"><span class="ca-overline">SELECTED ARTICLE</span><h3>${esc(n.title)}</h3><p>${esc(excerpt(n.summary||'수집된 기사 요약이 없어 제목만 기반으로 분석합니다.',340))}</p><div class="ca-article-meta"><span>${esc(n.source||'언론사 미확인')} · ${esc(n.date||'날짜 미확인')}</span><a href="${safe(n.url)}" target="_blank" rel="noopener noreferrer">기사 원문 보기 ↗</a></div></div>`:'<div class="ca-empty-inline">검색 결과가 없습니다. 검색어를 변경해 주세요.</div>'}
 </section>`;
}
function rolePicker(e){const n=e.n;if(!n)return '';
 const candidates=relatedRoles(n).slice(0,4);const r=e.r;
 return `<section class="panel ca-flow-panel"><div class="ca-section-title"><span class="ca-step">02</span><div><h3>연결되는 반도체 직무</h3><p>기사의 기술 키워드와 기존 직무 설명을 연결한 <b>후보</b>이며, LLM이 직무 영향을 해석합니다.</p></div></div>
 <div class="ca-role-pills">${candidates.map(x=>`<button type="button" data-ca-role="${esc(x.r.id)}" class="ca-role-choice ${r?.id===x.r.id?'active':''}">${esc(x.r.name)}</button>`).join('')}</div>
 <label class="ca-label" for="caRole">다른 직무를 선택하려면</label><select id="caRole" class="select ca-select"><option value="">뉴스와 연결된 추천 직무</option>${roles().map(x=>`<option value="${esc(x.id)}" ${state.role===x.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select>
 ${r?`<div class="ca-role-context"><b>${esc(r.name)}</b><p>${esc(r.work||r.description||'')} <span class="ca-soft-note">직무 설명 자료이며 채용 요건은 아닙니다.</span></p></div>`:''}
 </section>`;
}
function jobPicker(e){if(!e.n)return '';
 const list=e.jobOptions,selected=e.chosen;
 return `<section class="panel ca-flow-panel"><div class="ca-section-title"><span class="ca-step">03</span><div><h3>실제 채용공고 연결</h3><p>기존에 수집된 채용공고를 뉴스·직무 키워드로 연결합니다. <b>뉴스 때문에 채용이 늘었다는 뜻은 아닙니다.</b></p></div></div>
 <label class="ca-check ca-past"><input id="caShowPast" type="checkbox" ${state.showPast?'checked':''}> 마감된 공고도 참고 사례로 보기</label>
 ${list.length?`<div class="ca-job-choices">${list.map((x,i)=>`<label class="ca-job-option ${selected?.j.url===x.j.url?'selected':''}"><input type="radio" name="caJob" data-ca-job="${esc(x.j.url)}" ${selected?.j.url===x.j.url?'checked':''}>
 <span class="ca-job-content"><span class="ca-job-head"><b>${esc(x.j.company||'기업 미확인')}</b><span class="ca-job-tag ${x.deadlinePassed?'is-past':''}">${x.deadlinePassed?'마감일 지남':x.j.deadline?'마감일 미경과':'마감일 확인 필요'}</span></span><strong>${esc(x.j.title)}</strong><span class="ca-match-why">연관 근거: ${esc(x.why||'공통 직무 키워드')}</span><span class="ca-date-line">${esc(x.j.date||'등록일 확인 전')} · ${esc(x.j.source||'출처 미확인')} <a href="${safe(x.j.url)}" target="_blank" rel="noopener noreferrer">원문 ↗</a></span></span></label>`).join('')}</div>`:
 `<div class="ca-empty-inline"><b>저장된 공고 중 연관성이 확인된 결과가 없습니다.</b><p>뉴스와 직무 설명은 분석할 수 있지만, 관련 채용공고나 공고상 자격요건은 추정하지 않습니다.${!state.showPast?' 마감 공고 포함 옵션을 선택해 과거 사례를 검토할 수도 있습니다.':''}</p></div>`}
 <label class="ca-label" for="caJobText">선택 공고의 공식 주요업무·자격요건·우대사항 (선택)</label>
 <textarea class="select ca-textarea" id="caJobText" rows="3" maxlength="5000" placeholder="공고 원문에 실제 기재된 요건을 붙여 넣으세요. 붙여 넣지 않으면 확인되지 않은 자격요건을 추측하지 않습니다." ${selected?'':'disabled'}>${esc(state.jobText)}</textarea>
 <p class="ca-hint">공고 제목과 분류만으로 필수 역량을 확정할 수 없어요. 현황·마감일은 원문에서 다시 확인하세요. 직접 입력한 공고 내용은 선택한 공고의 자료로만 사용됩니다.</p>
 </section>`;
}
function decisionPanel(e){const p=profile();return `<section class="panel ca-flow-panel ca-decision-panel"><div class="ca-section-title"><span class="ca-step">04</span><div><h3>내 경험과 비교하고 취업전략 받기</h3><p>현재 갖춘 역량, 근거가 없는 역량, 우선 준비할 내용을 구분해 분석합니다.</p></div></div>
 <div class="ca-profile-strip ca-profile-inline"><div><span class="ca-overline">MY PROFILE</span><p>${esc(profileStatus())}</p></div><button type="button" class="button" data-nav="mine" data-me-tab="profile">프로필 수정 →</button></div>
 <label class="ca-label" for="caExperience">이번 분석에 추가할 경험·기술 (선택)</label>
 <textarea id="caExperience" class="select ca-textarea" maxlength="1600" rows="3" placeholder="예: 패키징 공모전에서 via fence 설계·시뮬레이션 수행, 수율 분석 프로젝트에서 Python으로 데이터 처리 등">${esc(state.experience)}</textarea>
 <label class="ca-check"><input id="caConsent" type="checkbox" ${state.consent?'checked':''}> 저장된 내 프로필·보유 기술·프로젝트 경험을 AI 분석에 사용하기</label>
 <p class="ca-hint">동의 시 저장된 프로필과 경험이 LLM 제공자에게 전송됩니다. 동의하지 않으면 직접 입력한 경험만 전송되어 개인별 부족 역량 판단이 제한됩니다. 선택 뉴스·공고와 직접 입력한 내용은 분석할 때 전송됩니다.</p>
 <div class="ca-action-row"><button type="button" id="caRun" class="button primary ca-run" ${!e.n||state.busy?'disabled':''}>✦ 뉴스부터 나의 취업전략까지 한번에 분석</button><button type="button" id="caKeyToggle" class="button">${state.keyOpen?'API 키 설정 닫기':'Gemini API 키 설정'}</button></div>
 ${state.keyOpen?`<div class="ca-key-panel"><label class="ca-label" for="caKeyInput">Gemini API 키</label><input id="caKeyInput" type="password" autocomplete="off" class="input" placeholder="API 키 입력"><button type="button" class="button" id="caKeySave">로컬 서버에 연결</button><p class="ca-hint">키는 실행 중인 로컬 서버 메모리에서만 사용합니다. <a href="https://aistudio.google.com/api-keys" target="_blank" rel="noopener noreferrer">키 발급 안내 ↗</a></p></div>`:''}
 </section>`;}
const sectionTitles=['뉴스에서 확인된 핵심 사실','이 뉴스가 직무에 미칠 영향','연결된 실제 채용공고','요구 역량과 나의 역량 비교','지금부터 실행할 취업 준비'];
function formatted(text){
 const pattern=/^\s*(?:【|\[)?([1-5])[.)\]】]?\s*(?:[.、:]\s*)?[^\n]*$/gm;
 const lines=String(text||'').trim().split('\n');const sections=[];let current=null;
 for(const line of lines){const clean=line.trim();const m=clean.match(/^(?:#{1,3}\s*)?(?:【|\[)?([1-5])[.)\]】]?\s*(?:[.、:]\s*)?(.{2,80})$/);
  if(m&&(/뉴스|직무|채용|역량|준비|실천|이슈|행동/.test(m[2]))){if(current)sections.push(current);current={n:Number(m[1]),text:''};}
  else if(current)current.text+=(current.text?'\n':'')+line;
  else if(clean){if(!current)current={n:0,text:''};current.text+=(current.text?'\n':'')+line;}
 }
 if(current)sections.push(current);
 if(sections.filter(s=>s.n>0).length>=3)return `<div class="ca-result-chain">${sections.map(s=>`<section class="ca-result-step"><span class="ca-step">${String(s.n||'!').padStart(2,'0')}</span><div><h4>${esc(sectionTitles[s.n-1]||'추가 해설')}</h4><div class="ca-result-body">${esc(s.text||'해당 내용을 추가로 확인해 주세요.')}</div></div></section>`).join('')}</div>`;
 return `<div class="ca-analysis">${esc(text)}</div>`;
}
function output(){if(state.busy)return `<section class="ca-output" aria-live="polite"><div class="ca-working"><span class="ca-loader"></span>기사 · 직무 · 공고 · 내 역량을 하나로 연결해 분석하고 있습니다…</div></section>`;
 if(state.error)return `<section class="ca-output ca-error" aria-live="polite"><b>분석하지 못했습니다.</b><div>${esc(state.error)}</div></section>`;
 if(state.analysis)return `<section class="ca-output" id="caAnalysis" aria-live="polite"><div class="ca-output-heading"><div><span class="ca-overline">ONE CONNECTED CAREER DECISION</span><h3>뉴스에서 나의 취업전략까지 · AI 분석 결과</h3></div><button type="button" class="button" id="caCopy">결과 복사</button></div>${formatted(state.analysis)}<div class="ca-evidence-title">사용한 근거 자료 <span>본문의 [N1] · [R1] · [J1] 출처</span></div>${sourceBlock(state.sources)}${state.sources?.role?.source?`<p class="ca-role-source">[R1] 직무 설명: <a href="${safe(state.sources.role.source)}" target="_blank" rel="noopener noreferrer">${esc(state.sources.role.name)} 직무 자료 ↗</a> · 채용공고의 공식 자격요건과 다릅니다.</p>`:''}<p class="ca-hint">기사는 저장된 제목·요약 기준, 공고는 저장된 메타데이터 및 사용자가 입력한 요건 기준입니다. 채용 여부와 자격요건은 공식 원문을 확인하세요. 모델 판단은 합격 가능성이나 채용 확대의 확정 근거가 아닙니다.</p></section>`;
 return `<section class="ca-output ca-empty" aria-live="polite"><div class="ca-empty-icon">✦</div><h3>뉴스 한 건에서 나의 취업전략까지</h3><p>뉴스를 선택하면 관련 직무와 기존 채용공고 후보가 자동으로 연결됩니다.<br>프로필 정보를 확인한 뒤 분석 실행을 누르면 하나의 연속된 취업전략이 만들어집니다.</p></section>`;}
function page({header,live}){const e=evidence(live);return header('AI 취업전략','뉴스 → 직무 영향 → 실제 채용공고 → 필요한 역량 → 내 부족·미확인 역량')
 +`<div class="ca-hero"><div><div class="ca-eyebrow">SEMI-HUB · AI CAREER DECISION</div><h2>기사 하나에서, <strong>나의 취업전략까지.</strong></h2><p>관심 뉴스 한 건을 시작점으로 연결되는 직무, 채용공고, 필요한 기술과 나의 준비 현황을 하나의 분석으로 확인하세요.</p></div><div class="ca-hero-symbol" aria-hidden="true">✳</div></div>
 <div class="ca-flow-map"><span>① 관심 뉴스</span><b>→</b><span>② 직무 영향</span><b>→</b><span>③ 실제 채용공고</span><b>→</b><span>④ 요구 역량 · 내 역량 차이</span></div>
 <div class="ca-kpis"><div class="ca-kpi"><span>참고 기업</span><b>${companies().length}</b></div><div class="ca-kpi"><span>저장된 실제 공고</span><b>${window.SEMI_JOBS_UI?.data?.(live)?.length||0}</b></div><div class="ca-kpi"><span>뉴스 검색 대상</span><b>${window.SEMI_TECH_UI?.items?.(live)?.length||0}</b></div></div>
 <div class="ca-flow-layout"><div class="ca-flow-left">${newsPicker(live,e)}${rolePicker(e)}${jobPicker(e)}${decisionPanel(e)}</div><aside class="ca-flow-right"><section class="panel ca-context ca-sticky"><div class="ca-section-title"><span class="ca-step">↗</span><div><h3>연결된 근거 미리보기</h3><p>분석에 들어갈 실제 자료</p></div></div>${sourceBlock({news:e.news,jobs:e.jobs})}${e.role?`<div class="ca-safety"><b>직무 참고 정보</b><p>${esc(e.role.name)}</p><p>${esc(excerpt(e.role.prep||e.role.work,160))}</p></div>`:''}<div class="ca-safety"><b>근거의 범위</b><p>기사 제목·요약만 확보되어 있으며 채용공고의 필수 자격요건은 없을 수 있습니다.</p><p>관련성이 있다는 것과 채용이 실제로 늘었다는 것은 구분합니다.</p></div></section></aside></div>${output()}
 <div class="ca-bottom-note">AI 응답을 생성하려면 <code>start_semihub.cmd</code>로 서버를 실행하고 Gemini API 키를 연결해야 합니다. 오프라인 HTML에서는 뉴스·공고 매칭 미리보기만 동작합니다.</div>`;}
function bind(render,live){
 const newsSearch=el('caNewsSearch');if(newsSearch){
 let composing=false, filterTimer;
 const refresh=()=>{state.search=newsSearch.value;state.newsUrl='';state.jobUrl='';state.jobText='';invalidate();render();const next=el('caNewsSearch');if(next){next.focus();next.setSelectionRange(state.search.length,state.search.length)}};
 newsSearch.oncompositionstart=()=>{composing=true;clearTimeout(filterTimer)};
 newsSearch.oncompositionend=()=>{composing=false;clearTimeout(filterTimer);filterTimer=setTimeout(refresh,250)};
 newsSearch.oninput=()=>{if(composing)return;clearTimeout(filterTimer);filterTimer=setTimeout(refresh,350)};
 newsSearch.onkeydown=ev=>{if(ev.key==='Enter'&&!composing){ev.preventDefault();clearTimeout(filterTimer);refresh()}};
 }
 const news=el('caNews');if(news)news.onchange=()=>{state.newsUrl=news.value;state.jobUrl='';state.jobText='';invalidate();render()};
 document.querySelectorAll('[data-ca-role]').forEach(b=>b.onclick=()=>{state.role=b.dataset.caRole;state.jobUrl='';state.jobText='';invalidate();render()});
 const role=el('caRole');if(role)role.onchange=()=>{state.role=role.value;state.jobUrl='';state.jobText='';invalidate();render()};
 document.querySelectorAll('[data-ca-job]').forEach(b=>b.onchange=()=>{state.jobUrl=b.dataset.caJob;state.jobText='';invalidate();render()});
 const past=el('caShowPast');if(past)past.onchange=()=>{state.showPast=past.checked;state.jobUrl='';state.jobText='';invalidate();render()};
 const textArea=el('caJobText');if(textArea)textArea.oninput=()=>{state.jobText=textArea.value;invalidate();const out=document.querySelector('.ca-output');if(out)out.hidden=true};
 const experience=el('caExperience');if(experience)experience.oninput=()=>{state.experience=experience.value;invalidate();const out=document.querySelector('.ca-output');if(out)out.hidden=true};
 const consent=el('caConsent');if(consent)consent.onchange=()=>{state.consent=consent.checked;invalidate();render()};
 const toggle=el('caKeyToggle');if(toggle)toggle.onclick=()=>{state.keyOpen=!state.keyOpen;render()};
 const save=el('caKeySave');if(save)save.onclick=async()=>{const key=el('caKeyInput')?.value?.trim();if(!key)return alert('API 키를 입력해 주세요.');save.disabled=true;try{const r=await fetch('/api/ai/key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});const d=await r.json();if(!r.ok)throw Error(d.error||'서버 오류');state.keyOpen=false;render();alert('API 키가 현재 실행 중인 로컬 서버에 연결되었습니다.')}catch(err){alert('API 키 설정 실패: '+String(err.message||err))}finally{save.disabled=false}};
 const run=el('caRun');if(run)run.onclick=async()=>{
  if(location.protocol==='file:'){state.error='오프라인 HTML에서는 AI 호출이 불가능합니다. start_semihub.cmd로 로컬 서버를 실행해 주세요.';render();return}
  const e=evidence(live);if(!e.n){state.error='선택된 뉴스가 없습니다.';render();return}
  const id=++state.requestId;state.busy=true;state.error='';state.analysis=null;render();
  try{const payload={mode:'connected',news:e.news,jobs:e.jobs,role:e.role,profile:userProfile(),focus:{company:companies().find(c=>c.id===state.company)?.name||'',role:e.r?.name||''},job_description:e.chosen?state.jobText:'',profile_consent:state.consent};
   const response=await fetch('/api/ai/career',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'AI 요청 실패');if(state.requestId!==id)return;
   state.analysis=data.analysis||'';state.sources={news:e.news,jobs:e.jobs,role:e.role};state.error='';
  }catch(err){if(state.requestId===id)state.error=String(err.message||err)}finally{if(state.requestId===id){state.busy=false;render();el('caAnalysis')?.scrollIntoView({behavior:'smooth',block:'start'})}}
 };
 const copy=el('caCopy');if(copy)copy.onclick=async()=>{const val=state.analysis||'';try{await navigator.clipboard.writeText(val)}catch(err){const t=document.createElement('textarea');t.value=val;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove()}copy.textContent='복사 완료 ✓'};
}
window.SEMI_CAREER_AI={page,bind,_test:{themes,scoredJobs,evidence,newsItems}};
})();
