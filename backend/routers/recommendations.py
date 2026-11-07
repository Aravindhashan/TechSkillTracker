"""Recommendations endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_dataframe
from backend.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def recommendations(
    payload: RecommendationRequest,
    df=Depends(get_dataframe),
) -> RecommendationResponse:
    from modules import recommendation_engine

    if df is None or getattr(df, "empty", True):
        # Still attempt; modules handle empty frames mostly.
        pass

    mode = payload.mode
    top_n = payload.top_n

    if mode == "complementary":
        skill = payload.skill
        if not skill:
            raise HTTPException(status_code=422, detail="skill is required for complementary mode")
        results, status = recommendation_engine.recommend_skills(df, skill, top_n=top_n)
        result_list = list(results or [])
        return RecommendationResponse(mode=mode, status=status, results=result_list, items=result_list, data=result_list, recommendations=result_list)

    if mode == "role":
        role = payload.role
        if not role:
            raise HTTPException(status_code=422, detail="role is required for role mode")
        results, status = recommendation_engine.recommend_for_job_role(df, role, top_n=top_n)
        result_list = list(results or [])
        return RecommendationResponse(mode=mode, status=status, results=result_list, items=result_list, data=result_list, recommendations=result_list)

    if mode == "learning-path":
        target_role = payload.target_role
        if not target_role:
            raise HTTPException(status_code=422, detail="target_role is required for learning-path mode")
        current_skills = payload.current_skills or []
        results, status = recommendation_engine.get_learning_path(df, current_skills, target_role)
        if results is None:
            results = []
        result_list = list(results or [])
        return RecommendationResponse(mode=mode, status=status, results=result_list, items=result_list, data=result_list, recommendations=result_list)

    raise HTTPException(status_code=422, detail=f"Unknown mode '{mode}'")
