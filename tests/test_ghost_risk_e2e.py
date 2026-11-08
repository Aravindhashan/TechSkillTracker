"""Slice 3 end-to-end (ticket 42): ingest -> events -> risk -> badge payload.

Stale postings MUST out-score fresh ones, and the search endpoint must carry
the badge payload the frontend renders.
"""

from datetime import datetime, timedelta, timezone

import pytest

from modules import ghost_risk, store


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "e2e.db"))
    store.init_db()
    return tmp_path / "e2e.db"


def _record(job_id, **overrides):
    record = {
        "job_id": job_id,
        "source": "test",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Python and Docker",
        "url": "https://example.com/job",
        "employment_type": "FULLTIME",
        "is_remote": False,
        "experience_years": 3.0,
        "posted_at": "2026-11-01",
    }
    record.update(overrides)
    return record


def _risk(job_id):
    posting = next(
        item for item in store.fetch_postings() if str(item["job_id"]) == job_id
    )
    return ghost_risk.ghost_risk_score(
        job_id,
        first_seen=posting["first_seen"],
        last_seen=posting["last_seen"],
        is_active=bool(posting["is_active"]),
    )


def test_ingest_logs_events_for_both(sqlite_db):
    store.upsert_postings([_record("fresh"), _record("stale")], {})
    assert store.fetch_posting_events("fresh") != []
    assert store.fetch_posting_events("stale") != []


def test_stale_scores_higher_than_fresh(sqlite_db):
    store.upsert_postings([_record("fresh"), _record("stale")], {})
    old = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0).isoformat()
    with store.get_connection() as conn:
        conn.cursor().execute(
            "UPDATE job_postings SET first_seen = ?, last_seen = ? WHERE job_id = 'stale'",
            (old, old),
        )
    store.close_stale_postings(days=7)

    fresh = _risk("fresh")
    stale = _risk("stale")
    assert stale["risk"] > fresh["risk"]
    assert stale["label"] == "high"
    assert fresh["label"] == "low"


def test_search_endpoint_carries_badge_payload(sqlite_db):
    from backend.main import app
    from fastapi.testclient import TestClient

    store.upsert_postings([_record("fresh")], {})
    client = TestClient(app)
    response = client.post("/api/search", json={"query": "python", "top_k": 3, "rerank": False})
    assert response.status_code == 200
    for row in response.json()["results"]:
        assert "ghost_risk" in row
        assert row["ghost_risk"]["label"] in ("low", "medium", "high")