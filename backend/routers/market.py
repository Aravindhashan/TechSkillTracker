"""Market overview endpoints."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_dataframe, get_store_count
from backend.schemas import (
    MarketOverviewResponse,
    RecentPosting,
    RecentPostingsResponse,
    TopLocation,
    TopLocationsResponse,
    TopSkill,
    TopSkillsResponse,
)

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


@router.get("/locations", response_model=TopLocationsResponse)
def top_locations(
    n: int = Query(default=10, ge=1, le=100),
    df=Depends(get_dataframe),
) -> TopLocationsResponse:
    if df is None or getattr(df, "empty", True) or "Location" not in df.columns:
        return TopLocationsResponse(locations=[])

    counts = df["Location"].value_counts().head(n)
    locations = [TopLocation(location=str(loc), count=int(count)) for loc, count in counts.items()]
    return TopLocationsResponse(locations=locations)


@router.get("/recent-postings", response_model=RecentPostingsResponse)
def recent_postings(
    n: int = Query(default=10, ge=1, le=50),
) -> RecentPostingsResponse:
    from modules import store as job_store

    try:
        records = job_store.fetch_postings_with_skills(days=365, limit=n)
    except Exception:
        return RecentPostingsResponse(postings=[])

    postings = [
        RecentPosting(
            job_id=str(item.get("job_id") or ""),
            title=item.get("title"),
            company=item.get("company"),
            location=item.get("location"),
            posted_at=item.get("posted_at"),
            url=item.get("url"),
            is_remote=bool(item.get("is_remote", False)) if item.get("is_remote") is not None else None,
            skills=[str(s) for s in (item.get("skills") or [])],
        )
        for item in records
    ]
    return RecentPostingsResponse(postings=postings)


@router.get("/demand-trends")
def demand_trends(
    top_n: int = Query(default=5, ge=1, le=20),
    df=Depends(get_dataframe),
):
    if df is None or getattr(df, "empty", True):
        return []
    if "Tech Skill" not in df.columns or "Date Posted" not in df.columns:
        return []
    top_skills = df["Tech Skill"].value_counts().head(top_n).index.tolist()
    work = df[df["Tech Skill"].isin(top_skills)].copy()
    work["_month"] = pd.to_datetime(work["Date Posted"], errors="coerce").dt.to_period("M").astype(str)
    grouped = work.groupby(["Tech Skill", "_month"]).size().reset_index(name="count")
    return grouped.rename(columns={"Tech Skill": "skill", "_month": "month"}).to_dict(orient="records")


@router.get("/skill-pairs")
def skill_pairs(
    min_cooccurrence: int = Query(default=2, ge=1),
    df=Depends(get_dataframe),
):
    from itertools import combinations

    if df is None or getattr(df, "empty", True):
        return []
    if "Company" not in df.columns or "Tech Skill" not in df.columns:
        return []
    pair_counts: dict[tuple[str, str], int] = {}
    for _company, group in df.groupby("Company"):
        skills = sorted(set(group["Tech Skill"].dropna().astype(str).tolist()))
        for a, b in combinations(skills, 2):
            pair_counts[(a, b)] = pair_counts.get((a, b), 0) + 1
    result = [
        {"skill_a": a, "skill_b": b, "count": c}
        for (a, b), c in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)
        if c >= min_cooccurrence
    ]
    return result[:20]
