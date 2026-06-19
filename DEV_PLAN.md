# 단계별 개발 계획서
## 금융공시 크롤링 + 부서 자동 매칭 서비스

**기준 문서**: PRD v1.0  
**작성일**: 2026-06-17  
**총 개발 기간**: 13주

---

## 전체 일정 개요

```
Week  1  2  3  4  5  6  7  8  9  10 11 12 13
──────────────────────────────────────────────
Step1 ████████████
Step2          ████████████
Step3                   ████████
Step4                         ████████
Step5                               ████████
```

| 단계 | 이름 | 기간 | 산출물 |
|------|------|------|--------|
| **Step 1** | 데이터 수집 파이프라인 | 1~3주 | 크롤러 + DB + 스케줄러 |
| **Step 2** | 부서 매칭 모델 서빙 | 3~5주 | 모델 API 서버 + 매칭 워커 |
| **Step 3** | 백엔드 API 서버 | 5~7주 | REST API + 인증 |
| **Step 4** | 프론트엔드 개발 | 7~10주 | 웹 UI + Telegram Bot |
| **Step 5** | 통합 테스트 및 운영 안정화 | 10~13주 | 전체 통합 + 모니터링 |

---

## Step 1. 데이터 수집 파이프라인 구축 (Week 1~3)

### 목표
외부 기관 공시를 DB에 신뢰성 있게 적재하는 자동화 파이프라인 완성

### 1-1. 개발 환경 및 인프라 셋업 (Week 1)

#### 작업 항목
```
[ ] Docker Compose 기반 로컬 개발 환경 구성
    - PostgreSQL 16
    - Redis (메시지 큐 용도)
    - Adminer (DB 관리 UI)

[ ] 데이터베이스 스키마 생성
    - announcements 테이블
    - dept_matches 테이블
    - departments 테이블
    - crawl_logs 테이블
    - Alembic 마이그레이션 설정

[ ] Python 프로젝트 구조 초기화
    - poetry 또는 pip-tools 의존성 관리
    - 기본 설정 파일 (config.py, .env)
    - 로깅 설정 (structlog 또는 loguru)
```

#### 디렉토리 구조
```
project/
├── crawler/
│   ├── base.py            # BaseCrawler 추상 클래스
│   ├── agencies/
│   │   ├── fsc.py         # 금융위원회
│   │   ├── fss.py         # 금융감독원
│   │   ├── kofiu.py       # 금융정보분석원
│   │   ├── moleg.py       # 법제처
│   │   └── bok.py         # 한국은행
│   └── parser.py          # HTML → 정제 텍스트 공통 유틸
├── db/
│   ├── models.py          # SQLAlchemy ORM 모델
│   ├── session.py         # DB 세션 관리
│   └── migrations/        # Alembic 마이그레이션
├── scheduler/
│   └── tasks.py           # APScheduler or Celery beat 작업 정의
├── matching/              # Step 2에서 채움
├── api/                   # Step 3에서 채움
└── docker-compose.yml
```

#### 핵심 설계 원칙
- `BaseCrawler` 추상 클래스로 기관별 크롤러를 플러그인 방식으로 확장
- 기관 추가 시 `agencies/` 하위 파일만 추가하면 스케줄러 자동 등록

---

### 1-2. 크롤러 구현 (Week 1~2)

#### BaseCrawler 인터페이스
```python
class BaseCrawler(ABC):
    agency_name: str       # "금융위원회"
    interval_hours: int    # 1 or 2
    base_url: str

    @abstractmethod
    def fetch_list(self) -> list[dict]:
        """목록 페이지에서 제목/URL/날짜 수집"""

    @abstractmethod
    def fetch_detail(self, url: str) -> dict:
        """상세 페이지에서 본문/담당부서/연락처 수집"""

    def run(self) -> int:
        """신규 건만 수집하여 DB 저장, 수집 건수 반환"""
```

#### 기관별 구현 포인트

| 기관 | 수집 방식 | 주요 파싱 포인트 |
|------|----------|----------------|
| 금융위원회 (fsc.go.kr) | requests + BeautifulSoup | 보도자료/고시공고/의결결과 게시판 분리 |
| 금융감독원 (fss.or.kr) | requests + BeautifulSoup | 카테고리별 목록 URL 패턴 확인 필요 |
| KoFIU (kofiu.go.kr) | requests + BeautifulSoup | JS 렌더링 여부 사전 확인, Playwright fallback |
| 법제처 (moleg.go.kr) | requests + BeautifulSoup | 법령해석/의견서 2개 게시판 |
| 한국은행 (bok.or.kr) | requests + BeautifulSoup | 금통위 의결 별도 카테고리 |

