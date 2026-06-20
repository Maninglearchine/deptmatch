"""
프로덕션 부서 매칭 서비스
Pipeline: BGE-M3 Hybrid Retrieval → Cross-Encoder Re-ranking → top-1

Stage 1 (Retrieval): Dense(BGE-M3, 55%) + TF-IDF(25%) + BM25(20%), top-CANDIDATE_K
Stage 2 (Re-rank)  : BAAI/bge-reranker-v2-m3, top-RERANK_TOP_K → top-1
"""
import re
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

from ..config import settings

logger = logging.getLogger(__name__)

DENSE_WEIGHT    = 0.55
TFIDF_WEIGHT    = 0.25
BM25_WEIGHT     = 0.20
CANDIDATE_K     = 120   # 1단계 bi-encoder 후보 수
RERANK_TOP_K    = 10    # 2단계 cross-encoder에 넘길 후보 수
DEPT_CHUNK_SIZE = 5


def _clean(x) -> str:
    return re.sub(r'\s+', ' ', str(x) if x else '').strip()


def _tokenize(text: str) -> list:
    return re.findall(r'[가-힣A-Za-z0-9]+', text.lower())


def _minmax(x: np.ndarray) -> np.ndarray:
    r = x.max() - x.min()
    return (x - x.min()) / (r + 1e-12)


def _topk(scores: np.ndarray, k: int) -> np.ndarray:
    k = min(k, len(scores))
    return np.argsort(scores)[-k:][::-1]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-float(x)))


_DEPT_HINT_RE = re.compile(r'담당\s*(부서|과|팀|실|국|원|관|처)', re.UNICODE)


def preprocess(text: str) -> str:
    """BGE-M3 (max 8192 tokens) — 길이 제한 없이 전체 본문 구조화."""
    if not text or not text.strip():
        return ""
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    title = lines[0] if lines else ""
    hints = [ln for ln in lines[1:] if _DEPT_HINT_RE.search(ln)][:3]
    body_lines = [ln for ln in lines[1:] if ln not in hints]
    body = ' '.join(body_lines)
    return ' '.join(p for p in [title] + hints + [body] if p)


