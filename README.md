---
title: DeptMatch API
emoji: 🏦
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# 금융공시 부서 자동 매칭 API

금융위원회·금감원·KoFIU·법제처·한국은행의 공시를 자동 수집하고
BGE-M3 + Cross-Encoder 모델로 담당 부서를 자동 매칭하는 FastAPI 백엔드입니다.

## 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/announcements` | 공시 목록 조회 |
| GET | `/api/v1/announcements/{id}` | 공시 상세 조회 |
| GET | `/api/v1/departments` | 부서 목록 조회 |

## 모델 아키텍처

- **임베더**: BAAI/bge-m3 (570M params, max 8192 tokens)
- **검색**: Dense(55%) + TF-IDF(25%) + BM25(20%) Hybrid Retrieval
- **재순위화**: BAAI/bge-reranker-v2-m3 Cross-Encoder
