"""Search and ROI endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_dataframe, get_search_records
from backend.schemas import RoiResponse, SearchRequest, SearchResponse

router = APIRouter(tags=["search"])


@router.post("/api/search", response_model=SearchResponse)
def search(payload: SearchRequest, records=Depends(get_search_records)) -> SearchResponse:
    from modules import semantic_search

    engine = semantic_search.SemanticSearchEngine(allow_models=True)
    engine.build(records or [])
    results = engine.search(payload.query, top_k=payload.top_k, rerank=payload.rerank)

    retrieval_backend = {"faiss": "FAISS", "numpy": "NumPy cosine"}.get(engine.backend, "lexical fallback")
    result_list = list(results or [])

    # Annotate each result with an estimated ghost risk (Slice 3 badge).
    try:
        from modules import ghost_risk, store

        by_id = {str(p["job_id"]): p for p in store.fetch_postings(limit=10000)}
        for item in result_list:
            posting = by_id.get(str(item.get("job_id")))
            if posting is None:
                continue
            risk = ghost_risk.ghost_risk_score(
                str(posting.get("job_id")),
                first_seen=posting.get("first_seen"),
                last_seen=posting.get("last_seen"),
                is_active=bool(posting.get("is_active")),
            )
            item["ghost_risk"] = {"risk": risk["risk"], "label": risk["label"]}
    except Exception:
        pass

    return SearchResponse(
        query=payload.query,
        backend=retrieval_backend,
        results=result_list,
        postings=result_list,
        items=result_list,
        data=result_list,
    )


@router.get("/api/roi", response_model=RoiResponse)
def roi(
    top_n: int = Query(default=25, ge=1, le=100),
    min_postings: int = Query(default=1, ge=1),
    df=Depends(get_dataframe),
) -> RoiResponse:
    from modules import skill_roi

    rows = skill_roi.compute_skill_roi(df, top_n=top_n, min_postings=min_postings) if df is not None else []
    row_list = list(rows or [])
    return RoiResponse(rows=row_list, results=row_list, items=row_list, data=row_list)
