"""Pydantic request/response schemas for the FastAPI backend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Health / market
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    backend: str
    postings: int
    store_available: bool
    data_age_hours: float | None = None


class MarketOverviewResponse(BaseModel):
    total_openings: int
    unique_skills: int
    companies: int
    locations: int = 0


class TopSkill(BaseModel):
    skill: str
    count: int


class TopLocation(BaseModel):
    location: str
    count: int


class TopLocationsResponse(BaseModel):
    locations: list[TopLocation] = Field(default_factory=list)


class RecentPosting(BaseModel):
    job_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    posted_at: str | None = None
    url: str | None = None
    is_remote: bool | None = None
    skills: list[str] = Field(default_factory=list)


class RecentPostingsResponse(BaseModel):
    postings: list[RecentPosting] = Field(default_factory=list)


class TopSkillsResponse(BaseModel):
    skills: list[TopSkill] = Field(default_factory=list)
    top_skills: list[TopSkill] = Field(default_factory=list)
    items: list[TopSkill] = Field(default_factory=list)
    results: list[TopSkill] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


class ForecastPoint(BaseModel):
    date: str
    actual: float | None = None
    forecast: float | None = None
    lower: float | None = None
    upper: float | None = None


class ForecastResponse(BaseModel):
    skill: str
    status: str = "success"
    message: str | None = None
    engine: str | None = None
    selected_by: str | None = None
    mape_comparison: dict[str, float] = Field(default_factory=dict)
    months_ahead: int
    forecast: list[ForecastPoint] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class RecommendationRequest(BaseModel):
    mode: Literal["complementary", "role", "learning-path"]
    skill: str | None = None
    role: str | None = None
    current_skills: list[str] | None = None
    target_role: str | None = None
    top_n: int = Field(default=10, ge=1, le=50)


class RecommendationResponse(BaseModel):
    mode: str
    status: str
    message: str | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Search / ROI
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    rerank: bool = True


class SearchResponse(BaseModel):
    query: str
    backend: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    postings: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)


class RoiResponse(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    results: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Demand science
# ---------------------------------------------------------------------------


class DemandScienceResponse(BaseModel):
    survival_overall: list[dict[str, Any]] = Field(default_factory=list)
    survival: list[dict[str, Any]] = Field(default_factory=list)
    survival_curves: list[dict[str, Any]] = Field(default_factory=list)
    survival_by_skill: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    survival_by_group: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    cox: dict[str, Any] = Field(default_factory=dict)
    cox_regression: dict[str, Any] = Field(default_factory=dict)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_flags: list[dict[str, Any]] = Field(default_factory=list)
    pmi_pairs: list[dict[str, Any]] = Field(default_factory=list)
    pmi: list[dict[str, Any]] = Field(default_factory=list)
    communities: dict[str, int] = Field(default_factory=dict)
    skill_communities: dict[str, int] = Field(default_factory=dict)
    relatedness: dict[str, list[list[Any]]] = Field(default_factory=dict)
    skill_relatedness: dict[str, list[list[Any]]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Fairness
# ---------------------------------------------------------------------------


class FairnessResponse(BaseModel):
    result: dict[str, Any]


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


class ResumeAnalysisResponse(BaseModel):
    filename: str
    analysis: dict[str, Any]
    resume_id: str | None = None


# ---------------------------------------------------------------------------
# Per-job match (Slice 1 — stateless)
# ---------------------------------------------------------------------------


class MatchRequest(BaseModel):
    job_id: str
    resume_skills: list[str] = Field(default_factory=list)
    resume_years: float | None = None
    resume_title: str | None = None


class MatchBatchRequest(BaseModel):
    job_ids: list[str] = Field(default_factory=list)
    resume_skills: list[str] = Field(default_factory=list)
    resume_years: float | None = None
    resume_title: str | None = None


class MatchBatchResponse(BaseModel):
    results: list["MatchResponse"] = Field(default_factory=list)


class MatchResponse(BaseModel):
    job_id: str
    match_score: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_must_have: list[str] = Field(default_factory=list)
    missing_nice_to_have: list[str] = Field(default_factory=list)
    experience_gap: float | None = None
    title_similarity: float | None = None
    posting_health: Literal["active", "closed"]
    confidence: Literal["low", "medium", "high"]
    ghost_risk: dict[str, Any] | None = None
