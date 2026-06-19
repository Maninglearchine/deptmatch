# PRD: 금융공시 및 주요 공고 크롤링 + 부서 자동 매칭 서비스

**문서 버전**: v2.0  
**최초 작성일**: 2026-06-17  
**최종 수정일**: 2026-06-19  
**주요 변경 (v1.0 → v2.0)**: BGE-M3 모델 전환, Cross-Encoder 재순위화 추가, 단일 모델 디렉터리 구조로 통합, 백엔드 실제 구현 반영

---

## 1. 개요 (Overview)

### 1.1 배경
금융위원회, 금융감독원, 법제처 등 금융 유관 기관은 매일 수십 건의 보도자료·공시·공고를 발행한다. 담당 부서 직원은 이를 수동으로 모니터링하고 본인 업무 관련 항목을 선별해야 하는데, 기관별 사이트를 직접 방문해야 하고 "이 공고가 어느 팀 소관인지" 파악하는 데 추가 시간이 소요된다.

### 1.2 서비스 목적
- 주요 금융 기관의 공시·공고를 **시간 단위**로 자동 수집
- 각 공고의 본문 내용을 분석하여 **사내 담당 부서를 자동 매칭**해 함께 노출
- 담당자가 단일 화면에서 관련 공시를 빠르게 파악하고 후속 조치를 취할 수 있도록 지원

### 1.3 참조 서비스
- **프론트엔드**: newstogram.xyz (금융당국 모니터링 봇) — 기관별 카테고리, 기간 필터, Telegram 연동 구조 참조
- **백엔드 모델**: v4.1.ipynb — BAAI/bge-m3 기반 두 단계 파인튜닝 + Cross-Encoder 재순위화

---

## 2. 목표 및 성공 지표 (Goals & KPIs)

| 목표 | 측정 지표 | 목표값 |
|------|----------|--------|
| 공시 수집 지연 최소화 | 기관 원문 게시 → 서비스 노출 소요 시간 | ≤ 1시간 |
| 부서 매칭 정확도 | Top-1 정확도 (내부 테스트셋 기준) | ≥ 80% |
| 부서 매칭 후보 포함률 | Top-5 내 정답 부서 포함율 | ≥ 95% |
| 서비스 가용성 | 월간 업타임 | ≥ 99.5% |
| 크롤링 성공률 | 수집 시도 대비 성공 건수 | ≥ 99% |

---

## 3. 사용자 및 이해관계자 (Stakeholders)

| 구분 | 역할 | 주요 니즈 |
|------|------|----------|
| **내부 업무 담당자** | 1차 사용자 | 본인 부서 소관 공고 빠른 파악 |
| **부서 관리자** | 2차 사용자 | 팀 전체 모니터링 현황 파악 |
| **컴플라이언스 팀** | 이해관계자 | 규제 변화 대응 현황 추적 |
| **IT/개발팀** | 운영자 | 크롤러 안정성, 모델 재학습 관리 |

---

## 4. 크롤링 대상 및 범위 (Data Sources)

### 4.1 수집 기관 및 카테고리

| 기관 | 카테고리 | 수집 주기 | URL 패턴 |
|------|---------|----------|----------|
| **금융위원회** | 보도자료, 고시·공고, 의결 결과 | 매 1시간 | fsc.go.kr |
| **금융감독원** | 보도자료, 제재·제도 공시 | 매 1시간 | fss.or.kr |
| **금융정보분석원 (KoFIU)** | 보도자료, 고시 | 매 1시간 | kofiu.go.kr |
| **법령해석포털 (법제처)** | 법령해석, 의견서 | 매 2시간 | moleg.go.kr |
| **한국은행** | 금통위 의결, 보도자료 | 매 2시간 | bok.or.kr |

> **참조**: newstogram.xyz의 기관 구조(금융감독원·금융위원회·금융정보분석원·법령해석포털·한국은행)를 기반으로 설계

### 4.2 수집 필드

```
- 제목 (title)
- 발행 기관 (source_agency)
- 카테고리 (category)
- 게시일시 (published_at)
- 원문 URL (url)
- 본문 텍스트 (body_text)
- 담당부서명 (author_dept) — 원문에 기재된 경우 추출
- 담당자명 / 연락처 (contact_info) — 원문에 기재된 경우 추출
- 첨부파일 링크 목록 (attachments)
```

---

## 5. 부서 자동 매칭 기능 (Department Auto-Matching)

### 5.1 모델 개요 (v4.1.ipynb 기반)