#### 공통 처리 로직
```python
# 중복 방지: URL unique constraint + upsert
# 신규 건 판별: 마지막 수집 published_at 이후 항목만 처리
# 본문 정제: HTML 태그 제거, 연속 공백/줄바꿈 정규화
# 담당부서 추출: "담당부서[:\s]+([가-힣]+[팀과실부처])" 패턴 정규식
# 연락처 추출: "02-\d{4}-\d{4}" 패턴 정규식
# 요청 딜레이: 기관당 1~3초 random sleep
# 에러 처리: 지수 백오프 재시도 (1s → 2s → 4s, 최대 3회)
```

#### 작업 항목
```
[ ] BaseCrawler 추상 클래스 구현
[ ] 금융위원회 크롤러 (fsc.py) — 우선순위 1
[ ] 금융감독원 크롤러 (fss.py) — 우선순위 2
[ ] HTML 정제 유틸 (parser.py)
[ ] 담당부서/연락처 정규식 추출기
[ ] 중복 감지 + DB upsert 로직
[ ] 단위 테스트: 크롤러별 파싱 정확도 검증
```

---

### 1-3. 스케줄러 및 메시지 큐 (Week 2~3)

#### 스케줄러 구성 (APScheduler)
```python
# scheduler/tasks.py
scheduler.add_job(FscCrawler().run,   'interval', hours=1, id='fsc')
scheduler.add_job(FssCrawler().run,   'interval', hours=1, id='fss')
scheduler.add_job(KofiuCrawler().run, 'interval', hours=1, id='kofiu')
scheduler.add_job(MolegCrawler().run, 'interval', hours=2, id='moleg')
scheduler.add_job(BokCrawler().run,   'interval', hours=2, id='bok')
```

#### 메시지 큐 (Redis Stream)
```
크롤러 → XADD announcements_stream {announcement_id}
매칭 워커 → XREAD 소비 후 predict_department() 호출
```

#### 작업 항목
```
[ ] APScheduler + Redis 연동 설정
[ ] 크롤러 완료 후 Redis Stream에 이벤트 발행
[ ] crawl_logs 테이블 자동 기록 (시작/종료/수집건수/오류)
[ ] 크롤링 실패 시 Slack/이메일 오류 알림 (선택)
[ ] 나머지 3개 기관 크롤러 (kofiu, moleg, bok)
```

### Step 1 완료 기준 (Definition of Done)
- [ ] 5개 기관 크롤러 모두 동작, 신규 공시 자동 DB 적재 확인
- [ ] 24시간 무중단 스케줄 실행 안정성 확인
- [ ] 중복 수집 0건 확인 (URL unique 제약 검증)
- [ ] crawl_logs 기록 정상 확인

---

## Step 2. 부서 매칭 모델 서빙 (Week 3~5)

### 목표
v3.ipynb의 Hybrid Retrieval 모델을 운영 가능한 API 서비스로 전환하고, 크롤링된 공시에 부서를 자동 매칭

### 2-1. 모델 학습 재현 및 검증 (Week 3)

#### 작업 항목
```
[ ] v3.ipynb 로컬/Colab 실행 환경 재현
    - 의존성: sentence-transformers, rank_bm25, python-docx, openpyxl
    - 학습 데이터: 업무담당규정.docx, dept.xlsx 경로 확인

[ ] Stage 1 학습 실행
    - 업무담당규정.docx → self-positive 학습쌍 생성
    - jhgan/ko-sroberta-multitask 도메인 적응
    - 결과: stage1_domain_retriever/ 저장

[ ] Stage 2 학습 실행
    - dept.xlsx → 부서별 5행 chunk 생성
    - OFWRK_NM → chunk 매핑 학습
    - 결과: stage2_dept_retriever/ 저장

[ ] 기존 query1~3.txt로 추론 테스트 → 예상 부서 검증
[ ] 학습된 모델 파일 버전 태깅 (예: v3_20260617)
```

