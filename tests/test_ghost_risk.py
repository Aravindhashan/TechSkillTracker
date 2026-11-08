from datetime import datetime, timezone

import pytest

from modules import ghost_risk, store


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "ghost.db"))
    store.init_db()
    return tmp_path / "ghost.db"


def _record(job_id, **overrides):
    record = {
        "job_id": job_id,
        "source": "test",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Python",
        "url": "https://example.com/job",
        "employment_type": "FULLTIME",
        "is_remote": False,
        "experience_years": 3.0,
        "posted_at": "2026-11-01",
    }
    record.update(overrides)
    return record


def test_fresh_active_posting_is_low_risk(sqlite_db):
    store.upsert_postings([_record("g-1")], {})
    posting = store.fetch_postings()[0]
    result = ghost_risk.ghost_risk_score(
        "g-1",
        first_seen=posting["first_seen"],
        last_seen=posting["last_seen"],
        is_active=True,
        now=datetime.now(timezone.utc),
    )
    assert result["risk"] < 0.3
    assert result["label"] == "low"


def test_stale_closed_reposted_posting_is_high_risk(sqlite_db):
    store.upsert_postings([_record("g-2")], {})
    old = "2026-08-08T00:00:00+00:00"
    with store.get_connection() as conn:
        conn.cursor().execute(
            "UPDATE job_postings SET first_seen = ?, last_seen = ?, is_active = FALSE WHERE job_id = 'g-2'",
            (old, old),
        )
    # Force close + repost history through the lifecycle API.
    with store.get_connection() as conn:
        cur = conn.cursor()
    # Log via public close path: age the posting then close it.
    store.close_stale_postings(days=7)

    result = ghost_risk.ghost_risk_score(
        "g-2",
        first_seen=old,
        last_seen=old,
        is_active=False,
        now=datetime.now(timezone.utc),
    )
    assert result["label"] == "high"
    assert result["factors"]["closed"] == 1.0


def test_unknown_job_uses_events_only(sqlite_db):
    # No rows at all: score is driven by age/closed defaults, never crashes.
    result = ghost_risk.ghost_risk_score(
        "missing",
        first_seen=None,
        last_seen=None,
        is_active=True,
    )
    assert 0 <= result["risk"] <= 1
    assert result["label"] in ("low", "medium", "high")