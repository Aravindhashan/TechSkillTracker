"""Fairness audit endpoint."""

from __future__ import annotations

import math

import pandas as pd
from fastapi import APIRouter, Depends, Query

from backend.dependencies import get_dataframe

router = APIRouter(prefix="/api/fairness", tags=["fairness"])


def _sanitize(value):
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    try:
        import numpy as np

        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(value, (np.bool_,)):
            return bool(value)
    except Exception:
        pass
    return value


@router.get("")
def fairness(
    min_postings: int = Query(default=1, ge=1),
    df=Depends(get_dataframe),
):
    from modules import demand_fairness

    if df is None or getattr(df, "empty", True):
        result = demand_fairness.audit_demand_fairness(
            pd.DataFrame(), min_postings=min_postings
        )
    else:
        result = demand_fairness.audit_demand_fairness(df, min_postings=min_postings)

    return _sanitize(result)
