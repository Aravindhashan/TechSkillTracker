"""Offline evaluation for recommendations and semantic search.

Demand-only evaluation utilities. Both harnesses share three ideas:

* split by posting (``Job ID``), never by row, so one posting cannot leak
  from train into test;
* holdouts are either temporal (most recent postings last) or seeded random;
* metrics are standard retrieval metrics for a ranked list: Precision@k,
  Recall@k, and NDCG@k (binary or graded relevance).

No live data is required: callers pass the same dataframe / records the app
loads from the store, or small synthetic fixtures in tests.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd

SKILL_COLUMN = "Tech Skill"
JOB_ID_COLUMN = "Job ID"
DATE_COLUMN = "Date Posted"
TITLE_COLUMN = "Job Title"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def precision_at_k(predicted: Iterable[str], relevant: set[str], k: int) -> float:
    """Fraction of the top-k predictions that are relevant."""
    if k <= 0:
        return 0.0
    top = list(predicted)[:k]
    if not top:
        return 0.0
    hits = sum(1 for item in top if item in relevant)
    return hits / len(top)


def recall_at_k(predicted: Iterable[str], relevant: set[str], k: int) -> float:
    """Fraction of all relevant items recovered in the top-k."""
    if k <= 0 or not relevant:
        return 0.0
    top = list(predicted)[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / len(relevant)


def _dcg(relevances: list[float]) -> float:
    return sum(rel / math.log2(index + 2) for index, rel in enumerate(relevances))


def ndcg_at_k(
    predicted: Iterable[str],
    relevance: dict[str, float] | set[str],
    k: int,
) -> float:
    """Normalised DCG at k. Accepts binary relevance (a set) or graded scores."""
    if k <= 0:
        return 0.0
    if isinstance(relevance, set):
        gains = {item: 1.0 for item in relevance}
    else:
        gains = dict(relevance)
    if not gains:
        return 0.0

    top = list(predicted)[:k]
    actual = [gains.get(item, 0.0) for item in top]
    ideal = sorted(gains.values(), reverse=True)[:k]
    ideal_dcg = _dcg(ideal)
    if ideal_dcg == 0:
        return 0.0
    return _dcg(actual) / ideal_dcg


def _summarise(per_query: list[dict[str, float]], ks: tuple[int, ...]) -> dict[str, Any]:
    """Mean each metric across queries; empty input yields zeros."""
    summary: dict[str, Any] = {"n_queries": len(per_query)}
    for k in ks:
        if not per_query:
            summary[f"precision@{k}"] = 0.0
            summary[f"recall@{k}"] = 0.0
            summary[f"ndcg@{k}"] = 0.0
            continue
        summary[f"precision@{k}"] = round(
            float(np.mean([row[f"precision@{k}"] for row in per_query])), 4
        )
        summary[f"recall@{k}"] = round(
            float(np.mean([row[f"recall@{k}"] for row in per_query])), 4
        )
        summary[f"ndcg@{k}"] = round(
            float(np.mean([row[f"ndcg@{k}"] for row in per_query])), 4
        )
    return summary


# ---------------------------------------------------------------------------
# Splits (by posting, never by row)
# ---------------------------------------------------------------------------


def _posting_ids(df: pd.DataFrame) -> list[str]:
    if JOB_ID_COLUMN in df.columns:
        return sorted(df[JOB_ID_COLUMN].dropna().astype(str).unique().tolist())
    return [str(index) for index in df.index]


def split_dataframe(
    df: pd.DataFrame,
    test_fraction: float = 0.2,
    strategy: str = "temporal",
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a skill-expanded frame into (train, test) by posting.

    ``strategy="temporal"`` holds out the most recent postings (by ``Date
    Posted`` when available); ``strategy="random"`` is a seeded shuffle.
    A posting appears on exactly one side.
    """
    if df is None or df.empty:
        return df, df
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")

    if JOB_ID_COLUMN in df.columns:
        keys = df[JOB_ID_COLUMN].astype(str)
    else:
        keys = pd.Series(df.index.astype(str), index=df.index)

    if strategy == "temporal" and DATE_COLUMN in df.columns:
        dates = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
        per_posting = dates.groupby(keys.values).min().sort_values()
        ordered_ids = per_posting.index.tolist()
    elif strategy == "random":
        rng = np.random.default_rng(seed)
        ordered_ids = keys.drop_duplicates().tolist()
        rng.shuffle(ordered_ids)
    else:
        raise ValueError(f"unknown split strategy: {strategy}")

    n_test = max(1, int(round(len(ordered_ids) * test_fraction)))
    test_ids = set(ordered_ids[-n_test:]) if strategy == "temporal" else set(ordered_ids[:n_test])
    mask = keys.isin(test_ids)
    return df[~mask].reset_index(drop=True), df[mask].reset_index(drop=True)


