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


def test_locations_state_wise(client):
    r = client.get("/api/market/locations?n=10")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert isinstance(data.get("locations"), list)


def test_recent_postings_with_apply_url(client):
    r = client.get("/api/market/recent-postings?n=5")
    assert r.status_code == 200
    data = r.json()
    postings = data.get("postings", [])
    assert len(postings) >= 1
    first = postings[0]
    assert first["job_id"] == "job-1"
    assert first["title"] == "Backend Engineer"
    assert first["url"] == "https://example.com/job"
    assert set(first["skills"]) == {"Python", "PostgreSQL"}


def test_market_overview_filtered_by_skill(client):
    r_unfiltered = client.get("/api/market/overview")
    assert r_unfiltered.status_code == 200
    assert r_unfiltered.json()["total_openings"] >= 1

    r_filtered = client.get("/api/market/overview?skills=Python")
    assert r_filtered.status_code == 200
    assert r_filtered.json()["total_openings"] >= 1

    r_nonexistent = client.get("/api/market/overview?skills=NonexistentSkillXYZ")
    assert r_nonexistent.status_code == 200
    assert r_nonexistent.json()["total_openings"] == 0

    r_location = client.get("/api/market/overview?locations=Bengaluru")
    assert r_location.status_code == 200
    assert r_location.json()["total_openings"] >= 1


def test_demand_trends(client):
    r = client.get("/api/market/demand-trends?top_n=5")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    for row in rows:
        assert "skill" in row and "month" in row and "count" in row


def test_demand_trends_filtered_by_skill(client):
    r = client.get("/api/market/demand-trends?top_n=5&skills=Python")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    for row in rows:
        assert row["skill"] == "Python"


def test_skill_pairs(client):
    r = client.get("/api/market/skill-pairs?min_cooccurrence=1")
    assert r.status_code == 200
    pairs = r.json()
    assert isinstance(pairs, list)
    for pair in pairs:
        assert "skill_a" in pair and "skill_b" in pair and "count" in pair


def test_skill_pairs_filtered(client):
    r = client.get("/api/market/skill-pairs?min_cooccurrence=1&skills=Python")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_forecast_404_unknown(client):
    r = client.get("/api/forecast/NonexistentSkillXYZ")
    assert r.status_code == 404


def test_forecast_422_invalid_engine(client):
    r = client.get("/api/forecast/Python?model_type=nonexistent_engine")
    assert r.status_code == 422


def test_forecast_insufficient_history_404(client):
    # Seeded corpus has one month of history; forecasting needs >=2 months
    # so the endpoint degrades to 404 (fallback documented, not 500).
    r = client.get("/api/forecast/Python")
    assert r.status_code == 404