#### 모델 성능 기준 검증
```python
# 테스트 케이스 (query1~3 기준 수동 검증)
query1 → 예상: 디지털금융총괄과 or 핀테크혁신과 (혁신금융서비스)
query2 → 예상: 서민금융과 (채권매각/연체채무)
query3 → 예상: 금융소비자정책과 (금융교육)
```

---

### 2-2. 모델 FastAPI 서버 구현 (Week 4)

#### 디렉토리 구조
```
matching/
├── model.py          # 모델 로딩 + predict_department() 래퍼
├── server.py         # FastAPI 앱 정의
├── schemas.py        # Pydantic 입출력 스키마
└── worker.py         # Redis Stream 소비 워커
```

#### API 엔드포인트
```python
# POST /match
# Request
{
  "text": "마이데이터 활용 금리인하요구 서비스 혁신금융 3건 신규 지정...",
  "top_n": 5
}

# Response
{
  "final_department": "디지털금융총괄과",
  "confidence_score": 0.87,
  "top5_candidates": [
    {"rank": 1, "dept": "디지털금융총괄과", "score": 0.87},
    {"rank": 2, "dept": "핀테크혁신과", "score": 0.71},
    {"rank": 3, "dept": "전자금융과", "score": 0.65},
    {"rank": 4, "dept": "IT금융정보보호팀", "score": 0.60},
    {"rank": 5, "dept": "금융혁신지원실", "score": 0.54}
  ],
  "processing_time_ms": 118,
  "model_version": "v3_20260617"
}
```

#### 모델 서버 설계 포인트
```python
# 앱 시작 시 1회 로드 (startup 이벤트)
@app.on_event("startup")
async def load_model():
    app.state.embedder = SentenceTransformer(STAGE2_MODEL_DIR)
    app.state.corpus_embs = ...   # pre-computed embeddings
    app.state.tfidf = ...
    app.state.bm25 = ...

# 신뢰도 fallback 처리
if result["confidence_score"] < 0.4:
    result["final_department"] = None
    result["needs_manual_review"] = True
```

#### 작업 항목
```
[ ] model.py: predict_department() 함수 v3.ipynb에서 추출/정리
[ ] schemas.py: MatchRequest / MatchResponse Pydantic 모델
[ ] server.py: FastAPI 앱 + /match + /health 엔드포인트
[ ] Docker 이미지 빌드 (python:3.11-slim 기반)
[ ] /match 엔드포인트 부하 테스트 (목표: ≤500ms/건)
```

---

### 2-3. 매칭 워커 구현 (Week 4~5)

#### 워커 동작 방식
```
Redis Stream 'announcements_stream' 구독
  ↓
announcement_id 수신
  ↓
announcements 테이블에서 body_text 조회
  ↓
POST /match 호출 (또는 직접 predict_department 호출)
  ↓
dept_matches 테이블 INSERT
  ↓
announcements.is_matched = TRUE 업데이트
  ↓
신뢰도 < 0.4이면 → manual_review_queue에 추가
```

#### 작업 항목
```
[ ] worker.py: Redis Stream XREAD 루프 구현
[ ] 매칭 결과 dept_matches 테이블 저장
[ ] 신뢰도 임계값(0.4) 미만 처리 로직
[ ] 배치 처리: 백로그 누적 시 batch_predict() 활용
[ ] 워커 재시작 시 미처리 건 자동 재처리 (XPENDING 활용)
[ ] 통합 테스트: 크롤러 수집 → 워커 매칭 → DB 저장 E2E 확인
```

### Step 2 완료 기준 (Definition of Done)
- [ ] 모델 API /match 응답 시간 ≤ 500ms (CPU 환경)
- [ ] query1~3 예상 부서 정확히 반환 확인
- [ ] 크롤러 수집 후 5분 이내 매칭 결과 DB 적재 확인
- [ ] 신뢰도 < 0.4 건 manual_review 처리 확인
- [ ] Docker Compose로 모델 서버 단독 기동 가능

---

## Step 3. 백엔드 API 서버 개발 (Week 5~7)

### 목표
프론트엔드와 외부 연동이 가능한 REST API 서버 완성

### 3-1. API 서버 기본 구조 (Week 5~6)