def _posting_skills(df: pd.DataFrame) -> dict[str, set[str]]:
    """Map posting id -> set of canonical skills in that posting."""
    if JOB_ID_COLUMN not in df.columns or SKILL_COLUMN not in df.columns:
        return {}
    grouped = df.groupby(df[JOB_ID_COLUMN].astype(str))[SKILL_COLUMN]
    return {str(job_id): set(skills.dropna().astype(str)) for job_id, skills in grouped}


# ---------------------------------------------------------------------------
# Recommender evaluation
# ---------------------------------------------------------------------------


def evaluate_recommendations(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    recommender: Callable[..., tuple[list, str]] | None = None,
    top_n: int = 5,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, Any]:
    """Score ``recommend_skills`` against held-out posting co-occurrence.

    For each skill that appears in a test posting, the query skill is run
    through the recommender trained on ``train_df`` only.  Ground truth is the
    union of skills that co-occur with the query skill in the same test
    posting.  Returns per-k mean metrics plus coverage (share of queries with
    at least one recommendation).
    """
    if recommender is None:
        from modules.recommendation_engine import recommend_skills

        recommender = recommend_skills

    posting_skills = _posting_skills(test_df)
    if not posting_skills:
        return {"n_queries": 0, **{f"{m}@{k}": 0.0 for k in ks for m in ("precision", "recall", "ndcg")}}

    # Ground truth: skill -> skills it actually co-occurs with in test postings.
    truth: dict[str, set[str]] = {}
    for skills in posting_skills.values():
        for skill in skills:
            truth.setdefault(skill, set()).update(skills - {skill})

    train_vocab = (
        set(train_df[SKILL_COLUMN].dropna().astype(str))
        if SKILL_COLUMN in train_df.columns
        else set()
    )

    per_query: list[dict[str, float]] = []
    covered = 0
    for query_skill, relevant in sorted(truth.items()):
        if not relevant or query_skill not in train_vocab:
            continue
        recommendations, _status = recommender(train_df, query_skill, top_n=top_n)
        predicted = [
            item["skill"] if isinstance(item, dict) else str(item)
            for item in recommendations
        ]
        if predicted:
            covered += 1
        row: dict[str, float] = {}
        for k in ks:
            row[f"precision@{k}"] = precision_at_k(predicted, relevant, k)
            row[f"recall@{k}"] = recall_at_k(predicted, relevant, k)
            row[f"ndcg@{k}"] = ndcg_at_k(predicted, relevant, k)
        per_query.append(row)

    summary = _summarise(per_query, ks)
    summary["coverage"] = round(covered / len(per_query), 4) if per_query else 0.0
    return summary


def evaluate_recommendations_holdout(
    df: pd.DataFrame,
    test_fraction: float = 0.2,
    strategy: str = "temporal",
    seed: int = 42,
    top_n: int = 5,
    ks: tuple[int, ...] = (1, 3, 5),
    recommender: Callable[..., tuple[list, str]] | None = None,
) -> dict[str, Any]:
    """Split ``df`` by posting and evaluate the recommender in one call."""
    train_df, test_df = split_dataframe(df, test_fraction, strategy, seed)
    result = evaluate_recommendations(train_df, test_df, recommender, top_n, ks)
    result["strategy"] = strategy
    result["test_fraction"] = test_fraction
    return result


# ---------------------------------------------------------------------------
# Semantic search evaluation
# ---------------------------------------------------------------------------