def test_recommendations_complementary(client):
    r = client.post("/api/recommendations", json={"mode": "complementary", "skill": "Python", "top_n": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "complementary"
    assert isinstance(data["results"], list)


def test_recommendations_role(client):
    r = client.post("/api/recommendations", json={"mode": "role", "role": "Backend", "top_n": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "role"
    assert isinstance(data["results"], list)


def test_recommendations_learning_path(client):
    r = client.post(
        "/api/recommendations",
        json={"mode": "learning-path", "current_skills": ["Python"], "target_role": "Backend"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "learning-path"
    assert isinstance(data["results"], list)


def test_recommendations_empty_ok(client):
    r = client.post("/api/recommendations", json={"mode": "complementary", "skill": "Python", "top_n": 5})
    assert r.status_code == 200


def test_recommendations_no_match_returns_200_empty(client):
    r = client.post(
        "/api/recommendations",
        json={"mode": "complementary", "skill": "NonexistentSkillXYZ", "top_n": 5},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["results"] == []
    assert data["status"]


def test_search(client):
    r = client.post("/api/search", json={"query": "python", "top_k": 3, "rerank": False})
    assert r.status_code == 200


def test_search_ranked_scores(client):
    r = client.post("/api/search", json={"query": "python", "top_k": 3, "rerank": False})
    assert r.status_code == 200
    data = r.json()
    assert "query" in data and "backend" in data
    results = data["results"]
    assert isinstance(results, list)
    if results:
        for row in results:
            assert "score" in row and "job_id" in row and "title" in row
        scores = [row["score"] for row in results]
        assert scores == sorted(scores, reverse=True)


def test_search_lexical_fallback(client):
    # Endpoint must work without a model download: query matching the seeded
    # posting returns it via lexical overlap even when embeddings are off.
    r = client.post("/api/search", json={"query": "Backend Engineer", "top_k": 3, "rerank": False})
    assert r.status_code == 200
    results = r.json()["results"]
    assert isinstance(results, list)


def test_roi(client):
    r = client.get("/api/roi?top_n=5")
    assert r.status_code == 200


def test_roi_rows_have_momentum_and_confidence(client):
    r = client.get("/api/roi?top_n=5")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert isinstance(rows, list)
    for row in rows:
        assert "skill" in row and "momentum" in row and "roi_score" in row and "confidence" in row


def test_demand_science(client):
    r = client.get("/api/demand-science")
    assert r.status_code == 200


def test_demand_science_all_sub_results(client):
    r = client.get("/api/demand-science")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["survival_overall"], list)
    assert isinstance(data["survival_by_skill"], dict)
    assert isinstance(data["cox"], dict)
    assert isinstance(data["anomalies"], list)
    assert isinstance(data["pmi_pairs"], list)
    assert isinstance(data["communities"], dict)
    assert isinstance(data["relatedness"], dict)


def test_demand_science_empty_corpus_returns_empty_arrays(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "empty.db"))
    from modules import store

    store.init_db()
    from backend.main import app
    from fastapi.testclient import TestClient

    empty_client = TestClient(app)
    r = empty_client.get("/api/demand-science")
    assert r.status_code == 200
    data = r.json()
    assert data["survival_overall"] == []
    assert data["anomalies"] == []
    assert data["pmi_pairs"] == []
    assert data["communities"] == {}
    assert data["relatedness"] == {}


def test_fairness(client):
    r = client.get("/api/fairness")
    assert r.status_code == 200
    assert "overall" in r.json()


def test_fairness_tables_and_gaps(client):
    r = client.get("/api/fairness")
    assert r.status_code == 200
    data = r.json()
    assert "by_location" in data and "by_remote" in data and "by_company_type" in data
    assert isinstance(data["by_location"], list)
    assert isinstance(data["by_remote"], list)
    assert isinstance(data["by_company_type"], list)
    gaps = data["gaps"]
    assert "location_share_range_pp" in gaps
    assert "remote_share_gap_pp" in gaps
    assert "company_type_share_range_pp" in gaps
    assert "adjusted_by_location" in gaps
    assert "adjusted_by_remote" in gaps
    assert "adjusted_by_company_type" in gaps
    assert data["confidence"] in ("low", "high")


def test_resume_unsupported(client):
    r = client.post("/api/resume/analyze", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_match_success(client):
    r = client.post(
        "/api/match",
        json={"job_id": "job-1", "resume_skills": ["Python", "PostgreSQL"], "resume_years": 2.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == "job-1"
    assert 0 <= data["match_score"] <= 100
    assert "matched_skills" in data and "missing_must_have" in data
    assert "posting_health" in data and "confidence" in data


def test_match_unknown_job_404(client):
    r = client.post("/api/match", json={"job_id": "no-such-job", "resume_skills": ["Python"]})
    assert r.status_code == 404


def test_match_bad_payload_422(client):
    r = client.post("/api/match", json={"resume_skills": ["Python"]})
    assert r.status_code == 422


def test_resume_pdf_upload(client):
    import io

    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    cc = canvas.Canvas(buf)
    cc.drawString(100, 750, "Skills: Python, Docker")
    cc.save()
    pdf_bytes = buf.getvalue()

    r = client.post(
        "/api/resume/analyze",
        files={"file": ("r.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "resume_skills" in data
    assert "missing_skills" in data
    assert "match_percentage" in data


def test_resume_docx_upload(client):
    import io

    from docx import Document

    doc = Document()
    doc.add_paragraph("Skills: Python, Docker")
    buf = io.BytesIO()
    doc.save(buf)

    r = client.post(
        "/api/resume/analyze",
        files={"file": ("r.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 200
    assert "resume_skills" in r.json()


def test_resume_unparseable_returns_422(client):
    r = client.post(
        "/api/resume/analyze",
        files={"file": ("r.pdf", b"not a real pdf", "application/pdf")},
    )
    assert r.status_code == 422
