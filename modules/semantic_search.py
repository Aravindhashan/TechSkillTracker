"""Semantic retrieval over live job postings.

The pipeline is deliberately small and dependency-tolerant:

1. embed each posting (title, company, location, skills, description) with
   ``sentence-transformers``
2. retrieve candidates with FAISS when installed, otherwise a NumPy cosine
   scan
3. optionally rerank the shortlist with a cross-encoder
4. fall back to a lexical overlap search when no model can be loaded

Nothing here touches salary; search and ROI are demand-only signals.
"""

from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache
from typing import Any, Callable, Iterable

import numpy as np

DEFAULT_MODEL_NAME = os.getenv("SEMANTIC_SEARCH_MODEL", "all-MiniLM-L6-v2")
DEFAULT_RERANK_MODEL = os.getenv(
    "SEMANTIC_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
DEFAULT_CACHE_PATH = os.path.join("data", "semantic_index.npz")
MAX_DESCRIPTION_CHARS = 1500

Embedder = Callable[[list[str]], np.ndarray]


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------


def posting_text(record: dict[str, Any]) -> str:
    """Flatten one posting into the text that gets embedded."""
    skills = record.get("skills") or []
    if isinstance(skills, str):
        skills = [skills]
    description = str(record.get("description") or "")[:MAX_DESCRIPTION_CHARS]
    # Title first for exact-title matches, description next so it survives the
    # model's 256-token window; company/location are short and go last.
    parts = [
        str(record.get("title") or ""),
        description,
        " ".join(str(skill) for skill in skills if skill),
        str(record.get("company") or ""),
        str(record.get("location") or ""),
    ]
    return " ".join(part for part in parts if part).strip()


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.]+", (text or "").lower())
        if len(token) > 1 or token in {"c", "r"}
    }


def _normalise_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype="float32")
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _records_signature(records: list[dict], texts: list[str], embedder_key: str) -> str:
    digest = hashlib.sha1()
    digest.update(embedder_key.encode("utf-8"))
    for record, text in zip(records, texts):
        digest.update(str(record.get("job_id") or "").encode("utf-8"))
        digest.update(str(record.get("last_seen") or record.get("posted_at") or "").encode("utf-8"))
        digest.update(hashlib.sha1(text.encode("utf-8")).digest())
    return digest.hexdigest()


def corpus_signature(records: list[dict]) -> str:
    """Content-based signature for caching an index outside the engine."""
    records = [record for record in records if record.get("job_id")]
    texts = [posting_text(record) for record in records]
    return _records_signature(records, texts, "corpus")