def _relevance_map(
    test_records: list[dict],
    train_skills: dict[str, set[str]],
) -> dict[str, dict[str, float]]:
    """Graded relevance of each train posting to one test posting.

    Relevance is the fraction of the test posting's skills that the train
    posting shares (0..1).  A train posting with no skill overlap scores 0.
    """
    mapping: dict[str, dict[str, float]] = {}
    for test_record in test_records:
        job_id = str(test_record.get("job_id") or "")
        if not job_id:
            continue
        test_skills = set(test_record.get("skills") or [])
        if not test_skills:
            continue
        relevance: dict[str, float] = {}
        for train_id, skills in train_skills.items():
            overlap = len(test_skills & skills)
            if overlap:
                relevance[train_id] = overlap / len(test_skills)
        if relevance:
            mapping[job_id] = relevance
    return mapping


def evaluate_search(
    engine: Any,
    test_records: list[dict],
    train_records: list[dict],
    top_k: int = 5,
    ks: tuple[int, ...] = (1, 3, 5),
    rerank: bool = False,
) -> dict[str, Any]:
    """Score an already-built engine against held-out postings.

    Each test posting's title is the query.  The engine must have been built
    on ``train_records`` only.  ``rerank`` defaults to False so the embedding
    retrieval path is measured in isolation.
    """
    if not test_records or not train_records:
        return {"n_queries": 0, **{f"{m}@{k}": 0.0 for k in ks for m in ("precision", "recall", "ndcg")}}

    train_skills = {
        str(record.get("job_id")): set(record.get("skills") or [])
        for record in train_records
        if record.get("job_id")
    }
    relevance_map = _relevance_map(test_records, train_skills)

    per_query: list[dict[str, float]] = []
    covered = 0
    for record in test_records:
        job_id = str(record.get("job_id") or "")
        query = str(record.get("title") or "").strip()
        if not query or job_id not in relevance_map:
            continue
        relevance = relevance_map[job_id]
        ranked = engine.search(query, top_k=top_k, rerank=rerank)
        predicted = [str(item["job_id"]) for item in ranked if item.get("job_id")]
        if predicted:
            covered += 1
        binary = set(relevance)
        row: dict[str, float] = {}
        for k in ks:
            row[f"precision@{k}"] = precision_at_k(predicted, binary, k)
            row[f"recall@{k}"] = recall_at_k(predicted, binary, k)
            row[f"ndcg@{k}"] = ndcg_at_k(predicted, relevance, k)
        per_query.append(row)

    summary = _summarise(per_query, ks)
    summary["coverage"] = round(covered / len(per_query), 4) if per_query else 0.0
    return summary


def split_records(
    records: list[dict],
    test_fraction: float = 0.2,
    strategy: str = "temporal",
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Split posting dicts into (train, test) by ``job_id``.

    Temporal order uses ``posted_at`` (falling back to ``last_seen``); the
    latest postings form the test set.  Mirrors ``split_dataframe``.
    """
    records = [record for record in records if record.get("job_id")]
    if len(records) < 2:
        return records, []
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")

    if strategy == "temporal":
        ordered = sorted(
            records,
            key=lambda record: str(record.get("posted_at") or record.get("last_seen") or ""),
        )
    elif strategy == "random":
        ordered = list(records)
        np.random.default_rng(seed).shuffle(ordered)
    else:
        raise ValueError(f"unknown split strategy: {strategy}")

    n_test = max(1, int(round(len(ordered) * test_fraction)))
    if strategy == "temporal":
        return ordered[:-n_test], ordered[-n_test:]
    return ordered[n_test:], ordered[:n_test]


def evaluate_search_holdout(
    records: list[dict],
    embedder: Callable | None = None,
    test_fraction: float = 0.2,
    strategy: str = "temporal",
    seed: int = 42,
    top_k: int = 5,
    ks: tuple[int, ...] = (1, 3, 5),
    engine_class: Any | None = None,
    allow_models: bool = True,
) -> dict[str, Any]:
    """Split, embed the train fold, and score the search engine."""
    train_records, test_records = split_records(records, test_fraction, strategy, seed)
    if engine_class is None:
        from modules.semantic_search import SemanticSearchEngine

        engine_class = SemanticSearchEngine
    engine = engine_class(embedder=embedder, allow_models=allow_models)
    engine.build(train_records)
    result = evaluate_search(engine, test_records, train_records, top_k, ks)
    result["strategy"] = strategy
    result["test_fraction"] = test_fraction
    result["n_train"] = len(train_records)
    result["n_test"] = len(test_records)
    return result
