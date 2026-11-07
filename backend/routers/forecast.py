"""Forecasting endpoint."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import get_dataframe
from backend.schemas import ForecastPoint, ForecastResponse

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


SUPPORTED_MODELS = (
    "auto",
    "sarimax",
    "prophet",
    "linear",
    "exponential_smoothing",
    "gradient_boosting",
    "lightgbm",
    "croston",
)


@router.get("/{skill}", response_model=ForecastResponse)
def forecast_skill(
    skill: str,
    months_ahead: int = Query(default=12, ge=1, le=36),
    model_type: str = Query(default="auto"),
    df=Depends(get_dataframe),
) -> ForecastResponse:
    from modules import ml_forecast

    if model_type not in SUPPORTED_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown forecasting engine '{model_type}'")

    if df is None or getattr(df, "empty", True) or "Tech Skill" not in df.columns:
        raise HTTPException(status_code=404, detail="No data available")

    available_skills = set(df["Tech Skill"].dropna().astype(str).tolist())
    if skill not in available_skills:
        raise HTTPException(status_code=404, detail=f"Unknown skill '{skill}'")

    try:
        forecast_df, status = ml_forecast.forecast_skill_demand(
            df, skill, months_ahead=months_ahead, model_type=model_type
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if forecast_df is None:
        raise HTTPException(status_code=404, detail=status or "Insufficient data for forecasting")

    # Serialise the assembled frame.
    points: list[ForecastPoint] = []
    for _, row in forecast_df.iterrows():
        date_value = row.get("Date")
        try:
            date_str = pd_timestamp_to_str(date_value)
        except Exception:
            date_str = str(date_value)
        points.append(
            ForecastPoint(
                date=date_str,
                actual=_none_if_nan(row.get("Actual")),
                forecast=_none_if_nan(row.get("Forecast")),
                lower=_none_if_nan(row.get("Lower_Bound")),
                upper=_none_if_nan(row.get("Upper_Bound")),
            )
        )

    import pandas as pd  # local import

    insights = []
    try:
        insights = ml_forecast.get_forecast_insights(forecast_df, skill)
    except Exception:
        insights = []

    mape = forecast_df.attrs.get("mape_comparison") or {}
    mape_clean = {str(k): float(v) for k, v in mape.items() if _is_finite(v)}

    return ForecastResponse(
        skill=skill,
        status=str(status or "success"),
        message=None,
        engine=forecast_df.attrs.get("engine"),
        selected_by=forecast_df.attrs.get("selected_by"),
        mape_comparison=mape_clean,
        months_ahead=months_ahead,
        forecast=points,
        insights=[str(i) for i in insights],
    )


def _none_if_nan(value):
    if value is None:
        return None
    try:
        import pandas as pd
        import numpy as np

        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value) if not isinstance(value, str) else value
    except Exception:
        return value if value is not None else None


def _is_finite(value):
    try:
        import math

        return math.isfinite(float(value))
    except Exception:
        return False


def pd_timestamp_to_str(value):
    import pandas as pd

    ts = pd.Timestamp(value)
    return ts.strftime("%Y-%m-%d")
