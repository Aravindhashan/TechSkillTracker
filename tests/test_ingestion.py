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


def test_salary_conversion_to_lpa():
    assert ingestion.salary_to_lpa(1200000, 1800000, "INR", "YEAR") == 18.0
    assert ingestion.salary_to_lpa(100000, 150000, "INR", "MONTH") == 18.0
    assert ingestion.salary_to_lpa(100000, 150000, "USD", "YEAR") is None


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
    assert record["salary_lpa"] == 18.0
    assert record["experience_years"] == 4.0
    assert record["posted_at"] == "2026-11-01"
    assert "_skill_text" not in record


def test_skill_text_includes_title_description_and_highlights():
    item = fake_item()
    record = ingestion.normalize_jsearch_item(item)
    text = ingestion.skill_text_for(item, record)

    assert "Senior Python Developer" in text
    assert "Django" in text
    assert "Qualifications" not in text  # keys are not part of the skill text


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


def test_cross_source_dedup_prefers_salary(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "dedup.db"))
    monkeypatch.setenv("ENABLE_JOBSPY", "true")
    monkeypatch.setenv("ENABLE_SKILL_EMBEDDINGS", "false")

    no_salary_item = fake_item(job_id="js-1")
    no_salary_item["job_min_salary"] = None
    no_salary_item["job_max_salary"] = None
    no_salary_item["job_salary_currency"] = None
    client = FakeClient([no_salary_item])

    jobspy_record = ingestion.normalize_jsearch_item(fake_item(job_id="jp-1"))
    jobspy_record["source"] = "jobspy:indeed"
    jobspy_record["job_id"] = "jobspy:jp-1"
    jobspy_record["salary_lpa"] = 18.0
    jobspy_record["salary_min"] = 1200000
    jobspy_record["salary_max"] = 1800000
    jobspy_record["salary_currency"] = "INR"
    jobspy_record["salary_period"] = "YEAR"

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
    assert postings[0]["salary_lpa"] == 18.0
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
