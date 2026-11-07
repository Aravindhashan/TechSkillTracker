"""Demand science endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_dataframe
from backend.routers.fairness import _sanitize
from backend.schemas import DemandScienceResponse

router = APIRouter(prefix="/api/demand-science", tags=["demand-science"])


def _df_to_records(frame) -> list[dict]:
    if frame is None:
        return []
    try:
        if hasattr(frame, "empty") and frame.empty:
            return []
    except Exception:
        pass
    try:
        return frame.to_dict(orient="records")
    except Exception:
        try:
            return [dict(r) for r in frame]
        except Exception:
            return []


@router.get("", response_model=DemandScienceResponse)
def demand_science(df=Depends(get_dataframe)) -> DemandScienceResponse:
    from modules import demand_science

    if df is None or getattr(df, "empty", True):
        return DemandScienceResponse()

    # Survival overall
    try:
        km_overall = demand_science.kaplan_meier(df)
    except Exception:
        km_overall = None
    survival_overall = _sanitize(_df_to_records(km_overall))

    # Survival by skill (top skills)
    survival_by_skill: dict[str, list[dict]] = {}
    try:
        if "Tech Skill" in df.columns:
            result = demand_science.survival_by_group(df, "Tech Skill", top_n=8)
            for key, frame in (result or {}).items():
                survival_by_skill[str(key)] = _sanitize(_df_to_records(frame))
    except Exception:
        survival_by_skill = {}

    # Cox
    cox: dict = {}
    try:
        cox = _sanitize(demand_science.cox_regression(df) or {})
    except Exception:
        cox = {}

    # Anomalies
    anomalies: list[dict] = []
    try:
        anom_df = demand_science.anomaly_detection(df)
        anomalies = _sanitize(_df_to_records(anom_df))
    except Exception:
        anomalies = []

    # PMI
    pmi_pairs: list[dict] = []
    try:
        pmi_pairs = _sanitize(list(demand_science.skill_pmi(df) or []))
    except Exception:
        pmi_pairs = []

    # Communities
    communities: dict = {}
    try:
        communities = demand_science.skill_communities(df) or {}
    except Exception:
        communities = {}

    # Relatedness
    relatedness: dict[str, list[list[Any]]] = {}
    try:
        related = demand_science.skill_relatedness(df) or {}
        for key, value in related.items():
            relatedness[str(key)] = [
                [str(pair[0]), float(pair[1])] for pair in (value or [])
                if isinstance(pair, (list, tuple)) and len(pair) >= 2
            ]
    except Exception:
        relatedness = {}

    communities_out = {str(k): int(v) for k, v in communities.items()}
    return DemandScienceResponse(
        survival_overall=survival_overall,
        survival=survival_overall,
        survival_curves=survival_overall,
        survival_by_skill=survival_by_skill,
        survival_by_group=survival_by_skill,
        cox=cox,
        cox_regression=cox,
        anomalies=anomalies,
        anomaly_flags=anomalies,
        pmi_pairs=pmi_pairs,
        pmi=pmi_pairs,
        communities=communities_out,
        skill_communities=communities_out,
        relatedness=relatedness,
        skill_relatedness=relatedness,
    )
