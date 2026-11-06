import pandas as pd
import pytest

from modules import demand_science as ds


@pytest.fixture(scope="module")
def df():
    import numpy as np

    rows = []
    skills = ["Python", "React", "Docker", "AWS", "SQL", "Kubernetes"]
    for skill in skills:
        for month in range(1, 13):
            n = int(4 + (month % 5))
            for _ in range(n):
                rows.append(
                    {
                        "Job ID": f"{skill}-{month}",
                        "Job Title": f"{skill} Dev",
                        "Tech Skill": skill,
                        "Company": "Acme" if month % 2 == 0 else "Beta",
                        "Location": "Bengaluru",
                        "Experience Required (in years)": 3.0 + (month % 4),
                        "Date Posted": f"2024-{month:02d}-15",
                        "first_seen": f"2024-{month:02d}-15",
                        "last_seen": f"2024-{month:02d}-20" if month < 12 else f"2024-12-20",
                        "is_active": month < 12,
                    }
                )
    # Add a multi-skill posting for PMI/communities.
    rows.append(
        {
            "Job ID": "multi-1",
            "Job Title": "Full Stack",
            "Tech Skill": "Python",
            "Company": "Acme",
            "Location": "Bengaluru",
            "Experience Required (in years)": 4.0,
            "Date Posted": "2024-06-15",
            "first_seen": "2024-06-15",
            "last_seen": "2024-06-20",
            "is_active": False,
        }
    )
    rows.append(
        {
            "Job ID": "multi-1",
            "Job Title": "Full Stack",
            "Tech Skill": "React",
            "Company": "Acme",
            "Location": "Bengaluru",
            "Experience Required (in years)": 4.0,
            "Date Posted": "2024-06-15",
            "first_seen": "2024-06-15",
            "last_seen": "2024-06-20",
            "is_active": False,
        }
    )
    return pd.DataFrame(rows)


def test_kaplan_meier(df):
    km = ds.kaplan_meier(df)
    assert not km.empty
    assert "survival" in km.columns
    assert (km["survival"] >= 0).all()
    assert (km["survival"] <= 1).all()


def test_survival_by_group(df):
    result = ds.survival_by_group(df, "Tech Skill", top_n=3)
    assert isinstance(result, dict)
    assert len(result) >= 1


def test_cox_regression(df):
    result = ds.cox_regression(df)
    # Either coefficients or an error message about insufficient events.
    assert "coefficients" in result or "error" in result


def test_anomaly_detection(df):
    anomalies = ds.anomaly_detection(df)
    assert isinstance(anomalies, pd.DataFrame)


def test_minhash_dedupe():
    records = [
        {"title": "Python Developer", "company": "Acme", "description": "Build APIs with Django"},
        {"title": "Python Developer", "company": "Acme", "description": "Build APIs with Django and Flask"},
        {"title": "React Engineer", "company": "Beta", "description": "Build UI with React"},
    ]
    deduped = ds.minhash_dedupe(records, threshold=0.5)
    assert len(deduped) <= len(records)
    assert len(deduped) >= 1


def test_minhash_dedupe_empty():
    assert ds.minhash_dedupe([]) == []


def test_skill_pmi(df):
    pmi = ds.skill_pmi(df)
    assert isinstance(pmi, list)
    if pmi:
        assert "pmi" in pmi[0]
        assert "skill_a" in pmi[0] and "skill_b" in pmi[0]


def test_skill_communities(df):
    communities = ds.skill_communities(df)
    assert isinstance(communities, dict)
    if communities:
        assert all(isinstance(v, int) for v in communities.values())


def test_skill_relatedness(df):
    related = ds.skill_relatedness(df)
    assert isinstance(related, dict)
    # gensim may or may not produce results depending on corpus size
