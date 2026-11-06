import pytest

from modules import ingestion


class FakeClient:
    """Stands in for JSearchClient so tests never hit the network."""

    def __init__(self, items):
        self.items = items
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.items

    def remaining_quota(self):
        return 199


def fake_item(**overrides):
    item = {
        "job_id": "abc123",
        "job_title": "Senior Python Developer",
        "employer_name": "Acme Corp",
        "job_city": None,
        "job_state": None,
        "job_country": "IN",
        "job_location": "Bengaluru, Karnataka, India",
        "job_description": "We need 3-5 years of experience with Python, Django and PostgreSQL.",
        "job_apply_link": "https://example.com/apply",
        "job_employment_type": "FULLTIME",
        "job_is_remote": False,
        "job_min_salary": 1200000,
        "job_max_salary": 1800000,
        "job_salary_currency": "INR",
        "job_salary_period": "YEAR",
        "job_posted_at_datetime_utc": "2026-11-01T00:00:00.000Z",
        "job_highlights": {"Qualifications": ["Python", "Django"]},
    }
    item.update(overrides)
    return item


def test_salary_fields_ignored():
    # Salary is no longer tracked; normalize_jsearch_item must not emit it.
    record = ingestion.normalize_jsearch_item(fake_item())
    assert "salary_lpa" not in record
    assert "salary_min" not in record


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Minimum 3+ years of experience", 3.0),
        ("3-5 years experience required", 4.0),
        ("12+ years", 12.0),
        ("No experience needed", None),
        ("50 years", None),
    ],
)
def test_parse_experience_years(text, expected):
    assert ingestion.parse_experience_years(text) == expected


def test_normalize_item_maps_fields():
    record = ingestion.normalize_jsearch_item(fake_item())

    assert record["job_id"] == "abc123"
    assert record["source"] == "jsearch"
    assert record["company"] == "Acme Corp"
    assert record["location"].startswith("Bengaluru")
    assert record["experience_years"] == 4.0
    assert record["posted_at"] == "2026-11-01"
    assert "salary_lpa" not in record


def test_normalize_item_infers_city_when_only_country_given():
    item = fake_item(
        job_location="India",
        job_description="Our office is in Pune. Python required.",
    )
    assert ingestion.normalize_jsearch_item(item)["location"] == "Pune"


def test_collect_extracts_skills():
    client = FakeClient([fake_item()])
    records, skills = ingestion.collect_jsearch(queries=["python developer"], client=client)

    assert len(records) == 1
    assert client.calls[0]["query"] == "python developer"
    canonical = {skill["skill_canonical"] for skill in skills["abc123"]}
    assert {"Python", "Django", "PostgreSQL"} <= canonical


def test_collect_deduplicates_job_ids():
    client = FakeClient([fake_item(), fake_item()])
    records, _ = ingestion.collect_jsearch(queries=["python"], client=client)
    assert len(records) == 1


def test_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "dry.db"))
    monkeypatch.setenv("ENABLE_JOBSPY", "false")

    summary = ingestion.run_ingest(
        queries=["python"],
        client=FakeClient([fake_item()]),
        dry_run=True,
        check_quota=False,
    )

    assert summary["fetched"] == 1
    assert summary["inserted"] == 0
    assert not (tmp_path / "dry.db").exists()


def test_run_ingest_writes_then_updates(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "live.db"))
    monkeypatch.setenv("ENABLE_JOBSPY", "false")
    monkeypatch.setenv("ENABLE_SKILL_EMBEDDINGS", "false")

    client = FakeClient([fake_item()])
    first = ingestion.run_ingest(queries=["python"], client=client, check_quota=False)
    assert first["inserted"] == 1

    second = ingestion.run_ingest(queries=["python"], client=client, check_quota=False)
    assert second["inserted"] == 0
    assert second["updated"] == 1

    from modules import store

    assert store.count_postings() == 1
    assert store.load_postings_dataframe().shape[0] >= 1


def test_cross_source_dedup(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "dedup.db"))
    monkeypatch.setenv("ENABLE_JOBSPY", "true")
    monkeypatch.setenv("ENABLE_SKILL_EMBEDDINGS", "false")

    client = FakeClient([fake_item(job_id="js-1")])

    jobspy_record = ingestion.normalize_jsearch_item(fake_item(job_id="jp-1"))
    jobspy_record["source"] = "jobspy:indeed"
    jobspy_record["job_id"] = "jobspy:jp-1"

    from unittest.mock import patch

    with patch(
        "modules.jobspy_adapter.collect_jobspy",
        return_value=([jobspy_record], {jobspy_record["job_id"]: []}),
    ):
        summary = ingestion.run_ingest(queries=["python"], client=client, check_quota=False)

    assert summary["fetched"] == 1

    from modules import store

    postings = store.fetch_postings()
    assert len(postings) == 1


def test_skill_text_includes_title_description_and_highlights():
    item = fake_item()
    record = ingestion.normalize_jsearch_item(item)
    text = ingestion.skill_text_for(item, record)

    assert "Senior Python Developer" in text
    assert "Django" in text