#### 디렉토리 구조
```
api/
├── main.py            # FastAPI 앱 엔트리포인트
├── routers/
│   ├── announcements.py
│   ├── departments.py
│   └── match.py
├── schemas/
│   ├── announcement.py
│   └── department.py
├── services/
│   ├── announcement_service.py
│   └── match_service.py
├── auth/
│   └── api_key.py     # API Key 인증 미들웨어
└── dependencies.py    # DB 세션 등 공통 의존성
```

#### 구현할 엔드포인트

**공시 목록 조회**
```
GET /api/v1/announcements
Query: source_agency, category, dept, range(D|W|M|ALL),
       page, per_page, min_confidence
Response: { total, page, items: [...] }
```

**공시 상세 조회**
```
GET /api/v1/announcements/{id}
Response: 전체 필드 + 매칭 Top-5 + 원문 담당부서/연락처
```

**부서 목록 조회**
```
GET /api/v1/departments
Response: [{ dept_name, is_active }]
```

**수동 매칭 재요청**
```
POST /api/v1/announcements/{id}/rematch
Body: { "override_dept": "핀테크혁신과" }  (생략 시 모델 재추론)
Response: 갱신된 매칭 결과
```

**수동 검토 큐 조회** *(운영자용)*
```
GET /api/v1/review-queue
Response: 신뢰도 < 0.4인 미처리 공시 목록
```

#### 작업 항목
```
[ ] FastAPI 앱 초기화 + CORS 설정
[ ] API Key 인증 미들웨어 (X-API-Key 헤더)
[ ] GET /announcements 구현 (필터 + 페이지네이션)
[ ] GET /announcements/{id} 구현
[ ] GET /departments 구현
[ ] POST /announcements/{id}/rematch 구현
[ ] GET /review-queue 구현
[ ] OpenAPI 문서 자동 생성 확인 (/docs)
```

---

### 3-2. 성능 최적화 및 보안 (Week 6~7)

#### DB 쿼리 최적화
```sql
-- 자주 사용되는 필터 조합에 인덱스 추가
CREATE INDEX idx_ann_agency_published ON announcements(source_agency, published_at DESC);
CREATE INDEX idx_ann_published_range ON announcements(published_at DESC);
CREATE INDEX idx_match_dept ON dept_matches(final_dept);
CREATE INDEX idx_match_confidence ON dept_matches(confidence_score);

-- 목록 조회용 뷰 (announcements + dept_matches JOIN)
CREATE VIEW v_announcements_with_match AS
  SELECT a.*, dm.final_dept, dm.confidence_score, dm.top5_json
  FROM announcements a
  LEFT JOIN dept_matches dm ON a.id = dm.announcement_id;
```

#### 보안
```
- API Key 인증 (X-API-Key 헤더)
- Rate Limiting: 100 req/min per API Key
- HTTPS 강제 (nginx 리버스 프록시)
- SQL Injection 방지: SQLAlchemy ORM 사용 (raw query 금지)
- 입력값 검증: Pydantic 모델로 모든 쿼리 파라미터 타입 검증
```

#### 작업 항목
```
[ ] 쿼리 성능 검증 (목록 조회 ≤ 200ms)
[ ] API Key 발급/관리 테이블 추가
[ ] Rate Limiting 미들웨어 (slowapi)
[ ] 응답 캐싱: 부서 목록 (5분 캐시, Redis)
[ ] 전체 API 엔드포인트 통합 테스트 (pytest)
[ ] Postman Collection 또는 HTTP 파일 작성
```

### Step 3 완료 기준 (Definition of Done)
- [ ] 전체 엔드포인트 정상 동작 및 Postman 검증 완료
- [ ] 목록 조회 API 응답 ≤ 200ms (인덱스 적용 기준)
- [ ] API Key 없는 요청 401 반환 확인
- [ ] OpenAPI 문서(/docs) 자동 생성 확인
- [ ] pytest 기반 API 통합 테스트 80% 이상 커버리지

---

## Step 4. 프론트엔드 개발 (Week 7~10)

### 목표
담당자가 공시와 매칭 부서를 한 화면에서 확인하고 필터링할 수 있는 웹 UI 완성

### 4-1. 기술 스택 및 초기 설정 (Week 7)

```
프레임워크: Next.js 14 (App Router)
스타일링:   Tailwind CSS + shadcn/ui
상태관리:   Zustand (클라이언트 상태)
데이터 페칭: TanStack Query (서버 상태)
배포:       Vercel 또는 Nginx + Docker
```

