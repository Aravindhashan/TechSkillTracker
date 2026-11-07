"""Market overview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_dataframe, get_store_count
from backend.schemas import MarketOverviewResponse, TopSkill, TopSkillsResponse

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview", response_model=MarketOverviewResponse)
def market_overview(df=Depends(get_dataframe)) -> MarketOverviewResponse:
    if df is None or getattr(df, "empty", True):
        return MarketOverviewResponse(total_openings=0, unique_skills=0, companies=0, locations=0, records=0)

    total_openings = (
        df["Job ID"].nunique() if "Job ID" in df.columns else len(df)
    )
    unique_skills = df["Tech Skill"].nunique() if "Tech Skill" in df.columns else 0
    companies = df["Company"].nunique() if "Company" in df.columns else 0
    locations = df["Location"].nunique() if "Location" in df.columns else 0
    return MarketOverviewResponse(
        total_openings=int(total_openings),
        unique_skills=int(unique_skills),
        companies=int(companies),
        locations=int(locations),
    )


@router.get("/top-skills", response_model=TopSkillsResponse)
def top_skills(
    n: int = Query(default=10, ge=1, le=100),
    df=Depends(get_dataframe),
) -> TopSkillsResponse:
    if df is None or getattr(df, "empty", True) or "Tech Skill" not in df.columns:
        return TopSkillsResponse(skills=[])

    counts = df["Tech Skill"].value_counts().head(n)
    skills = [TopSkill(skill=str(skill), count=int(count)) for skill, count in counts.items()]
    return TopSkillsResponse(skills=skills, top_skills=skills, items=skills, results=skills)