**핵심 구조**: BGE-M3 Hybrid Retrieval → Cross-Encoder Re-ranking

```
공시 본문 텍스트 (query, 길이 제한 없음 — BGE-M3 최대 8192 토큰)
        ↓ preprocess(): 제목 + 담당부서 힌트 + 본문 구조화
  ┌─────────────────────────────────────────────────────┐
  │  학습 파이프라인 (Google Colab GPU, v4.1.ipynb)       │
  │                                                     │
  │  Stage 1: 도메인 적응                                │
  │    Base  : BAAI/bge-m3 (570M 파라미터, 8192 토큰)    │
  │    데이터 : 업무담당규정.docx (문단 단위 self-positive) │
  │    Loss  : MultipleNegativesRankingLoss              │
  │       ↓ 저장 → bge_m3_finetuned/                   │
  │                                                     │
  │  Stage 2: 부서 매칭 특화                              │
  │    Base  : bge_m3_finetuned/ (Stage 1 출력)          │
  │    데이터 : dept.xlsx (단일 업무문장 + 부서+업무 조합   │
  │            + 무작위 3~5개 업무 결합 증강)             │
  │    Loss  : MultipleNegativesRankingLoss              │
  │       ↓ 저장 → bge_m3_finetuned/ (덮어쓰기)         │
  └─────────────────────────────────────────────────────┘
        ↓ (최종 모델: bge_m3_finetuned/)
  ┌──────────────┬──────────────┬──────────────┐
  │ Dense Score  │ TF-IDF Score │ BM25 Score   │
  │ BGE-M3 임베딩│ (char 2-5gram)│ (토큰 기반)  │
  │    55%       │    25%       │    20%       │
  └──────────────┴──────────────┴──────────────┘
        ↓ Min-Max 정규화 + 가중 합산
  상위 120개 후보 (CANDIDATE_K=120)
        ↓
  ┌─────────────────────────────────────────────┐
  │  Cross-Encoder Re-ranking (RERANK_TOP_K=10) │
  │  모델: BAAI/bge-reranker-v2-m3              │
  │  confidence = sigmoid(s0)*0.7 + gap*0.3     │
  └─────────────────────────────────────────────┘
        ↓
  최종 부서 1건 + confidence_score 반환
```

**이전 모델(v3.ipynb) 대비 변경 사항:**

| 항목 | v3 (구) | v4.1 (현재) |
|------|---------|------------|
| Base 모델 | jhgan/ko-sroberta-multitask (122M) | BAAI/bge-m3 (570M) |
| 최대 입력 길이 | 512 토큰 (길이 초과 시 정보 손실) | 8192 토큰 (전체 본문 처리 가능) |
| 언어 지원 | 한국어 전용 | 다국어 (한국어 포함) |
| Re-ranking | 없음 | Cross-Encoder (bge-reranker-v2-m3) |
| 모델 후보 수집 | top-80 → 다수결 top-5 | top-120 → Cross-Encoder top-10 → top-1 |
| 신뢰도 계산 | bi-encoder 점수 직접 사용 | sigmoid 정규화 + gap 가중치 |
| 모델 저장 경로 | stage1_domain_retriever/, stage2_dept_retriever/ | bge_m3_finetuned/ (단일 경로) |

### 5.2 입력 데이터 (dept.xlsx)

| 컬럼 | 설명 |
|------|------|
| `HNG_BR_NM` | 부서명 (한글) |
| `OFWRK_NM` | 해당 부서의 업무 설명 |

- 부서별 5행 단위 chunk로 분할하여 검색 corpus 구성 (DEPT_CHUNK_SIZE=5)
- corpus 텍스트 형식: `[부서명] {dept}\n[담당업무]\n- {work1}\n- {work2}...`

### 5.3 쿼리 전처리 (preprocess)

```python
# BGE-M3 (max 8192 tokens) — 길이 제한 없이 전체 본문 구조화
# 1. 첫 줄을 제목으로 분리
# 2. "담당 부서/과/팀" 힌트 문장 최대 3개 우선 배치
# 3. 나머지 본문 이어 붙임
→ "{제목} {힌트문장1} {힌트문장2} {본문전체}"
```

### 5.4 매칭 결과 스펙

```json
{
  "dept": "디지털금융총괄과",
  "confidence": 0.87,
  "needs_review": false
}
```

- `needs_review`: `confidence < CONFIDENCE_REVIEW(0.4)` 시 `true`
- `confidence`: Cross-Encoder sigmoid 정규화 기반 (`s0 * 0.7 + gap * 0.3`)
  - Reranker 미사용 시 bi-encoder top-1 점수로 대체