#### 프로젝트 구조
```
frontend/
├── app/
│   ├── page.tsx              # 메인 피드
│   ├── announcements/
│   │   └── [id]/page.tsx     # 상세 페이지
│   └── dashboard/page.tsx    # 부서별 대시보드
├── components/
│   ├── AnnouncementCard.tsx  # 공시 카드 (핵심)
│   ├── DeptMatchBadge.tsx    # 부서 매칭 + 신뢰도 바
│   ├── FilterBar.tsx         # 기관/기간/부서 필터
│   ├── AgencyTabs.tsx        # 기관 탭
│   └── ReviewAlert.tsx       # 수동 검토 경고 배지
├── hooks/
│   ├── useAnnouncements.ts
│   └── useDepartments.ts
└── lib/
    └── api.ts                # API 클라이언트
```

#### 작업 항목
```
[ ] Next.js 프로젝트 초기화 + Tailwind + shadcn/ui 설정
[ ] API 클라이언트 (lib/api.ts) 타입 정의
[ ] TanStack Query 설정 및 커스텀 훅 작성
[ ] 환경변수 설정 (NEXT_PUBLIC_API_URL)
```

---

### 4-2. 핵심 컴포넌트 구현 (Week 8~9)

#### AnnouncementCard (공시 카드)
```tsx
// 표시 정보
// - 기관 배지 (색상 구분: 금융위=파랑, 금감원=초록, ...)
// - 카테고리 태그
// - 제목 (2줄 말줄임)
// - 게시일시 (상대시간: "3시간 전")
// - 매칭 부서 + 신뢰도 바
// - 후보 부서 2~3개 (작은 글씨)
// - 수동 검토 필요 경고 (신뢰도 < 40%)
// - [원문 보기] 버튼
```

#### DeptMatchBadge (부서 매칭 시각화)
```tsx
// 높음 (80%+): 초록 progress bar
// 보통 (60~79%): 노랑 progress bar
// 낮음 (40~59%): 주황 progress bar
// 검토 필요 (<40%): 빨강 + "⚠️ 수동 검토" 텍스트
```

#### FilterBar (필터 영역)
```tsx
// - 기관 탭 (전체/금융위/금감원/KoFIU/법제처/한국은행)
//   각 탭에 미확인 건수 뱃지
// - 기간 필터 (D/W/M/ALL) — 토글 버튼 그룹
// - 부서 필터 드롭다운 (검색 가능, 내 부서 저장 기능)
// - 카테고리 필터 드롭다운
// - 신뢰도 임계값 슬라이더 (0~100%)
```

#### 작업 항목
```
[ ] AnnouncementCard 컴포넌트 구현
[ ] DeptMatchBadge 컴포넌트 (신뢰도 색상 분기)
[ ] FilterBar 컴포넌트 (기관탭 + 기간 + 부서 드롭다운)
[ ] 공시 목록 페이지 (무한 스크롤 or 페이지네이션)
[ ] 공시 상세 페이지 (본문 + Top-5 후보 바 차트)
[ ] 부서별 대시보드 페이지 (내 부서 필터 저장)
[ ] 로딩 스켈레톤 UI
[ ] 빈 상태 처리 ("조건에 맞는 공시가 없습니다")
```

---

### 4-3. Telegram Bot 연동 (Week 9~10)

#### Bot 동작 방식
```
신규 공시 DB 적재 + 매칭 완료
  ↓
Redis Stream 'telegram_stream' 이벤트 발행
  ↓
Telegram Bot 워커가 소비
  ↓
구독 조건(기관, 부서) 체크
  ↓
조건 만족 시 메시지 발송

메시지 형식:
📢 [금융위원회] 보도자료
제목: 마이데이터 활용 금리인하요구 서비스 혁신금융 3건 지정
매칭부서: 디지털금융총괄과 (87%)
게시: 2026-06-17 14:30
🔗 https://fsc.go.kr/...
```

#### Bot 명령어
```
/start       - 구독 시작 안내
/subscribe   - 구독 조건 설정 (기관, 부서)
/unsubscribe - 구독 해제
/status      - 현재 구독 상태 확인
/latest      - 최신 5건 조회
```

