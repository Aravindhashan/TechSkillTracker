import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ENABLE_CROSS_ENCODER", "0")

    from modules import store

    store.init_db()
    record = {
        "job_id": "job-1",
        "source": "jsearch",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Python and Postgres",
        "url": "https://example.com/job",
        "employment_type": "FULLTIME",
        "is_remote": False,
        "experience_years": 3.0,
        "posted_at": "2026-11-01",
    }
    skills = {
        "job-1": [
            {"skill_raw": "Python", "skill_canonical": "Python", "confidence": 1.0},
            {"skill_raw": "Postgres", "skill_canonical": "PostgreSQL", "confidence": 1.0},
        ]
    }
    store.upsert_postings([record], skills)

    from backend.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["backend"] == "sqlite"
    assert data["postings"] >= 1


def test_market_overview(client):
    r = client.get("/api/market/overview")
    assert r.status_code == 200
    data = r.json()
    assert "total_openings" in data
    assert data["total_openings"] >= 1


def test_top_skills(client):
    r = client.get("/api/market/top-skills?n=5")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, (list, dict))


def test_forecast_404_unknown(client):
    r = client.get("/api/forecast/NonexistentSkillXYZ")
    assert r.status_code == 404


def test_recommendations_empty_ok(client):
    r = client.post("/api/recommendations", json={"mode": "complementary", "skill": "Python", "top_n": 5})
    assert r.status_code == 200


def test_search(client):
    r = client.post("/api/search", json={"query": "python", "top_k": 3, "rerank": False})
    assert r.status_code == 200


def test_roi(client):
    r = client.get("/api/roi?top_n=5")
    assert r.status_code == 200


def test_demand_science(client):
    r = client.get("/api/demand-science")
    assert r.status_code == 200


def test_fairness(client):
    r = client.get("/api/fairness")
    assert r.status_code == 200
    assert "overall" in r.json()


def test_resume_unsupported(client):
    r = client.post("/api/resume/analyze", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415