### 5.5 모델 운영 방식

| 항목 | 내용 |
|------|------|
| 학습 환경 | Google Colab GPU (CUDA, A100 권장) |
| 학습 주기 | dept.xlsx 업데이트 시 Stage 2 재학습 (월 1회 이상) |
| 모델 저장 | `bge_m3_finetuned/` — Stage 1 저장 후 Stage 2 덮어쓰기 (단일 경로) |
| Drive 백업 | Google Drive `/bge_m3_finetuned/` 에 자동 저장 후 가중치 파일 존재 검증 |
| 추론 환경 | CPU 서버 (인퍼런스는 GPU 불필요) |
| fallback 순서 | `bge_m3_finetuned/` → HF 캐시 BAAI/bge-m3 다운로드 |
| reranker fallback | `reranker_model/` → HF 캐시 `BAAI/bge-reranker-v2-m3` / 로드 실패 시 bi-encoder 단독 사용 |
| 신뢰도 임계값 | `CONFIDENCE_AUTO=0.7` (자동 확정) / `CONFIDENCE_REVIEW=0.4` (수동 검토) |

---

## 6. 프론트엔드 요구사항 (Frontend Requirements)

> newstogram.xyz 구조를 참조하되, **부서 매칭 결과 노출**이 핵심 추가 기능

### 6.1 주요 화면 구성

#### 6.1.1 메인 피드 화면

```
┌─────────────────────────────────────────────────┐
│  [로고] 금융공시 모니터링        Telegram | About │
├─────────────────────────────────────────────────┤
│  기관 탭: [전체] [금융위] [금감원] [KoFIU] [법제처] [한국은행] │
│  기간 필터: [오늘] [이번주] [이번달] [전체]          │
│  부서 필터: [전체 부서 ▼]   카테고리: [전체 ▼]       │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ [금융위원회] 보도자료  2026-06-17 14:30      │ │
│ │ "마이데이터 활용 금리인하요구 서비스" 혁신금융 3건 지정 │ │
│ │                                             │ │
│ │ 매칭 부서: 🏢 디지털금융총괄과  ████████░░ 87% │ │
│ │ 후보: 핀테크혁신과 71% | 전자금융과 60%         │ │
│ │                          [원문 보기] [공유]   │ │
│ └─────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────┐ │
│ │ [금융위원회] 보도자료  2026-06-17 10:15      │ │
│ │ 연체 채무자 채권매각 관행 개선방안             │ │
│ │                                             │ │
│ │ 매칭 부서: 🏢 서민금융과        ████████░░ 83% │ │
│ │           [원문 보기] [공유]                  │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### 6.1.2 공시 상세 화면

- 원문 전체 본문 표시
- 매칭 부서 정보 (Top-5 신뢰도 바 차트)
- 원문 기재 담당부서 / 담당자 / 연락처 (존재 시)
- 원문 URL 바로가기
- 첨부파일 다운로드 링크

#### 6.1.3 부서별 대시보드

- 내 부서 필터 설정 후 저장
- 해당 부서 관련 공시만 모아보기
- 미확인 건수 뱃지 표시

### 6.2 UI 컴포넌트 요구사항

| 컴포넌트 | 설명 |
|---------|------|
| 공시 카드 | 기관 배지, 카테고리, 제목, 게시일시, 매칭 부서 + 신뢰도 |
| 부서 매칭 바 | 신뢰도 % 시각화 (progress bar), 상위 3개 후보 표시 |
| 기간 필터 | D(오늘) / W(이번주) / M(이번달) / ALL |
| 기관 필터 탭 | 기관별 탭 + 미확인 건수 뱃지 |
| 부서 필터 드롭다운 | 부서명 검색 가능한 select |
| 알림 설정 | Telegram / 이메일 수신 조건 설정 |
| 신뢰도 경고 | 신뢰도 < 40% 시 "⚠️ 수동 검토 필요" 표시 |

### 6.3 Telegram Bot 연동

- 신규 공시 수집 즉시 구독 채널에 푸시
- 메시지 형식: `[기관] 제목 | 매칭부서: {dept} ({score}%) | {url}`
- 부서별 채널 분리 구독 지원

---

## 7. 백엔드 아키텍처 (Backend Architecture)

### 7.1 전체 구성 (현재 구현)

```
┌──────────────────────────────────────────────────────────────────┐
│                          외부 기관 사이트                          │
│  금융위 | 금감원 | KoFIU | 법제처 | 한국은행                       │
└─────────────────────┬────────────────────────────────────────────┘
                      │ HTTP/Playwright
