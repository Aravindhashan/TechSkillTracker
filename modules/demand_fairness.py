"""Demand fairness audit: ROI/momentum gaps across groups.

For each grouping dimension — location, remote status, and company type —
this module reports how demand is distributed and how it differs *after
controlling for skill and experience*.  The adjusted gaps come from a pooled
OLS on per-(skill, month, group) posting counts (mirroring
``modules.skill_roi``):

    log_count ~ C(skill) + C(group) + month_index + mean_experience

The group coefficients are demand gaps holding skill mix, time, and required
experience fixed.  They are associations in the observed postings, not causal
effects.  Company type is a keyword-based proxy (see
:func:`classify_company_type`), not an authoritative taxonomy.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

SKILL_COLUMN = "Tech Skill"
JOB_ID_COLUMN = "Job ID"
DATE_COLUMN = "Date Posted"
LOCATION_COLUMN = "Location"
COMPANY_COLUMN = "Company"
EXPERIENCE_COLUMN = "Experience Required (in years)"
REMOTE_COLUMN = "Is Remote"
TITLE_COLUMN = "Job Title"

# Company-type proxies.  Deliberately small and documented so the audit can be
# reported openly: anything not matching these lists is "Other".
_ENTERPRISE_KEYWORDS = (
    "jpmorgan",
    "goldman",
    "infosys",
    "tcs",
    "tata consultancy",
    "wipro",
    "accenture",
    "hcl",
    "tech mahindra",
    "cognizant",
    "capgemini",
    "ibm",
    "oracle",
    "microsoft",
    "google",
    "amazon",
    "flipkart",
    "nike",
    "adobe",
    "salesforce",
    "epam",
    "globant",
    "deloitte",
    "pwc",
    "kpmg",
    "ey ",
    "hsbc",
    "barclays",
    "citi",
    "paypal",
    "razorpay",
    "zerodha",
    "paytm",
    "phonepe",
)

_STAFFING_KEYWORDS = (
    "source-right",
    "source right",
    "talent",
    "staffing",
    "recruit",
    "manpower",
    "randstad",
    "adecco",
    "teamlease",
    "foundit",
    "naukri",
    "hiring",
    "hr ",
    "consultancy",
)

REMOTE_LOCATION_WORDS = ("remote", "work from home", "wfh")


def classify_company_type(company: Any) -> str:
    """Classify a company name as Enterprise, Staffing, or Other."""
    name = str(company or "").strip().lower()
    if not name or name == "unknown":
        return "Other"
    # Enterprise wins over Staffing so known consultancies (e.g. Tata
    # Consultancy Services) are not caught by the staffing keyword list.
    if any(keyword in name for keyword in _ENTERPRISE_KEYWORDS):
        return "Enterprise"
    if any(keyword in name for keyword in _STAFFING_KEYWORDS):
        return "Staffing"
    return "Other"


def _truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return not pd.isna(value) and value != 0
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y", "remote"}


def _remote_group(row: pd.Series) -> str:
    # A "Remote" location wins over a false flag: the store's boolean default
    # is False, so a remote-located posting with no flag set is still remote.
    if REMOTE_COLUMN in row and pd.notna(row.get(REMOTE_COLUMN)) and _truthy(row.get(REMOTE_COLUMN)):
        return "Remote"
    location = str(row.get(LOCATION_COLUMN) or "").lower()
    if any(word in location for word in REMOTE_LOCATION_WORDS):
        return "Remote"
    return "On-site"


def _normalize_location(value: Any) -> str:
    try:
        from modules.data_cleaner import _normalize_location as _norm

        return _norm(value)
    except Exception:
        text = str(value or "").strip()
        return text if text else "Unknown"


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if SKILL_COLUMN not in work.columns or DATE_COLUMN not in work.columns:
        return pd.DataFrame()

    work[DATE_COLUMN] = pd.to_datetime(work[DATE_COLUMN], errors="coerce")
    work = work.dropna(subset=[DATE_COLUMN])
    work = work[work[SKILL_COLUMN].notna()]
    if work.empty:
        return work

    if JOB_ID_COLUMN in work.columns:
        posting_key = work[JOB_ID_COLUMN].astype("string")
    else:
        posting_key = (
            work.get(TITLE_COLUMN, pd.Series("", index=work.index)).astype(str)
            + "|"
            + work.get(COMPANY_COLUMN, pd.Series("", index=work.index)).astype(str)
            + "|"
            + work.get(LOCATION_COLUMN, pd.Series("", index=work.index)).astype(str)
        )
    work["_posting"] = posting_key.fillna(pd.Series(work.index.astype(str), index=work.index))
    work["_month"] = work[DATE_COLUMN].dt.to_period("M").dt.to_timestamp()
    work["_location_group"] = work.get(
        LOCATION_COLUMN, pd.Series("Unknown", index=work.index)
    ).map(_normalize_location)
    work["_remote_group"] = work.apply(_remote_group, axis=1)
    work["_type_group"] = work.get(
        COMPANY_COLUMN, pd.Series("Unknown", index=work.index)
    ).map(classify_company_type)
    return work


def _group_rows(work: pd.DataFrame, group_column: str, total_postings: int) -> list[dict[str, Any]]:
    from modules.skill_roi import compute_skill_roi

    rows: list[dict[str, Any]] = []
    for group, subset in work.groupby(group_column, sort=True):
        postings = subset["_posting"].nunique()
        distinct = subset.drop_duplicates(subset=["_posting"])
        experience = pd.to_numeric(distinct.get(EXPERIENCE_COLUMN), errors="coerce")
        mean_experience = experience.mean()
        demand = subset.groupby(SKILL_COLUMN)["_posting"].nunique()
        top_skill = demand.idxmax() if len(demand) else None

        momentum_median: float | None = None
        roi_median: float | None = None
        roi_rows = compute_skill_roi(subset, top_n=25)
        if roi_rows:
            momentum_median = round(float(np.median([row["momentum"] for row in roi_rows])), 4)
            roi_median = round(float(np.median([row["roi_score"] for row in roi_rows])), 4)

        rows.append(
            {
                "group": group,
                "postings": int(postings),
                "share_pct": round(float(postings) / total_postings * 100, 1)
                if total_postings
                else 0.0,
                "mean_experience": None
                if math.isnan(mean_experience)
                else round(float(mean_experience), 2),
                "distinct_skills": int(subset[SKILL_COLUMN].nunique()),
                "top_skill": top_skill,
                "median_momentum": momentum_median,
                "median_roi_score": roi_median,
            }
        )
    return sorted(rows, key=lambda row: row["postings"], reverse=True)


def _fit_group_gaps(
    work: pd.DataFrame, group_column: str, skills: list[str], groups: list[str]
) -> dict[str, float | None]:
    """Pooled OLS group gaps controlling for skill, time, and experience."""
    if len(groups) < 2 or len(skills) < 1 or work.empty:
        return {}

    panel = (
        work.groupby([SKILL_COLUMN, "_month", group_column])["_posting"]
        .nunique()
        .reset_index(name="count")
    )
    # Mean experience inside each (skill, month, group) cell.
    experience_cell = (
        work.drop_duplicates(subset=["_posting"])
        .assign(
            _experience=pd.to_numeric(
                work.drop_duplicates(subset=["_posting"]).get(EXPERIENCE_COLUMN),
                errors="coerce",
            )
        )
        .groupby([SKILL_COLUMN, "_month", group_column])["_experience"]
        .mean()
        .reset_index(name="mean_experience")
    )
    panel = panel.merge(experience_cell, on=[SKILL_COLUMN, "_month", group_column], how="left")
    # Missing experience means "not stated", not zero years: impute the overall
    # mean so cells without a stated value do not drag the control to 0.
    overall_experience = float(
        pd.to_numeric(
            work.drop_duplicates(subset=["_posting"]).get(EXPERIENCE_COLUMN),
            errors="coerce",
        ).mean()
    )
    if math.isnan(overall_experience):
        overall_experience = 0.0
    panel["mean_experience"] = panel["mean_experience"].fillna(overall_experience)

    model_df = panel.copy()
    model_df["group_code"] = model_df[group_column].map({g: i for i, g in enumerate(groups)})
    model_df["skill_code"] = model_df[SKILL_COLUMN].map({s: i for i, s in enumerate(skills)})
    model_df["log_count"] = np.log1p(model_df["count"])
    model_df["month_index"] = (
        model_df["_month"] - model_df["_month"].min()
    ).dt.days / 30.0
    model_df = model_df.dropna(subset=["group_code", "skill_code", "log_count", "month_index"])

    if len(model_df) < len(groups) + len(skills) + 5 or model_df["_month"].nunique() < 3:
        return {}

    try:
        import patsy
        import statsmodels.formula.api as smf
    except Exception:
        return {}

    formula = "log_count ~ C(skill_code) + C(group_code) + month_index"
    controls: list[str] = []
    if model_df["mean_experience"].nunique(dropna=True) > 1:
        controls = ["mean_experience"]
        formula = "log_count ~ C(skill_code) + C(group_code) + month_index + mean_experience"
    try:
        # A constant control (no experience variation) is collinear with the
        # intercept; the rank check below withholds gaps when rank-deficient.
        design = patsy.dmatrix(
            formula.split("~", 1)[1], model_df, return_type="dataframe"
        )
        if np.linalg.matrix_rank(design.to_numpy()) < design.shape[1] and controls:
            formula = "log_count ~ C(skill_code) + C(group_code) + month_index"
            design = patsy.dmatrix(
                formula.split("~", 1)[1], model_df, return_type="dataframe"
            )
        if np.linalg.matrix_rank(design.to_numpy()) < design.shape[1]:
            return {}
        result = smf.ols(formula, data=model_df).fit()
    except Exception:
        return {}

    fitted: dict[str, float | None] = {groups[0]: None}
    for code, group in enumerate(groups[1:], start=1):
        term = f"C(group_code)[T.{code}]"
        if term not in result.params:
            fitted[group] = None
            continue
        gap = float(result.params[term])
        fitted[group] = None if math.isnan(gap) else round(gap, 4)
    return fitted


def audit_demand_fairness(
    df: pd.DataFrame,
    min_postings: int = 1,
) -> dict[str, Any]:
    """Audit ROI/momentum gaps across location, remote status, and company type.

    Returns per-dimension tables plus a gap summary.  Adjusted gaps are pooled
    OLS group coefficients controlling for skill, month, and required
    experience; when history is too thin they are reported as missing rather
    than guessed.
    """
    notes = [
        "All gaps are associations in observed postings, not causal effects.",
        "Company type is a keyword-based proxy (Enterprise / Staffing / Other), not an authoritative taxonomy.",
    ]
    if df is None or df.empty:
        return {
            "overall": {"postings": 0, "skills": 0, "months": 0},
            "by_location": [],
            "by_remote": [],
            "by_company_type": [],
            "gaps": {
                "location_share_range_pp": 0.0,
                "remote_share_gap_pp": 0.0,
                "company_type_share_range_pp": 0.0,
                "adjusted_by_location": {},
                "adjusted_by_remote": {},
                "adjusted_by_company_type": {},
            },
            "confidence": "low",
            "notes": notes,
        }

    work = _prepare(df)
    if work.empty:
        return audit_demand_fairness(pd.DataFrame(), min_postings)

    total_postings = int(work["_posting"].nunique())
    overall = {
        "postings": total_postings,
        "skills": int(work[SKILL_COLUMN].nunique()),
        "months": int(work["_month"].nunique()),
    }
    confidence = (
        "high"
        if total_postings >= 10 and overall["months"] >= 3
        else "low"
    )
    if confidence == "low":
        notes.append(
            "Low confidence: fewer than 10 postings or fewer than 3 months of history; "
            "adjusted gaps are withheld until the corpus grows."
        )

    skills = (
        work.groupby(SKILL_COLUMN)["_posting"].nunique().sort_values(ascending=False).index.tolist()
    )
    if min_postings > 1:
        counts = work.groupby(SKILL_COLUMN)["_posting"].nunique()
        skills = [skill for skill in skills if counts.loc[skill] >= min_postings]

    by_location = _group_rows(work, "_location_group", total_postings)
    by_remote = _group_rows(work, "_remote_group", total_postings)
    by_company_type = _group_rows(work, "_type_group", total_postings)

    def _range(rows: list[dict]) -> float:
        if not rows:
            return 0.0
        shares = [row["share_pct"] for row in rows]
        return round(max(shares) - min(shares), 1)

    gaps = {
        "location_share_range_pp": _range(by_location),
        "remote_share_gap_pp": _range(by_remote),
        "company_type_share_range_pp": _range(by_company_type),
        "adjusted_by_location": _fit_group_gaps(
            work, "_location_group", skills, [row["group"] for row in by_location]
        ),
        "adjusted_by_remote": _fit_group_gaps(
            work, "_remote_group", skills, [row["group"] for row in by_remote]
        ),
        "adjusted_by_company_type": _fit_group_gaps(
            work, "_type_group", skills, [row["group"] for row in by_company_type]
        ),
    }

    return {
        "overall": overall,
        "by_location": by_location,
        "by_remote": by_remote,
        "by_company_type": by_company_type,
        "gaps": gaps,
        "confidence": confidence,
        "notes": notes,
    }
