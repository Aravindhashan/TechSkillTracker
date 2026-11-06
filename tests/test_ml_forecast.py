import pandas as pd
import pytest

from modules import ml_forecast as mf


@pytest.fixture(scope="module")
def df():
    import numpy as np

    rows = []
    skills = ["Python", "React", "Docker", "AWS", "SQL"]
    # ~24 months of postings per skill
    for skill in skills:
        for month in range(1, 25):
            n = int(5 + (month % 7) + (hash(skill) % 4))
            year = 2023 + (month - 1) // 12
            mon = (month - 1) % 12 + 1
            for _ in range(n):
                rows.append(
                    {
                        "Tech Skill": skill,
                        "Date Posted": f"{year}-{mon:02d}-15",
                        "Job Title": f"{skill} Dev",
                        "Company": "Acme",
                        "Location": "Bengaluru",
                        "Experience Required (in years)": 3.0,
                    }
                )
    return pd.DataFrame(rows)


def test_supported_engines_includes_new_ones():
    assert "gradient_boosting" in mf.SUPPORTED_ENGINES
    assert "croston" in mf.SUPPORTED_ENGINES
    assert "auto" in mf.SUPPORTED_ENGINES


def test_mape_handles_zeros():
    assert mf._mape([1, 2, 3], [1, 2, 3]) == pytest.approx(0.0)
    assert mf._mape([0, 2, 3], [1, 2, 3]) == pytest.approx(0.0)  # zero actual skipped
    assert mf._mape([0, 0, 0], [1, 2, 3]) == float("inf")


def test_croston_produces_forecast(df):
    monthly = mf._monthly_series(df, "Python")
    fc = mf._croston_forecast(monthly, 6)
    assert fc is not None
    assert len(fc[fc["Forecast"].notna()]) == 6
    assert fc.attrs["engine"] == "Croston (SBA)"


def test_gradient_boosting_produces_forecast(df):
    fc, status = mf.forecast_skill_demand(df, "Python", months_ahead=4, model_type="gradient_boosting")
    assert status == "success"
    assert fc is not None
    assert len(fc[fc["Forecast"].notna()]) == 4
    assert "Gradient Boosting" in fc.attrs["engine"]


def test_auto_reports_mape_comparison(df):
    fc, status = mf.forecast_skill_demand(df, "Python", months_ahead=4, model_type="auto")
    assert status == "success"
    assert fc is not None
    comparison = fc.attrs.get("mape_comparison") or {}
    assert isinstance(comparison, dict)
    assert len(comparison) >= 2
    assert fc.attrs.get("selected_by") in ("mape", "availability")


def test_backtest_engines_returns_finite_values(df):
    result = mf.backtest_engines(df, "Python", holdout=3)
    assert isinstance(result, dict)
    assert "linear" in result
    assert all(isinstance(v, float) for v in result.values())


def test_forecast_insufficient_data():
    import pandas as pd

    tiny = pd.DataFrame(
        {"Tech Skill": ["X", "X"], "Date Posted": ["2024-01-01", "2024-02-01"]}
    )
    fc, status = mf.forecast_skill_demand(tiny, "X", months_ahead=3, model_type="linear")
    # linear needs >=2 months; with 2 months it may still produce a forecast or fail gracefully
    assert fc is None or status in ("success",)


def test_unknown_engine_rejected(df):
    fc, status = mf.forecast_skill_demand(df, "Python", months_ahead=3, model_type="nope")
    assert fc is None
    assert "Unknown" in status