#### 작업 항목
```
[ ] python-telegram-bot 라이브러리 설정
[ ] Bot 워커 (telegram_worker.py) 구현
[ ] 구독 설정 테이블 (telegram_subscriptions) 추가
[ ] /subscribe 명령어 + 조건 저장 로직
[ ] 신뢰도 < 40% 건 알림 제외 옵션
[ ] 발송 실패 시 재시도 로직 (최대 3회)
[ ] 프론트엔드에서 Telegram 구독 링크 노출
```

### Step 4 완료 기준 (Definition of Done)
- [ ] 공시 카드 + 부서 매칭 신뢰도 바 정상 노출 확인
- [ ] 기관/기간/부서 필터 정상 동작 확인
- [ ] 공시 상세 페이지 본문 + Top-5 후보 표시 확인
- [ ] 모바일 반응형 레이아웃 확인 (iPhone 14 기준)
- [ ] Telegram Bot 신규 공시 알림 발송 확인
- [ ] Lighthouse 성능 점수 ≥ 85

---

## Step 5. 통합 테스트 및 운영 안정화 (Week 10~13)

### 목표
전체 시스템 E2E 검증 + 모델 성능 측정 + 운영 모니터링 체계 구축

### 5-1. E2E 통합 테스트 (Week 10~11)

#### 테스트 시나리오
```
시나리오 1: 정상 수집 플로우
  1. 크롤러 수동 실행
  2. 신규 공시 DB 적재 확인
  3. 매칭 워커 자동 실행
  4. dept_matches 적재 확인
  5. API 목록 조회 → 공시 + 부서 노출 확인
  6. Telegram 알림 수신 확인

시나리오 2: 중복 수집 방지
  1. 같은 공시 2회 크롤링
  2. DB 중복 적재 0건 확인

시나리오 3: 신뢰도 낮은 건 처리
  1. 관련성 낮은 본문 매칭 요청
  2. 신뢰도 < 0.4 → needs_manual_review: true 확인
  3. review-queue API에서 해당 건 노출 확인

시나리오 4: 크롤러 장애 복구
  1. 기관 사이트 접근 불가 시뮬레이션
  2. 에러 로그 기록 확인
  3. 다음 스케줄 주기에 자동 재시도 확인

시나리오 5: 수동 매칭 재요청
  1. 잘못 매칭된 공시 선택
  2. /rematch API 호출 (override_dept 지정)
  3. dept_matches 갱신 확인
  4. 프론트엔드 갱신 표시 확인
```

#### 작업 항목
```
[ ] pytest E2E 테스트 스위트 작성
[ ] 각 시나리오 자동화 테스트 구현
[ ] 부하 테스트: API 동시 50 요청 → p95 응답 ≤ 500ms
[ ] 크롤러 72시간 연속 실행 안정성 테스트
```

---

### 5-2. 모델 성능 평가 및 개선 (Week 11~12)

#### 평가 데이터셋 구성
```
- 수동 레이블링: 실제 공시 50건에 대한 담당 부서 정답 레이블
- 평가 지표: Top-1 정확도, Top-5 정확도, 평균 신뢰도 점수
- 목표: Top-1 ≥ 80%, Top-5 ≥ 95%
```

#### 모델 개선 포인트 (목표 미달 시)
```
A. 본문 전처리 개선
   - 공시 앞 512 토큰 → 제목 + 앞 300토큰 혼합 방식 시도
   - 원문 기재 담당부서 텍스트를 추가 힌트로 활용

B. 앙상블 가중치 튜닝
   - dense_weight / tfidf_weight / bm25_weight 그리드 서치
   - 현재 기본값 → 최적값 탐색

C. Stage 2 학습 데이터 보강
   - 실제 공시-부서 매핑 레이블 데이터를 추가 학습쌍으로 활용
   - Negative 샘플 전략 개선
```

#### 모델 재학습 파이프라인 자동화
```
dept.xlsx 업데이트 감지
  ↓
Stage 2 재학습 자동 트리거 (주 1회 배치)
  ↓
신규 모델 평가 (성능 회귀 없는지 확인)
  ↓
symlink 교체로 무중단 모델 업데이트
  ↓
model_version 업데이트 기록
```

#### 작업 항목
```
[ ] 평가 데이터셋 50건 수동 레이블링
[ ] 모델 성능 평가 스크립트 작성
[ ] Top-1 / Top-5 정확도 측정 및 결과 문서화
[ ] 미달 시 개선안 A/B/C 중 적용
[ ] dept.xlsx 변경 감지 + 재학습 배치 스크립트
[ ] 모델 버전 관리 체계 수립
```