# ---------------------------------------------------------------------------
# Model loading (lazy, cached, optional)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=2)
def _load_sentence_transformer(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


@lru_cache(maxsize=2)
def _load_cross_encoder(name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(name)


def semantic_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


def retrieval_available() -> str:
    """Name the retrieval backend that will be used ("faiss" or "numpy")."""
    try:
        import faiss  # noqa: F401

        return "faiss"
    except Exception:
        return "numpy"


# ---------------------------------------------------------------------------
# Lexical fallback
# ---------------------------------------------------------------------------


def lexical_search(
    records: list[dict], query: str, top_k: int = 10
) -> list[dict[str, Any]]:
    """Token-overlap search used when embeddings are unavailable."""
    query_tokens = _tokens(query)
    if not query_tokens or not records:
        return []

    scored: list[tuple[float, dict]] = []
    for record in records:
        text_tokens = _tokens(posting_text(record))
        overlap = query_tokens & text_tokens
        if not overlap:
            continue
        score = len(overlap) / len(query_tokens)
        if query_tokens & _tokens(str(record.get("title") or "")):
            score += 0.25
        scored.append((score, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [_result(record, score) for score, record in scored[:top_k]]


def _result(
    record: dict,
    score: float,
    semantic_score: float | None = None,
    rerank_score: float | None = None,
) -> dict[str, Any]:
    description = str(record.get("description") or "")
    return {
        "job_id": record.get("job_id"),
        "title": record.get("title"),
        "company": record.get("company"),
        "location": record.get("location"),
        "posted_at": record.get("posted_at"),
        "url": record.get("url"),
        "skills": list(record.get("skills") or []),
        "description": description[:400],
        "score": round(float(score), 4),
        "semantic_score": round(float(score if semantic_score is None else semantic_score), 4),
        "rerank_score": None if rerank_score is None else round(float(rerank_score), 4),
    }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SemanticSearchEngine:
    """Embed, index, retrieve, and optionally rerank a posting corpus."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        reranker: Any | None = None,
        cache_path: str | os.PathLike | None = DEFAULT_CACHE_PATH,
        model_name: str = DEFAULT_MODEL_NAME,
        rerank_model: str = DEFAULT_RERANK_MODEL,
        allow_models: bool = True,
    ):
        self.embedder = embedder
        self._custom_embedder = embedder is not None
        self.reranker = reranker
        self.cache_path = os.fspath(cache_path) if cache_path else None
        self.model_name = model_name
        self.rerank_model = rerank_model
        self.allow_models = allow_models

        self.records: list[dict] = []
        self.texts: list[str] = []
        self.vectors: np.ndarray | None = None
        self._faiss_index = None
        self._signature: str | None = None
        self._embedder_failed = False
        self._reranker_failed = False

    # -- building -----------------------------------------------------------

    def build(self, records: Iterable[dict], force: bool = False) -> "SemanticSearchEngine":
        records = [record for record in records if record.get("job_id")]
        self.records = records
        self.texts = [posting_text(record) for record in records]
        if not records:
            self.vectors = None
            self._faiss_index = None
            self._signature = None
            return self

        signature = _records_signature(records, self.texts, self._embedder_key())
        if not force and signature == self._signature and self.vectors is not None:
            return self
        if not force and self._load_cache(signature):
            self._build_faiss()
            self._signature = signature
            return self

        embedded = self._embed(self.texts)
        if embedded is None:
            self.vectors = None
            self._faiss_index = None
            self._signature = signature
            return self

        self.vectors = _normalise_rows(embedded)
        self._build_faiss()
        self._save_cache(signature)
        self._signature = signature
        return self

    def _embedder_key(self) -> str:
        if self._custom_embedder:
            return f"custom:{type(self.embedder).__name__}"
        return f"st:{self.model_name}"

    def _embed(self, texts: list[str]) -> np.ndarray | None:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            return np.asarray(embedder(texts), dtype="float32")
        except Exception:
            return None

    def _get_embedder(self) -> Embedder | None:
        if self.embedder is not None:
            return self.embedder
        if not self.allow_models or self._embedder_failed:
            return None
        try:
            model = _load_sentence_transformer(self.model_name)
        except Exception:
            self._embedder_failed = True
            return None
        self.embedder = lambda texts: model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return self.embedder

    def _get_reranker(self):
        if self.reranker is not None:
            return self.reranker
        if not self.allow_models or self._reranker_failed:
            return None
        if os.getenv("ENABLE_CROSS_ENCODER", "1") in {"0", "false", "False", ""}:
            return None
        try:
            self.reranker = _load_cross_encoder(self.rerank_model)
        except Exception:
            self._reranker_failed = True
            return None
        return self.reranker

    # -- FAISS / NumPy index ------------------------------------------------

    def _build_faiss(self) -> None:
        self._faiss_index = None
        if self.vectors is None:
            return
        try:
            import faiss

            index = faiss.IndexFlatIP(self.vectors.shape[1])
            index.add(self.vectors)
            self._faiss_index = index
        except Exception:
            self._faiss_index = None

    # -- cache --------------------------------------------------------------

    def _load_cache(self, signature: str) -> bool:
        if not self.cache_path or not os.path.exists(self.cache_path):
            return False
        try:
            data = np.load(self.cache_path, allow_pickle=False)
            if str(data["signature"]) != signature:
                return False
            ids = [str(value) for value in data["ids"]]
            if ids != [str(record.get("job_id")) for record in self.records]:
                return False
            vectors = np.asarray(data["vectors"], dtype="float32")
        except Exception:
            return False
        if vectors.shape[0] != len(self.records):
            return False
        self.vectors = vectors
        return True

    def _save_cache(self, signature: str) -> None:
        if not self.cache_path or self.vectors is None:
            return
        try:
            parent = os.path.dirname(self.cache_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            np.savez_compressed(
                self.cache_path,
                signature=np.array(signature),
                ids=np.array([str(record.get("job_id")) for record in self.records]),
                vectors=self.vectors,
            )
        except Exception:
            pass

    # -- search -------------------------------------------------------------

    @property
    def backend(self) -> str:
        """Which retrieval backend is active for this engine."""
        if self.vectors is None:
            return "lexical"
        return "faiss" if self._faiss_index is not None else "numpy"

    def search(
        self,
        query: str,
        top_k: int = 10,
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query or not self.records or top_k <= 0:
            return []

        if self.vectors is None:
            return lexical_search(self.records, query, top_k=top_k)

        query_vector = self._embed([query])
        if query_vector is None or query_vector.size == 0:
            return lexical_search(self.records, query, top_k=top_k)
        query_vector = _normalise_rows(query_vector)[0]

        candidate_k = min(len(self.records), top_k * 4)
        if self._faiss_index is not None:
            scores, indices = self._faiss_index.search(
                query_vector.reshape(1, -1), candidate_k
            )
            indices = indices[0].tolist()
            scores = scores[0].tolist()
        else:
            similarities = self.vectors @ query_vector
            indices = np.argsort(-similarities)[:candidate_k].tolist()
            scores = [float(similarities[index]) for index in indices]

        candidates = [
            (int(index), float(score))
            for index, score in zip(indices, scores)
            if 0 <= int(index) < len(self.records)
        ]

        rerank_scores: dict[int, float] = {}
        if rerank and len(candidates) > 1:
            rerank_scores = self._rerank(query, [index for index, _ in candidates])
            if rerank_scores:
                candidates.sort(key=lambda item: rerank_scores.get(item[0], item[1]), reverse=True)

        results = []
        for index, score in candidates[:top_k]:
            rerank_score = rerank_scores.get(index)
            effective_score = rerank_score if rerank_score is not None else score
            results.append(
                _result(
                    self.records[index],
                    effective_score,
                    semantic_score=score,
                    rerank_score=rerank_score,
                )
            )
        return results

    def _rerank(self, query: str, indices: list[int]) -> dict[int, float]:
        reranker = self._get_reranker()
        if reranker is None:
            return {}
        pairs = [(query, self.texts[index]) for index in indices]
        try:
            if hasattr(reranker, "predict"):
                scores = reranker.predict(pairs)
            else:
                scores = reranker(pairs)
            values = [float(value) for value in np.asarray(scores).reshape(-1)]
        except Exception:
            return {}
        if len(values) != len(indices):
            return {}
        return dict(zip(indices, values))