┌─────────────────────▼────────────────────────────────────────────┐
│                     크롤러 레이어 (Crawler Layer)                  │
│  - 기관별 크롤러 모듈 (독립 스케줄, APScheduler)                   │
│  - 중복 감지 (URL unique constraint)                              │
│  - 본문 정제 (HTML → plain text)                                  │
│  - 원문 담당부서/연락처 추출 (정규식)                               │
└─────────────────────┬────────────────────────────────────────────┘
                      │ 수집 즉시 매칭 처리 (동기)
┌─────────────────────▼────────────────────────────────────────────┐
│              부서 매칭 서비스 (matcher.py)                         │
│  - BGE-M3 Hybrid Retrieval (Dense 55% + TF-IDF 25% + BM25 20%) │
│  - Cross-Encoder Re-ranking (bge-reranker-v2-m3)                │
│  - confidence = sigmoid(s0)*0.7 + gap*0.3                       │
└─────────────────────┬────────────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────────────┐
│                   데이터베이스 (SQLite / 운영: PostgreSQL 검토)     │
│  announcements, dept_matches, departments, crawl_logs            │
└─────────────────────┬────────────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────────────┐
│                    API 서버 (FastAPI + uvicorn)                   │
│  GET /api/v1/announcements  |  GET /api/v1/announcements/{id}    │
│  GET /api/v1/departments    |  POST /api/v1/match                │
└─────────────────────┬────────────────────────────────────────────┘
                      │
             ┌────────┴──────────┐
             ▼                   ▼
       웹 프론트엔드           Telegram Bot
       (Vanilla JS)           (알림 발송, 예정)
       API_BASE: localhost:8000
```

### 7.2 크롤러 설계 원칙

- **기관별 독립 모듈**: 각 기관의 구조 변경이 다른 기관에 영향 없도록 분리
- **점진적 크롤링**: 마지막 수집 ID/날짜 이후 신규 건만 수집
- **중복 방지**: `(source_agency, url)` unique constraint + 제목+날짜 해시 체크
- **요청 간격 준수**: 기관별 robots.txt 존중, 요청 간 1~3초 딜레이
- **에러 처리**: 수집 실패 시 지수 백오프 재시도 (최대 3회)
- **스케줄러**: APScheduler (BackgroundScheduler) — 기관별 독립 주기 설정

### 7.3 부서 매칭 모델 서빙

| 항목 | 내용 |
|------|------|
| 프레임워크 | FastAPI + uvicorn |
| 모델 로딩 | 서버 시작 시 1회 로드 (`get_matcher()` singleton), 메모리 상주 |
| 임베더 로드 순서 | `bge_m3_finetuned/` (가중치 파일 존재 확인) → HF 캐시 BAAI/bge-m3 |
| Reranker 로드 순서 | `reranker_model/` → HF 캐시 BAAI/bge-reranker-v2-m3 → 없으면 bi-encoder 단독 |
| 추론 단위 | 공시 1건당 `predict()` 1회 호출 |
| 응답 SLA | 건당 ≤ 500ms (CPU 기준) |
| 가중치 파일 검증 | `_is_valid_model_dir()` — config.json + model.safetensors 또는 pytorch_model.bin 모두 존재 시에만 로드 |

---

## 8. 데이터 모델 (Data Schema)

> **현재 구현**: SQLite (`data/announcements.db`)  
> **운영 확장**: PostgreSQL 전환 검토

### 8.1 announcements (공시 테이블)

```sql
CREATE TABLE announcements (
    id              INTEGER      PRIMARY KEY AUTOINCREMENT,
    source_agency   VARCHAR(50)  NOT NULL,  -- 금융위원회, 금감원 등
    category        VARCHAR(50)  NOT NULL,  -- 보도자료, 고시공고, 의결결과 등
    title           TEXT         NOT NULL,
    body_text       TEXT,
    published_at    DATETIME     NOT NULL,
    url             TEXT         NOT NULL UNIQUE,
    author_dept_raw VARCHAR(100),           -- 원문 기재 담당부서
    contact_raw     TEXT,                   -- 원문 기재 담당자/연락처
    crawled_at      DATETIME     DEFAULT CURRENT_TIMESTAMP,
    is_matched      BOOLEAN      DEFAULT 0
);
CREATE INDEX idx_ann_published ON announcements(published_at DESC);
CREATE INDEX idx_ann_agency    ON announcements(source_agency);
```

### 8.2 dept_matches (부서 매칭 결과)

```sql
CREATE TABLE dept_matches (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id     INTEGER REFERENCES announcements(id),
    final_dept          VARCHAR(100),
    confidence_score    REAL,
    needs_review        BOOLEAN DEFAULT 0,
    match_method        VARCHAR(50),        -- dense+tfidf+bm25+crossencoder
    model_version       VARCHAR(30),
    matched_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_manual_override  BOOLEAN DEFAULT 0,
    override_dept       VARCHAR(100)
);
```

### 8.3 departments (부서 목록)

```sql
CREATE TABLE departments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name   VARCHAR(100) NOT NULL UNIQUE,  -- HNG_BR_NM
    is_active   BOOLEAN DEFAULT 1,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 8.4 crawl_logs (크롤링 이력)

