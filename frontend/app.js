/* ============================================================
   app.js — 금융공시 모니터링 프론트엔드
   API_BASE: 실제 백엔드 주소. null 이면 목업 데이터로 동작.
   - 로컬 개발: 'http://localhost:8000/api/v1'
   - 운영 배포: 백엔드 서버 URL (Railway/Render 등)
============================================================ */

const API_BASE = window.ENV_API_BASE || null; // index.html의 window.ENV_API_BASE 로 주입

/* ── 목업 데이터 ────────────────────────────────────────────── */
const MOCK_DATA = [
  {
    id: 1001,
    source_agency: '금융위원회', agency_class: 'fsc',
    category: '보도자료',
    title: '"마이데이터 활용 금리인하요구 서비스" 등 혁신금융서비스 3건 신규 지정 의결',
    published_at: '2026-06-17T14:30:00+09:00',
    url: 'https://fsc.go.kr',
    matched_dept: '핀테크사업팀',
    confidence_score: 0.87,
    needs_manual_review: false,
    author_dept_raw: '디지털금융총괄과',
    contact_raw: '송현지 서기관 02-2100-2841',
    body_text: '금융위원회(위원장 이억원)는 6월 17일 정례회의를 통해 3건의 혁신금융서비스를 신규로 지정하였다. 이로써 현재까지 총 1,075건의 서비스가 혁신금융서비스로 지정되어 시장에서 테스트할 수 있게 되었다.\n\n금융위원회는 농업협동조합중앙회의 "마이데이터 활용 금리인하요구 서비스"를 혁신금융서비스로 신규 지정하였다. 이에 따라 농협이 제공하는 마이데이터서비스를 활용하여 적시에 금리인하요구권을 행사할 수 있게 되었다.',
  },
  {
    id: 1002,
    source_agency: '금융위원회', agency_class: 'fsc',
    category: '보도자료',
    title: '연체 채무자의 부담을 가중시키는 금융회사의 채권매각 관행을 바로잡겠습니다',
    published_at: '2026-06-17T10:15:00+09:00',
    url: 'https://fsc.go.kr',
    matched_dept: '여신관리팀',
    confidence_score: 0.83,
    needs_manual_review: false,
    author_dept_raw: '서민금융과',
    contact_raw: '',
    body_text: '금융위원회는 「채권추심 및 대출채권 매각 가이드라인」 개정안을 사전예고하였다. 이번 개정안은 원채권 금융회사에 채권매각 이후 양수인의 불법행위에 대한 점검·보고의무를 부여하고, 채권매각계약서에 재매각시 승계되는 채무자 보호 조건을 포함하도록 의무화하는 내용이다.',
  },
  {
    id: 1003,
    source_agency: '금융위원회', agency_class: 'fsc',
    category: '보도자료',
    title: '잘「알고투자」하는 금융교육으로 국민의 안정적 자산형성을 지원하겠습니다',
    published_at: '2026-06-16T16:00:00+09:00',
    url: 'https://fsc.go.kr',
    matched_dept: '소비자보호팀',
    confidence_score: 0.79,
    needs_manual_review: false,
    author_dept_raw: '금융소비자정책과',
    contact_raw: '',
    body_text: '금융위원회 권대영 부위원장은 6.16일 관계부처 위원 및 민간전문가 등과 함께 「2026년 제1차 금융교육협의회」를 개최하여 「자본시장·금융투자 분야 금융교육 강화방안」등에 대해 논의하였다.',
  },
  {
    id: 1004,
    source_agency: '금융감독원', agency_class: 'fss',
    category: '보도자료',
    title: '2025년 국내은행 경영실태평가 결과 및 시사점',
    published_at: '2026-06-16T11:00:00+09:00',
    url: 'https://fss.or.kr',
    matched_dept: '리스크관리부',
    confidence_score: 0.91,
    needs_manual_review: false,
    author_dept_raw: '은행감독국',
    contact_raw: '김민준 팀장 02-3145-7800',
    body_text: '금융감독원은 2025년 국내은행 경영실태평가(CAMEL-R) 결과를 발표하였다. 전반적인 은행 건전성은 양호한 수준을 유지하고 있으나, 일부 지방은행과 인터넷전문은행의 수익성 지표가 전년 대비 소폭 하락하였다.',
  },
  {
    id: 1005,
    source_agency: '금융감독원', agency_class: 'fss',
    category: '제재공시',
    title: '불법 유사투자자문업 운영 행위자에 대한 수사기관 통보',
    published_at: '2026-06-15T14:00:00+09:00',
    url: 'https://fss.or.kr',
    matched_dept: null,
    confidence_score: 0.31,
    needs_manual_review: true,
    author_dept_raw: '',
    contact_raw: '',
    body_text: '금융감독원은 소셜미디어를 통해 불법으로 유사투자자문업을 운영한 행위자에 대하여 관련 법령에 따라 수사기관에 통보 조치하였다.',
  },
  {
    id: 1006,
    source_agency: '한국은행', agency_class: 'bok',
    category: '의결결과',
    title: '금융통화위원회 기준금리 동결 결정 (3.00%) — 2026년 6월 통화정책방향',
    published_at: '2026-06-13T10:30:00+09:00',
    url: 'https://bok.or.kr',
    matched_dept: '자금운용팀',
    confidence_score: 0.72,
    needs_manual_review: false,
    author_dept_raw: '통화정책국',
    contact_raw: '박수연 과장 02-759-4114',
    body_text: '금융통화위원회는 다음 통화정책방향 결정 시까지 한국은행 기준금리를 현 수준(3.00%)에서 유지하여 통화정책을 운용하기로 하였다.',
  },
  {
    id: 1007,
    source_agency: '금융정보분석원', agency_class: 'kofiu',
    category: '고시·공고',
    title: '특정금융거래정보의 보고 및 이용 등에 관한 법률 시행령 일부개정령안 입법예고',
    published_at: '2026-06-12T09:00:00+09:00',
    url: 'https://kofiu.go.kr',
    matched_dept: 'AML대응팀',
    confidence_score: 0.68,
    needs_manual_review: false,
    author_dept_raw: '',
    contact_raw: '',
    body_text: '금융정보분석원은 특정금융거래정보의 보고 및 이용 등에 관한 법률 시행령 일부개정령안을 2026년 6월 12일부터 7월 2일까지 입법예고합니다.',
  },
  {
    id: 1008,
    source_agency: '법령해석포털', agency_class: 'moleg',
    category: '법령해석',
    title: '전자금융거래법 제22조에 따른 이용자 정보 제공 의무 범위 해석',
    published_at: '2026-06-11T15:00:00+09:00',
    url: 'https://moleg.go.kr',
    matched_dept: '법무지원팀',
    confidence_score: 0.55,
    needs_manual_review: false,
    author_dept_raw: '',
    contact_raw: '',
    body_text: '전자금융거래법 제22조의 이용자 정보 제공 의무는 전자금융업자가 이용자의 거래내역, 개인정보 등을 제3자에게 제공할 때 사전 동의를 받아야 하는 범위와 방식을 규정하고 있습니다.',
  },
  {
    id: 1009,
    source_agency: '금융위원회', agency_class: 'fsc',
    category: '고시·공고',
    title: '2026년 하반기 혁신금융서비스 지정 신청 공고',
    published_at: '2026-06-10T10:00:00+09:00',
    url: 'https://fsc.go.kr',
    matched_dept: '핀테크사업팀',
    confidence_score: 0.82,
    needs_manual_review: false,
    author_dept_raw: '디지털금융총괄과',
    contact_raw: '이혜인 사무관 02-2100-2872',
    body_text: '금융위원회는 2026년 하반기 혁신금융서비스 지정 신청을 공고합니다. 신청 기간은 2026년 6월 10일부터 7월 10일까지이며, 지정 요건 및 신청 방법은 공고문을 참조하시기 바랍니다.',
  },
  {
    id: 1010,
    source_agency: '금융감독원', agency_class: 'fss',
    category: '보도자료',
    title: '2026년 1분기 가계대출 동향 및 시사점',
    published_at: '2026-06-09T14:30:00+09:00',
    url: 'https://fss.or.kr',
    matched_dept: '여신심사팀',
    confidence_score: 0.75,
    needs_manual_review: false,
    author_dept_raw: '가계부채팀',
    contact_raw: '홍길동 팀장 02-3145-5600',
    body_text: '금융감독원은 2026년 1분기 가계대출 동향을 발표하였다. 전 금융권 가계대출 잔액은 전분기 대비 2.1조원 증가한 1,872.3조원을 기록하였으며, 주택담보대출 중심으로 증가세가 지속되었다.',
  },
  {
    id: 1011,
    source_agency: '한국은행', agency_class: 'bok',
    category: '보도자료',
    title: '2026년 5월 금융시장 동향',
    published_at: '2026-06-08T12:00:00+09:00',
    url: 'https://bok.or.kr',
    matched_dept: '경영기획팀',
    confidence_score: 0.44,
    needs_manual_review: false,
    author_dept_raw: '',
    contact_raw: '',
    body_text: '2026년 5월 중 금융시장은 국내외 불확실성이 완화되면서 안정세를 보였다. 주가는 상승하고 장기금리는 소폭 하락하였으며, 원/달러 환율은 미 달러화 약세의 영향으로 하락하였다.',
  },
  {
    id: 1012,
    source_agency: '금융정보분석원', agency_class: 'kofiu',
    category: '보도자료',
    title: '2025년 의심거래보고(STR) 및 고액현금거래보고(CTR) 통계 분석',
    published_at: '2026-06-07T11:00:00+09:00',
    url: 'https://kofiu.go.kr',
    matched_dept: 'AML대응팀',
    confidence_score: 0.88,
    needs_manual_review: false,
    author_dept_raw: '정보분석팀',
    contact_raw: '김영철 과장 02-6908-9500',
    body_text: '금융정보분석원은 2025년 금융기관 등이 보고한 의심거래보고(STR) 및 고액현금거래보고(CTR) 현황을 분석한 결과를 발표하였다. 2025년 STR 건수는 총 187만 건으로 전년 대비 12.3% 증가하였다.',
  },
];