---

### 5-3. 운영 모니터링 체계 구축 (Week 12~13)

#### 모니터링 대시보드 (Grafana 또는 내장)
```
패널 1: 기관별 시간당 수집 건수 (시계열 그래프)
패널 2: 크롤링 성공률 (목표: ≥ 99%)
패널 3: 매칭 신뢰도 분포 히스토그램
패널 4: 수동 검토 큐 누적 건수
패널 5: API 응답 시간 p50/p95
패널 6: 모델 서버 메모리/CPU 사용률
```

#### 알림 설정
```
- 크롤러 연속 3회 실패 → 즉시 알림 (Slack/이메일)
- 매칭 워커 5분 이상 중단 → 즉시 알림
- 수동 검토 큐 50건 초과 → 경고 알림
- API 오류율 > 1% → 경고 알림
```

#### 배포 구성 (Docker Compose → 운영 환경)
```yaml
services:
  postgres:    # DB
  redis:       # 메시지 큐 + 캐시
  crawler:     # 크롤러 + 스케줄러
  matcher:     # 모델 서버 (FastAPI)
  worker:      # 매칭 워커 + Telegram 워커
  api:         # REST API 서버 (FastAPI)
  frontend:    # Next.js (또는 Vercel 배포)
  nginx:       # 리버스 프록시 + HTTPS
```

#### 운영 문서 작성
```
[ ] 서비스 아키텍처 다이어그램
[ ] 크롤러 추가 가이드 (신규 기관 온보딩)
[ ] 모델 재학습 운영 절차서
[ ] 장애 대응 런북 (Runbook)
[ ] API 사용 가이드 (내부 배포용)
```

#### 작업 항목
```
[ ] Prometheus + Grafana 또는 내장 지표 수집 설정
[ ] 크롤러/워커/API 핵심 지표 계측 코드 추가
[ ] 알림 임계값 설정 및 수신 채널 연결
[ ] Docker Compose 운영 배포 파일 최종화
[ ] 전체 운영 문서 작성
[ ] 파일럿 운영 (내부 사용자 3~5명 대상, 2주)
```

### Step 5 완료 기준 (Definition of Done)
- [ ] E2E 시나리오 5개 전부 통과
- [ ] Top-1 정확도 ≥ 80% 달성 확인
- [ ] 모니터링 대시보드 핵심 지표 6개 정상 표시
- [ ] 크롤러 72시간 무중단 안정 운영 확인
- [ ] 운영 문서 4종 완성
- [ ] 내부 파일럿 사용자 피드백 수렴 및 우선순위 버그 수정

---

## 기술 스택 요약

| 영역 | 기술 |
|------|------|
| 크롤러 | Python, requests, BeautifulSoup4, Playwright (JS렌더링 fallback) |
| 스케줄러 | APScheduler |
| 메시지 큐 | Redis Stream |
| DB | PostgreSQL 16 + SQLAlchemy + Alembic |
| 모델 | SentenceTransformer (jhgan/ko-sroberta-multitask), TF-IDF, BM25 |
| 모델 서버 | FastAPI + uvicorn |
| API 서버 | FastAPI + uvicorn + slowapi |
| 프론트엔드 | Next.js 14, Tailwind CSS, shadcn/ui, TanStack Query |
| 알림 | python-telegram-bot |
| 컨테이너 | Docker + Docker Compose |
| 리버스 프록시 | Nginx |
| 모니터링 | Prometheus + Grafana (또는 내장 지표 API) |

---

## 리스크 및 의존성

| 리스크 | 발생 단계 | 대응 |
|--------|----------|------|
| 기관 사이트 JS 렌더링 (크롤러 파싱 실패) | Step 1 | Playwright fallback 구현 |
| GPU 미확보로 모델 재학습 지연 | Step 2 | Google Colab 즉시 사용 가능, 사내 GPU 병행 확보 |
| Top-1 정확도 80% 미달 | Step 5 | 평가 후 개선안 A/B/C 순차 적용, 일정 1주 예비 |
| dept.xlsx 부서 정보 미갱신 | 운영 전반 | Step 5에서 자동화 파이프라인 구축으로 해소 |
| 기관 사이트 구조 변경 | 운영 전반 | 기관별 크롤러 독립 모듈 + 실패 알림으로 빠른 수정 |
