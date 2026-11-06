"""Demand-based skill ROI.

The original ticket asked for a salary-premium regression.  Salary data was
removed from this project on purpose (no salary columns, no salary visuals, no
salary prediction), so this module estimates *demand* ROI instead:

* ``momentum`` — per-month slope of log demand for a skill
* ``premium`` — pooled OLS coefficient for the skill, controlling for time,
  location concentration, role diversity, and required experience
* ``roi_score`` — a normalised blend of momentum and relative demand

Every figure is an association in the observed postings, not a causal effect.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

DATE_COLUMN = "Date Posted"
SKILL_COLUMN = "Tech Skill"
TITLE_COLUMN = "Job Title"
LOCATION_COLUMN = "Location"
EXPERIENCE_COLUMN = "Experience Required (in years)"


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if DATE_COLUMN not in work.columns or SKILL_COLUMN not in work.columns:
        return pd.DataFrame()

    work[DATE_COLUMN] = pd.to_datetime(work[DATE_COLUMN], errors="coerce")
    work = work.dropna(subset=[DATE_COLUMN])
    work = work[work[SKILL_COLUMN].notna()]
    if work.empty:
        return work

    if "Job ID" in work.columns:
        posting_key = work["Job ID"].astype("string")
    else:
        posting_key = (
            work.get(TITLE_COLUMN, pd.Series("", index=work.index)).astype(str)
            + "|"
            + work.get("Company", pd.Series("", index=work.index)).astype(str)
            + "|"
            + work.get(LOCATION_COLUMN, pd.Series("", index=work.index)).astype(str)
        )
    posting_key = posting_key.fillna(pd.Series(work.index.astype(str), index=work.index))
    work["_posting"] = posting_key
    work["_month"] = work[DATE_COLUMN].dt.to_period("M").dt.to_timestamp()
    return work


def _monthly_controls(work: pd.DataFrame) -> pd.DataFrame:
    postings = work.drop_duplicates(subset=["_posting"]).copy()
    postings[EXPERIENCE_COLUMN] = pd.to_numeric(
        postings.get(EXPERIENCE_COLUMN), errors="coerce"
    )

    overall_experience = postings[EXPERIENCE_COLUMN].mean()
    if math.isnan(overall_experience):
        overall_experience = 0.0

    rows = []
    for month, group in postings.groupby("_month", sort=True):
        location_share = 0.0
        if LOCATION_COLUMN in group.columns and group[LOCATION_COLUMN].notna().any():
            location_share = float(group[LOCATION_COLUMN].value_counts(normalize=True).iloc[0])
        role_diversity = 0.0
        if TITLE_COLUMN in group.columns and len(group):
            role_diversity = float(group[TITLE_COLUMN].nunique() / len(group))
        mean_experience = group[EXPERIENCE_COLUMN].mean()
        if math.isnan(mean_experience):
            mean_experience = overall_experience
        rows.append(
            {
                "_month": month,
                "mean_experience": float(mean_experience),
                "location_share": location_share,
                "role_diversity": role_diversity,
            }
        )
    return pd.DataFrame(rows)


def _momentum(month_counts: pd.DataFrame) -> float:
    if month_counts.empty or len(month_counts) < 2:
        return 0.0
    months = month_counts["_month"]
    x = ((months - months.min()).dt.days / 30.0).to_numpy(dtype="float64")
    y = np.log1p(month_counts["count"].to_numpy(dtype="float64"))
    if np.unique(x).size < 2:
        return 0.0
    slope = np.polyfit(x, y, 1)[0]
    return float(slope) if not math.isnan(slope) else 0.0


def _fit_premium(panel: pd.DataFrame, skills: list[str]) -> dict[str, dict[str, float | None]]:
    """Pooled OLS with skill dummies and monthly controls.

    Returns ``{skill: {"premium", "p_value"}}``.  The top-demand skill is the
    baseline, so its premium is 0 by construction.
    """
    empty = {skill: {"premium": None, "p_value": None} for skill in skills}
    if len(skills) < 2 or panel.empty:
        return empty

    model_df = panel.copy()
    model_df["skill_code"] = model_df[SKILL_COLUMN].map(
        {skill: index for index, skill in enumerate(skills)}
    )
    model_df["log_count"] = np.log1p(model_df["count"])
    model_df["month_index"] = (
        model_df["_month"] - model_df["_month"].min()
    ).dt.days / 30.0
    model_df = model_df.dropna(
        subset=["skill_code", "log_count", "month_index", "mean_experience",
                "location_share", "role_diversity"]
    )

    if len(model_df) < len(skills) + 5 or model_df["_month"].nunique() < 3:
        return empty

    try:
        import patsy
        import statsmodels.formula.api as smf
    except Exception:
        return empty

    candidate_controls = ["mean_experience", "location_share", "role_diversity"]
    usable_controls = [
        control
        for control in candidate_controls
        if model_df[control].nunique(dropna=True) > 1
    ]

    def _formula(controls: list[str]) -> str:
        expression = "log_count ~ C(skill_code) + month_index"
        if controls:
            expression += " + " + " + ".join(controls)
        return expression

    formula = _formula(usable_controls)
    try:
        # Drop controls that make the design matrix rank-deficient.
        while True:
            design = patsy.dmatrix(formula, model_df, return_type="dataframe")
            if np.linalg.matrix_rank(design.to_numpy()) >= design.shape[1]:
                break
            if not usable_controls:
                return empty
            usable_controls.pop()
            formula = _formula(usable_controls)
        result = smf.ols(formula, data=model_df).fit()
    except Exception:
        return empty

    fitted = {skills[0]: {"premium": 0.0, "p_value": None}}
    for code, skill in enumerate(skills[1:], start=1):
        term = f"C(skill_code)[T.{code}]"
        if term not in result.params:
            fitted[skill] = {"premium": None, "p_value": None}
            continue
        premium = float(result.params[term])
        p_value = float(result.pvalues.get(term, float("nan")))
        fitted[skill] = {
            "premium": round(premium, 4) if not math.isnan(premium) else None,
            "p_value": round(p_value, 4) if not math.isnan(p_value) else None,
        }
    return fitted


def _zscore(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    std = float(values.std())
    if std == 0:
        return np.zeros_like(values, dtype="float64")
    return (values - values.mean()) / std


def _confidence(months: int, demand: int) -> str:
    if months >= 6 and demand >= 10:
        return "high"
    if months >= 3 and demand >= 5:
        return "medium"
    return "low"


def compute_skill_roi(
    df: pd.DataFrame,
    top_n: int = 25,
    min_postings: int = 1,
) -> list[dict[str, Any]]:
    """Rank skills by demand ROI.

    Controls: month, required experience, location concentration, and role
    diversity.  No salary inputs or outputs.
    """
    if df is None or df.empty:
        return []

    work = _prepare(df)
    if work.empty:
        return []

    controls = _monthly_controls(work)
    total_postings = work["_posting"].nunique()
    if total_postings == 0:
        return []

    demand = (
        work.groupby(SKILL_COLUMN)["_posting"]
        .nunique()
        .sort_values(ascending=False)
    )
    demand = demand[demand >= min_postings].head(top_n)
    skills = demand.index.tolist()
    if not skills:
        return []

    rows = []
    for skill in skills:
        subset = work[work[SKILL_COLUMN] == skill]
        month_counts = (
            subset.groupby("_month")["_posting"].nunique().reset_index(name="count")
        )
        momentum = _momentum(month_counts)
        rows.append(
            {
                "skill": skill,
                "demand": int(demand.loc[skill]),
                "share_pct": round(float(demand.loc[skill]) / total_postings * 100, 1),
                "months_observed": int(month_counts["_month"].nunique()),
                "momentum": round(momentum, 4),
                "monthly_growth_pct": round((math.exp(momentum) - 1) * 100, 1),
                "confidence": _confidence(
                    int(month_counts["_month"].nunique()), int(demand.loc[skill])
                ),
            }
        )

    # One row per (skill, month) for the pooled regression.
    panel = (
        work[work[SKILL_COLUMN].isin(skills)]
        .groupby([SKILL_COLUMN, "_month"])["_posting"]
        .nunique()
        .reset_index(name="count")
        .merge(controls, on="_month", how="left")
    )
    fitted = _fit_premium(panel, skills)

    momentum_values = np.array([row["momentum"] for row in rows], dtype="float64")
    demand_values = np.log1p([row["demand"] for row in rows])
    momentum_z = _zscore(momentum_values)
    demand_z = _zscore(demand_values)

    for index, row in enumerate(rows):
        row.update(fitted.get(row["skill"], {"premium": None, "p_value": None}))
        row["roi_score"] = round(float(0.6 * momentum_z[index] + 0.4 * demand_z[index]), 4)

    rows.sort(key=lambda row: row["roi_score"], reverse=True)
    return rows