/* ── 상태 ──────────────────────────────────────────────────── */
const state = {
  data: [...MOCK_DATA],
  filtered: [],
  page: 1,
  perPage: 10,
  range: 'M',
  agencies: new Set(['금융감독원','금융위원회','금융정보분석원','법령해석포털','한국은행']),
  categories: new Set(['보도자료','고시·공고','의결결과','법령해석','제재공시']),
  minConf: 0,
  deptQuery: '',
  showReviewOnly: false,
};

/* ── 유틸 ──────────────────────────────────────────────────── */
function confClass(score) {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'mid';
  return 'low';
}
function confLabel(score) {
  if (score >= 0.7) return '높음';
  if (score >= 0.4) return '중간';
  return '낮음';
}
function relativeTime(isoStr) {
  const diff = (Date.now() - new Date(isoStr)) / 1000;
  if (diff < 60)   return '방금 전';
  if (diff < 3600) return `${Math.floor(diff/60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff/3600)}시간 전`;
  return `${Math.floor(diff/86400)}일 전`;
}
function formatDate(isoStr) {
  const d = new Date(isoStr);
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

/* ── 필터 ──────────────────────────────────────────────────── */
function applyFilter() {
  const now = Date.now();
  const rangeCut = { D: 86400e3, W: 7*86400e3, M: 30*86400e3, ALL: Infinity };
  const cut = rangeCut[state.range];

  state.filtered = state.data.filter(item => {
    const age = now - new Date(item.published_at);
    if (age > cut) return false;
    if (!state.agencies.has(item.source_agency)) return false;
    if (!state.categories.has(item.category)) return false;
    if (item.confidence_score < state.minConf) return false;
    if (state.deptQuery && item.matched_dept &&
        !item.matched_dept.includes(state.deptQuery)) return false;
    if (state.showReviewOnly && !item.needs_manual_review) return false;
    return true;
  });

  state.page = 1;
  renderFeed();
  renderPagination();
  updateCounts();
}

/* ── 렌더링 ────────────────────────────────────────────────── */
function renderFeed() {
  const list = document.getElementById('feedList');
  const total = state.filtered.length;
  document.getElementById('totalCount').textContent = total.toLocaleString();

  if (total === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <p>해당 조건의 게시물이 없습니다</p>
      </div>`;
    return;
  }

  const start = (state.page - 1) * state.perPage;
  const items = state.filtered.slice(start, start + state.perPage);

  list.innerHTML = items.map(item => cardHTML(item)).join('');

  // 카드 클릭 이벤트
  list.querySelectorAll('.feed-card').forEach(card => {
    card.addEventListener('click', () => {
      const id = Number(card.dataset.id);
      const item = state.data.find(d => d.id === id);
      if (item) openModal(item);
    });
  });
}

function cardHTML(item) {
  const cc = confClass(item.confidence_score);
  const pct = Math.round(item.confidence_score * 100);

  const deptBadge = item.needs_manual_review
    ? `<span class="badge-review">⚠ 수동검토</span>`
    : item.matched_dept
      ? `<span class="dept-badge">${item.matched_dept}</span>`
      : `<span class="card-no-match">미매칭</span>`;

  const confRow = item.needs_manual_review ? '' : `
    <div class="card-conf-row">
      <div class="conf-track"><div class="conf-fill ${cc}" style="width:${pct}%"></div></div>
      <span class="conf-pct ${cc}">${pct}%</span>
    </div>`;

  return `
    <div class="feed-card" data-id="${item.id}">
      <div class="card-bar" style="background:var(--${item.agency_class})"></div>
      <div class="card-body">
        <div class="card-meta">
          <span class="card-agency ${item.agency_class}">${item.source_agency}</span>
          <span class="card-category">${item.category}</span>
          <span class="card-date">${relativeTime(item.published_at)}</span>
        </div>
        <div class="card-title-row">
          <a class="card-title" href="${item.url}" target="_blank" rel="noopener"
             onclick="event.stopPropagation()">${item.title}</a>
          ${deptBadge}
        </div>
        ${confRow}
      </div>
    </div>`;
}

function renderPagination() {
  const total = state.filtered.length;
  const totalPages = Math.ceil(total / state.perPage);
  const pg = document.getElementById('pagination');
  if (totalPages <= 1) { pg.innerHTML = ''; return; }

  let html = `<button class="page-btn" ${state.page===1?'disabled':''} onclick="goPage(${state.page-1})">‹</button>`;
  for (let i = 1; i <= totalPages; i++) {
    if (i===1 || i===totalPages || Math.abs(i-state.page)<=1) {
      html += `<button class="page-btn ${i===state.page?'active':''}" onclick="goPage(${i})">${i}</button>`;
    } else if (Math.abs(i-state.page)===2) {
      html += `<span style="color:var(--text-muted);padding:0 4px">…</span>`;
    }
  }
  html += `<button class="page-btn" ${state.page===totalPages?'disabled':''} onclick="goPage(${state.page+1})">›</button>`;
  pg.innerHTML = html;
}

function goPage(n) {
  state.page = n;
  renderFeed();
  renderPagination();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateCounts() {
  const agencies = ['금융감독원','금융위원회','금융정보분석원','법령해석포털','한국은행'];
  agencies.forEach(ag => {
    const el = document.getElementById('cnt-' + ag);
    if (!el) return;
    el.textContent = state.data.filter(d => d.source_agency === ag).length;
  });

  // 부서 필터 목록 갱신
  const depts = [...new Set(state.filtered.map(d => d.matched_dept).filter(Boolean))].sort();
  const dl = document.getElementById('deptFilter');
  if (!dl) return;
  dl.innerHTML = depts
    .filter(d => !state.deptQuery || d.includes(state.deptQuery))
    .slice(0, 15)
    .map(d => `
      <li>
        <label>
          <input type="checkbox" value="${d}" checked />
          <span>${d}</span>
        </label>
      </li>`).join('');
}

/* ── 모달 ──────────────────────────────────────────────────── */
function openModal(item) {
  const cc = confClass(item.confidence_score);
  const pct = Math.round(item.confidence_score * 100);

  const contactHTML = item.contact_raw
    ? `<div class="modal-contact">
         <span>📋 원문 담당부서: <strong>${item.author_dept_raw || '미기재'}</strong></span>
         <span>📞 담당자: <strong>${item.contact_raw}</strong></span>
       </div>` : '';

  document.getElementById('modalContent').innerHTML = `
    <div class="modal-agency-row">
      <span class="card-agency ${item.agency_class}">${item.source_agency}</span>
      <span style="font-size:12px;color:var(--text-muted)">${item.category}</span>
      <span style="font-size:12px;color:var(--text-muted);margin-left:auto">${formatDate(item.published_at)}</span>
    </div>
    <div class="modal-title">${item.title}</div>

    <div class="modal-dept-section">
      <div class="modal-dept-title">AI 부서 매칭 결과</div>
      <div class="modal-final-dept">
        <span class="modal-dept-name">
          ${item.needs_manual_review
            ? '<span class="badge-review">⚠ 수동검토 필요 — 신뢰도 부족</span>'
            : `🏢 ${item.matched_dept || '매칭 실패'}`}
        </span>
        <span class="modal-conf-badge ${cc}">
          신뢰도 ${pct}% · ${confLabel(item.confidence_score)}
        </span>
      </div>
    </div>

    ${contactHTML}

    <div class="modal-body-text">${item.body_text}</div>

    <div class="modal-actions">
      <a href="${item.url}" target="_blank" rel="noopener" class="btn-primary">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        원문 보기
      </a>
      <button class="btn-secondary" onclick="copyLink('${item.url}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
        링크 복사
      </button>
      <button class="btn-secondary" onclick="requestRematch(${item.id})" style="margin-left:auto">
        🔄 매칭 재요청
      </button>
    </div>`;

  document.getElementById('modalOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('open');
  document.body.style.overflow = '';
}

function copyLink(url) {
  navigator.clipboard.writeText(url).then(() => showToast('링크 복사됨'));
}

async function requestRematch(id) {
  if (!API_BASE) { showToast('API 연결 필요'); return; }
  showToast('재매칭 요청 중...');
  try {
    const res = await fetch(`${API_BASE}/announcements/${id}/rematch`, { method: 'POST' });
    if (!res.ok) throw new Error();
    const data = await res.json();
    const item = state.data.find(d => d.id === id);
    if (item) {
      item.matched_dept = data.matched_dept;
      item.confidence_score = data.confidence_score;
      item.needs_manual_review = data.needs_manual_review;
    }
    showToast(`재매칭 완료: ${data.matched_dept || '미매칭'} (${Math.round(data.confidence_score * 100)}%)`);
    closeModal();
    applyFilter();
  } catch (e) {
    showToast('재매칭 요청 실패');
  }
}

/* ── 토스트 ─────────────────────────────────────────────────── */
function showToast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  Object.assign(t.style, {
    position:'fixed', bottom:'24px', left:'50%', transform:'translateX(-50%)',
    background:'#323232', color:'#fff', padding:'10px 20px', borderRadius:'8px',
    fontSize:'13px', zIndex:9999, pointerEvents:'none',
    boxShadow:'0 4px 12px rgba(0,0,0,.2)',
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2200);
}

/* ── API 연동 (실제 서버 연결 시 목업 대체) ─────────────────── */
async function fetchFromAPI() {
  if (!API_BASE) return;
  try {
    const res = await fetch(`${API_BASE}/announcements?range=ALL&per_page=200`);
    const json = await res.json();
    // API 응답 성공 시 항상 실제 데이터로 교체 (빈 배열이어도 mock 유지 안 함)
    if (Array.isArray(json.items)) {
      state.data = json.items;
    }
  } catch (e) {
    console.warn('API 연결 실패, 목업 데이터 사용:', e.message);
  }
}

/* ── 이벤트 바인딩 ──────────────────────────────────────────── */
function bindEvents() {
  // 기간 토글
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.range = btn.dataset.range;
      applyFilter();
    });
  });

  // 기관 체크박스
  document.getElementById('agencyFilter').addEventListener('change', e => {
    const cb = e.target;
    if (cb.value === 'all') {
      document.querySelectorAll('#agencyFilter input:not([value="all"])').forEach(c => {
        c.checked = cb.checked;
      });
      state.agencies = cb.checked
        ? new Set(['금융감독원','금융위원회','금융정보분석원','법령해석포털','한국은행'])
        : new Set();
    } else {
      cb.checked ? state.agencies.add(cb.value) : state.agencies.delete(cb.value);
    }
    applyFilter();
  });

  // 카테고리 체크박스
  document.getElementById('categoryFilter').addEventListener('change', e => {
    const cb = e.target;
    if (cb.value === 'all') {
      document.querySelectorAll('#categoryFilter input:not([value="all"])').forEach(c => {
        c.checked = cb.checked;
      });
      state.categories = cb.checked
        ? new Set(['보도자료','고시·공고','의결결과','법령해석','제재공시'])
        : new Set();
    } else {
      cb.checked ? state.categories.add(cb.value) : state.categories.delete(cb.value);
    }
    applyFilter();
  });

  // 신뢰도 슬라이더
  document.getElementById('confSlider').addEventListener('input', e => {
    const v = Number(e.target.value);
    state.minConf = v / 100;
    document.getElementById('confVal').textContent = `${v}% 이상`;
    applyFilter();
  });

  // 부서 검색
  document.getElementById('deptSearch').addEventListener('input', e => {
    state.deptQuery = e.target.value.trim();
    applyFilter();
  });

  // 수동검토 필터
  document.getElementById('showReviewOnly').addEventListener('change', e => {
    state.showReviewOnly = e.target.checked;
    applyFilter();
  });

  // 모달 닫기
  document.getElementById('modalClose').addEventListener('click', closeModal);
  document.getElementById('modalOverlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

/* ── 스켈레톤 로더 ───────────────────────────────────────────── */
function showSkeleton() {
  const list = document.getElementById('feedList');
  if (!list) return;
  list.innerHTML = Array(6).fill(`
    <div class="skeleton-card">
      <div class="sk-bar skeleton" style="height:60px;width:3px"></div>
      <div class="sk-body">
        <div class="sk-line skeleton" style="width:30%"></div>
        <div class="sk-line skeleton" style="width:80%"></div>
        <div class="sk-line skeleton" style="width:55%"></div>
      </div>
    </div>`).join('');
}

/* ── 초기화 ─────────────────────────────────────────────────── */
async function init() {
  if (!document.getElementById('feedList')) return;
  showSkeleton();
  await fetchFromAPI();         // API 있으면 실제 데이터, 없으면 목업
  state.filtered = [...state.data];
  bindEvents();
  updateCounts();
  applyFilter();
}

init();
