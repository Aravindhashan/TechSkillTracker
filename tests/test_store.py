from datetime import datetime, timedelta, timezone

import pytest

from modules import store


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    store.init_db()
    return tmp_path / "test.db"


def _record(job_id: str = "job-1", **overrides) -> dict:
    record = {
        "job_id": job_id,
        "source": "jsearch",
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Python and Postgres",
        "url": "https://example.com/job",
        "employment_type": "FULLTIME",
        "is_remote": False,
        "salary_min": 1200000,
        "salary_max": 1800000,
        "salary_currency": "INR",
        "salary_period": "YEAR",
        "salary_lpa": 18.0,
        "experience_years": 3.0,
        "posted_at": "2026-11-01",
    }
    record.update(overrides)
    return record


def _skills():
    return {
        "job-1": [
            {"skill_raw": "Python", "skill_canonical": "Python", "confidence": 1.0},
            {"skill_raw": "Postgres", "skill_canonical": "PostgreSQL", "confidence": 1.0},
        ]
    }


def test_upsert_inserts_then_updates(sqlite_db):
    first = store.upsert_postings([_record()], _skills())
    assert first == {"inserted": 1, "updated": 0, "skills": 2}

    second = store.upsert_postings([_record()], _skills())
    assert second["inserted"] == 0
    assert second["updated"] == 1


def test_first_seen_is_preserved_and_last_seen_moves(sqlite_db):
    store.upsert_postings([_record()], _skills())
    with store.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT first_seen, last_seen FROM job_postings WHERE job_id = 'job-1'")
        first_seen, last_seen = cur.fetchone()

    old = (datetime.now(timezone.utc) - timedelta(days=10)).replace(microsecond=0).isoformat()
    with store.get_connection() as conn:
        conn.cursor().execute(
            "UPDATE job_postings SET first_seen = ?, last_seen = ? WHERE job_id = 'job-1'",
            (old, old),
        )

    store.upsert_postings([_record()], _skills())
    with store.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT first_seen, last_seen FROM job_postings WHERE job_id = 'job-1'")
        new_first, new_last = cur.fetchone()

    assert new_first == old
    # last_seen must be refreshed to (at least) now, not left at the old value
    assert datetime.fromisoformat(new_last) > datetime.fromisoformat(old)


def test_upsert_only_fills_missing_fields(sqlite_db):
    store.upsert_postings([_record()], _skills())
    store.upsert_postings([_record(title="Updated Title", company=None)], {})
    rows = store.fetch_postings()
    assert rows[0]["title"] == "Updated Title"
    # None must not blank out the stored company
    assert rows[0]["company"] == "Acme"


def test_load_dataframe_matches_legacy_columns(sqlite_db):
    store.upsert_postings([_record()], _skills())
    frame = store.load_postings_dataframe()

    assert list(frame.columns) == [
        "Job ID",
        "Job Title",
        "Tech Skill",
        "Company",
        "Location",
        "Experience Required (in years)",
        "Date Posted",
        "first_seen",
        "last_seen",
        "is_active",
    ]
    assert len(frame) == 2  # one row per skill
    assert set(frame["Tech Skill"]) == {"Python", "PostgreSQL"}


def test_dataframe_keeps_postings_with_mixed_date_formats(sqlite_db):
    store.upsert_postings(
        [
            _record("job-date", posted_at="2026-11-01"),
            _record("job-timestamp", posted_at=None),
        ],
        {},
    )
    frame = store.load_postings_dataframe()

    assert set(frame["Job ID"]) == {"job-date", "job-timestamp"}
    assert frame["Date Posted"].notna().all()


def test_fetch_postings_with_skills_attaches_canonical_skills(sqlite_db):
    store.upsert_postings([_record()], _skills())

    rows = store.fetch_postings_with_skills()

    assert len(rows) == 1
    assert rows[0]["description"] == "Python and Postgres"
    assert rows[0]["skills"] == ["PostgreSQL", "Python"]


def test_close_stale_postings_marks_unseen_rows(sqlite_db):
    store.upsert_postings([_record()], _skills())
    old = (datetime.now(timezone.utc) - timedelta(days=30)).replace(microsecond=0).isoformat()
    with store.get_connection() as conn:
        conn.cursor().execute("UPDATE job_postings SET last_seen = ?", (old,))

    assert store.close_stale_postings(days=7) == 1
    rows = store.fetch_postings(active_only=True)
    assert rows == []


def test_ingest_run_and_data_age(sqlite_db):
    run_id = store.start_ingest_run("test")
    store.finish_ingest_run(run_id, fetched=1, inserted=1, updated=0)

    latest = store.latest_ingest_run()
    assert latest["status"] == "success"
    assert latest["fetched"] == 1

    store.upsert_postings([_record()], _skills())
    age = store.data_age_hours()
    assert age is not None and age < 1


def test_taxonomy_roundtrip(sqlite_db):
    saved = store.save_skill_taxonomy(
        [{"canonical": "React", "aliases": ["ReactJS", "React.js"]}]
    )
    assert saved == 1
    entries = store.fetch_skill_taxonomy()
    assert entries[0]["canonical"] == "React"
    assert "ReactJS" in entries[0]["aliases"]


def test_store_available_does_not_create_a_database(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(path))

    assert store.store_available() is False
    assert not path.exists()
