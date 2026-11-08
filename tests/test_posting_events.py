from datetime import datetime, timedelta, timezone

import pytest

from modules import store


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "events.db"))
    store.init_db()
    return tmp_path / "events.db"


def _record(job_id="ev-1", **overrides):
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


def test_seen_logged_on_first_insert(sqlite_db):
    store.upsert_postings([_record()], {})
    events = store.fetch_posting_events("ev-1")
    assert [event["event_type"] for event in events] == ["seen"]


def test_reposted_logged_on_reactivation(sqlite_db):
    store.upsert_postings([_record()], {})
    old = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0).isoformat()
    with store.get_connection() as conn:
        conn.cursor().execute(
            "UPDATE job_postings SET last_seen = ? WHERE job_id = 'ev-1'", (old,)
        )
    store.close_stale_postings(days=7)

    store.upsert_postings([_record()], {})
    events = store.fetch_posting_events("ev-1")
    types = [event["event_type"] for event in events]
    assert "closed" in types
    assert types[-1] == "reposted"


def test_closed_logged_when_stale(sqlite_db):
    store.upsert_postings([_record()], {})
    old = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0).isoformat()
    with store.get_connection() as conn:
        conn.cursor().execute(
            "UPDATE job_postings SET last_seen = ? WHERE job_id = 'ev-1'", (old,)
        )
    store.close_stale_postings(days=7)
    types = [event["event_type"] for event in store.fetch_posting_events("ev-1")]
    assert types == ["seen", "closed"]


def test_backfill_seeds_seen_for_existing_postings(sqlite_db):
    store.upsert_postings([_record()], {})
    with store.get_connection() as conn:
        conn.cursor().execute("DELETE FROM posting_events")
    assert store.fetch_posting_events("ev-1") == []

    seeded = store.backfill_posting_events()
    assert seeded >= 1
    events = store.fetch_posting_events("ev-1")
    assert events and events[0]["event_type"] == "seen"

    # Idempotent: second backfill adds nothing.
    assert store.backfill_posting_events() == 0