```sql
CREATE TABLE crawl_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agency   VARCHAR(50),
    started_at      DATETIME,
    finished_at     DATETIME,
    collected_count INTEGER,
    error_count     INTEGER,
    error_detail    TEXT
);
```

---

## 9. API 설계 (API Spec)

### 9.1 공시 목록 조회

```
GET /api/v1/announcements
Query Params:
  - source_agency: string (optional)
  - category: string (optional)
  - dept: string (optional)           ← 매칭 부서 필터
  - range: D|W|M|ALL (default: W)
  - page: int (default: 1)
  - per_page: int (default: 20)
  - min_confidence: float (optional)  ← 신뢰도 임계값 필터

Response 200:
{
  "total": 142,
  "page": 1,
  "items": [
    {
      "id": 1001,
      "source_agency": "금융위원회",
      "category": "보도자료",
      "title": "마이데이터 활용 금리인하요구 서비스...",
      "published_at": "2026-06-17T14:30:00+09:00",
      "url": "https://fsc.go.kr/...",
      "matched_dept": "디지털금융총괄과",
      "confidence_score": 0.87,
      "needs_review": false
    }
  ]
}
```

### 9.2 공시 상세 조회

```
GET /api/v1/announcements/{id}
Response 200: 공시 전체 필드 + 매칭 결과 + 원문 담당부서/연락처
```

### 9.3 부서 목록 조회

```
GET /api/v1/departments
Response 200: [{ "dept_name": "디지털금융총괄과" }, ...]
```

### 9.4 수동 매칭 재요청

```
POST /api/v1/announcements/{id}/rematch
Body: { "override_dept": "핀테크혁신과" }  ← 생략 시 모델 재추론
Response 200: 갱신된 매칭 결과
```

---

## 10. 비기능 요구사항 (Non-Functional Requirements)

| 항목 | 요구사항 |
|------|---------|
| **성능** | 공시 목록 API 응답 ≤ 200ms (DB 조회 기준) |
| **보안** | API 인증 (JWT or API Key), HTTPS 필수 |
| **로깅** | 크롤링 실패, 매칭 오류, API 오류 중앙 로그 수집 |
| **모니터링** | 크롤러 수집 건수, 매칭 성공률, 신뢰도 분포 대시보드 |
| **확장성** | 크롤링 대상 기관 추가 시 기존 코드 수정 최소화 |
| **데이터 보관** | 공시 원문 2년 보관, 크롤링 로그 6개월 보관 |
| **알림 신뢰성** | Telegram 메시지 발송 실패 시 재시도 3회 |

---

## 11. 개발 로드맵 (Milestones)

### Phase 1 — 크롤러 + 기본 피드 ✅ 완료
- [x] 금융위원회, 금감원, KoFIU, 법제처, 한국은행 크롤러 구현 및 DB 적재
- [x] FastAPI 기반 기본 API 서버 (목록/상세 조회)
- [x] 프론트엔드 메인 피드 화면 (Vanilla JS, `API_BASE: http://localhost:8000/api/v1`)
- [x] 중복 감지 (URL unique) 및 APScheduler 기반 스케줄러 설정
- [x] SQLite 데이터베이스 (`data/announcements.db`)

### Phase 2 — 부서 매칭 통합 ✅ 완료
- [x] BGE-M3 (BAAI/bge-m3) 기반 Hybrid Retrieval 매칭 서비스 구현
- [x] Cross-Encoder (BAAI/bge-reranker-v2-m3) 재순위화 통합
- [x] 두 단계 파인튜닝 파이프라인 (v4.1.ipynb) — 단일 `bge_m3_finetuned/` 경로 저장
- [x] 프론트엔드 부서 매칭 결과 UI 통합 (실제 AI 매칭 결과 노출 확인)
- [x] 신뢰도 임계값 기반 자동 확정 / 수동 검토 분류