class DeptMatcher:
    def __init__(self):
        self._embedder: SentenceTransformer | None = None
        self._reranker: CrossEncoder | None = None
        self._corpus_df: pd.DataFrame | None = None
        self._corpus_embs: np.ndarray | None = None
        self._tfidf: TfidfVectorizer | None = None
        self._tfidf_mat = None
        self._bm25: BM25Okapi | None = None
        self._ready = False

    # ------------------------------------------------------------------ #
    # 모델 로드                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_valid_model_dir(path: Path) -> bool:
        """config.json + 가중치 파일이 모두 있는 경우에만 True."""
        if not path.exists():
            return False
        if not (path / "config.json").exists():
            return False
        weight_files = ["model.safetensors", "pytorch_model.bin"]
        return any((path / w).exists() for w in weight_files)

    def _load_embedder(self) -> SentenceTransformer:
        for model_path in [settings.MODEL_DIR, settings.STAGE1_MODEL_DIR]:
            p = Path(model_path)
            if self._is_valid_model_dir(p):
                logger.info("로컬 임베더 로드: %s", model_path)
                return SentenceTransformer(str(p), device="cpu")
            if p.exists():
                logger.warning("모델 디렉터리 불완전 (가중치 없음), 건너뜀: %s", model_path)
        logger.info("BAAI/bge-m3 로드 (HF 캐시 또는 최초 다운로드)")
        # max_seq_length 설정 없음 — bge-m3 기본값(8192) 그대로 사용
        return SentenceTransformer("BAAI/bge-m3", device="cpu")

    def _load_reranker(self) -> "CrossEncoder | None":
        try:
            local = Path(settings.RERANKER_DIR)
            if local.exists() and (local / "config.json").exists():
                logger.info("로컬 reranker 로드: %s", local)
                return CrossEncoder(str(local))
            logger.info("BAAI/bge-reranker-v2-m3 다운로드 (최초 1회)")
            return CrossEncoder("BAAI/bge-reranker-v2-m3")
        except Exception as exc:
            logger.warning("reranker 로드 실패 → bi-encoder 단독 사용: %s", exc)
            return None

    # ------------------------------------------------------------------ #
    # 코퍼스 구성                                                          #
    # ------------------------------------------------------------------ #

    def _build_corpus(self) -> pd.DataFrame:
        dept_df = pd.read_excel(settings.DEPT_EXCEL)
        dept_df = dept_df[["HNG_BR_NM", "OFWRK_NM"]].copy()
        dept_df["HNG_BR_NM"] = dept_df["HNG_BR_NM"].apply(_clean)
        dept_df["OFWRK_NM"]  = dept_df["OFWRK_NM"].apply(_clean)
        dept_df = (
            dept_df
            .replace({"": np.nan, "nan": np.nan})
            .dropna(subset=["HNG_BR_NM", "OFWRK_NM"])
            .reset_index(drop=True)
        )

        rows, chunk_no = [], 0
        for dept, g in dept_df.groupby("HNG_BR_NM", sort=False):
            for start in range(0, len(g), DEPT_CHUNK_SIZE):
                part  = g.iloc[start:start + DEPT_CHUNK_SIZE]
                works = part["OFWRK_NM"].tolist()
                text  = (
                    f"[부서명] {dept}\n[담당업무]\n"
                    + "\n".join(f"- {w}" for w in works)
                )
                rows.append({"HNG_BR_NM": dept, "text": text,
                              "chunk_id": f"dept_chunk_{chunk_no}"})
                chunk_no += 1
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ #
    # 초기화                                                               #
    # ------------------------------------------------------------------ #

    def load(self):
        logger.info("DeptMatcher 초기화 중...")
        self._embedder = self._load_embedder()
        self._reranker = self._load_reranker()
        self._corpus_df = self._build_corpus()

        texts = self._corpus_df["text"].tolist()

        self._corpus_embs = self._embedder.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        norms = np.linalg.norm(self._corpus_embs, axis=1, keepdims=True)
        self._corpus_embs /= norms + 1e-12

        self._tfidf = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=1
        )
        self._tfidf_mat = self._tfidf.fit_transform(texts)
        self._bm25 = BM25Okapi([_tokenize(t) for t in texts])

        self._ready = True
        reranker_status = "활성" if self._reranker else "비활성(bi-encoder 단독)"
        logger.info(
            "DeptMatcher 준비 완료: %d chunks | reranker=%s",
            len(texts), reranker_status,
        )

    # ------------------------------------------------------------------ #
    # 예측                                                                 #
    # ------------------------------------------------------------------ #

    def predict(self, text: str) -> dict:
        if not self._ready:
            raise RuntimeError("DeptMatcher.load() 먼저 호출 필요")

        query = preprocess(text)
        if not query:
            return {"dept": None, "confidence": 0.0, "needs_review": True}

        # ── 1단계: Hybrid bi-encoder retrieval ─────────────────────────
        q_emb = self._embedder.encode([query], convert_to_numpy=True)
        q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-12

        dense = self._corpus_embs @ q_emb[0]
        tfidf = (self._tfidf_mat @ self._tfidf.transform([query]).T).toarray().ravel()
        bm25  = np.asarray(self._bm25.get_scores(_tokenize(query)))

        cand = np.unique(np.concatenate([
            _topk(dense, CANDIDATE_K),
            _topk(tfidf, CANDIDATE_K),
            _topk(bm25,  CANDIDATE_K),
        ]))

        hybrid = (
            DENSE_WEIGHT * _minmax(dense[cand])
            + TFIDF_WEIGHT * _minmax(tfidf[cand])
            + BM25_WEIGHT  * _minmax(bm25[cand])
        )

        order    = np.argsort(hybrid)[::-1][:RERANK_TOP_K]
        top_rows = self._corpus_df.iloc[cand[order]].copy()
        top_rows["bi_score"] = hybrid[order]

        # ── 2단계: Cross-encoder re-ranking ─────────────────────────────
        if self._reranker is not None:
            pairs        = [(query, row["text"]) for _, row in top_rows.iterrows()]
            cross_scores = self._reranker.predict(pairs)
            top_rows["cross_score"] = cross_scores

            best_idx   = int(np.argmax(cross_scores))
            sorted_cs  = np.sort(cross_scores)[::-1]

            # sigmoid 정규화 후 gap 기반 confidence
            s0 = _sigmoid(sorted_cs[0])
            s1 = _sigmoid(sorted_cs[1]) if len(sorted_cs) > 1 else 0.0
            gap = s0 - s1
            confidence = float(np.clip(s0 * 0.7 + gap * 0.3, 0.0, 1.0))
        else:
            # reranker 미사용 시 bi-encoder top-1 그대로
            best_idx   = 0
            t0 = float(top_rows.iloc[0]["bi_score"])
            t1 = float(top_rows.iloc[1]["bi_score"]) if len(top_rows) > 1 else 0.0
            gap = t0 - t1
            confidence = float(np.clip(t0 * 0.7 + gap * 0.3, 0.0, 1.0))

        top1_dept  = str(top_rows.iloc[best_idx]["HNG_BR_NM"])
        confidence = round(confidence, 4)

        return {
            "dept":         top1_dept,
            "confidence":   confidence,
            "needs_review": confidence < settings.CONFIDENCE_REVIEW,
        }


_matcher: DeptMatcher | None = None
_matcher_lock = __import__("threading").Lock()


def get_matcher() -> DeptMatcher:
    global _matcher
    with _matcher_lock:
        if _matcher is None:
            _matcher = DeptMatcher()
            _matcher.load()
    return _matcher