### Phase 3 — 알림 및 고도화 (예정)
- [ ] Telegram Bot 알림 연동
- [ ] 부서 필터 / 구독 설정 기능
- [ ] 크롤링 모니터링 대시보드
- [ ] PostgreSQL 전환 (운영 환경 스케일업 시)

### Phase 4 — 안정화 및 운영 자동화 (예정)
- [ ] 모델 성능 평가 (테스트셋 기반 Top-1/Top-5 정확도 측정)
- [ ] dept.xlsx 업데이트 시 자동 모델 재학습 파이프라인
- [ ] 부서별 미확인 건수 뱃지 및 읽음 처리
- [ ] 첨부파일 다운로드 기능

---

## 12. 리스크 및 제약사항 (Risks & Constraints)

| 리스크 | 영향도 | 상태 | 대응 방안 |
|--------|--------|------|----------|
| 기관 사이트 구조 변경으로 크롤러 파싱 실패 | 중 | 진행 중 | 기관별 크롤러 독립 모듈화 + 실패 알림 |
| 부서 매칭 정확도 저하 (dept.xlsx 미갱신) | 중 | 진행 중 | 월 1회 dept.xlsx 업데이트 및 재학습 프로세스 수립 |
| GPU 없이 모델 재학습 불가 | 중 | 진행 중 | Google Colab GPU 활용 (Drive 저장 + 가중치 검증 자동화) |
| 크롤링 차단 (IP 블록, robots.txt 위반) | 높 | 진행 중 | User-Agent 설정, 요청 딜레이 준수, 필요 시 IP 로테이션 |
| 공시 본문 길이 초과로 정보 손실 | — | **해소** | BGE-M3 도입으로 최대 8192 토큰 처리 가능 |
| Colab 세션 종료로 모델 저장 실패 | 중 | **완화** | Google Drive 우선 저장 + 가중치 파일 존재 검증으로 무음 실패 방지 |
| 동일 기관 내 부서명 유사성으로 매칭 혼동 | 중 | 진행 중 | Cross-Encoder 재순위화 + 매칭 불가 임계값(0.4) + 수동 검토 큐 운영 |

---

## 13. 용어 정리 (Glossary)

| 용어 | 정의 |
|------|------|
| HNG_BR_NM | dept.xlsx 내 한글 부서명 컬럼 |
| OFWRK_NM | dept.xlsx 내 업무 설명 컬럼 |
| BGE-M3 | BAAI/bge-m3 — 570M 파라미터, 8192 토큰 지원 다국어 임베딩 모델 |
| Cross-Encoder | 쿼리-문서 쌍을 직접 입력받아 관련도 점수를 출력하는 재순위화 모델 (BAAI/bge-reranker-v2-m3) |
| Bi-Encoder | 쿼리와 문서를 각각 임베딩한 뒤 코사인 유사도로 비교하는 검색 모델 (BGE-M3) |
| Dense Score | BGE-M3 임베딩 코사인 유사도 (가중치 55%) |
| TF-IDF Score | char 2~5 gram 기반 희소 벡터 유사도 (가중치 25%) |
| BM25 Score | 토큰 기반 확률적 검색 점수 (가중치 20%) |
| CANDIDATE_K | 1단계 Hybrid Retrieval에서 수집하는 후보 수 (현재 120) |
| RERANK_TOP_K | Cross-Encoder에 넘기는 최종 후보 수 (현재 10) |
| Top-1 정확도 | 최종 예측 부서가 정답인 비율 |
| confidence | 매칭 확신도 (0~1), `sigmoid(s0)*0.7 + gap*0.3` 공식 적용 |
| needs_review | confidence < 0.4 시 true, 수동 검토 큐 대상 |
| CONFIDENCE_AUTO | 자동 확정 임계값 (0.7) |
| CONFIDENCE_REVIEW | 수동 검토 임계값 (0.4) |
| bge_m3_finetuned/ | Stage 1 도메인 적응 후 Stage 2 부서 매칭 파인튜닝 결과를 덮어쓴 최종 단일 모델 디렉터리 |
| APScheduler | 백엔드 크롤러 주기 실행에 사용하는 Python 스케줄러 라이브러리 |
| MultipleNegativesRankingLoss | 배치 내 타 샘플을 자동 negative로 활용하는 sentence-transformers 학습 손실 함수 |
