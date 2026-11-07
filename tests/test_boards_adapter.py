"""Boards adapter tests — offline, fixture payloads only (no network)."""

from unittest.mock import Mock

import pytest

from modules import boards_adapter, ingestion


def _greenhouse_list():
    return {
        "jobs": [
            {
                "id": 123,
                "title": "Machine Learning Engineer",
                "absolute_url": "https://stripe.com/jobs/search?gh_jid=123",
                "location": {"name": "Remote"},
                "company_name": "Stripe",
                "updated_at": "2026-11-05T10:00:00Z",
            }
        ]
    }


def _greenhouse_detail():
    return {
        "id": 123,
        "title": "Machine Learning Engineer",
        "company_name": "Stripe",
        "location": {"name": "Remote"},
        "content": "<p>Python and PyTorch required.</p>",
        "updated_at": "2026-11-05T10:00:00Z",
        "absolute_url": "https://stripe.com/jobs/search?gh_jid=123",
    }


def _lever_list():
    return [
        {
            "id": "abc",
            "text": "Backend Engineer",
            "hostedUrl": "https://jobs.lever.co/acme/abc",
            "categories": {"location": "Remote", "commitment": "Full-time"},
            "description": "<p>Go and Kubernetes required.</p>",
            "createdAt": "2026-11-04T00:00:00Z",
        }
    ]


def _ashby_list():
    return {
        "jobs": [
            {
                "id": "ash-1",
                "title": "Research Engineer",
                "jobUrl": "https://jobs.ashbyhq.com/openai/ash-1",
                "location": "San Francisco",
                "publishedAt": "2026-11-05T00:00:00Z",
                "isRemote": False,
                "descriptionHtml": "<p>Python research required.</p>",
            }
        ]
    }


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        response = Mock()
        payload = self.routes[url]
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        return response


def test_normalize_greenhouse_maps_fields_and_strips_html():
    record = boards_adapter.normalize_greenhouse_job(_greenhouse_list()["jobs"][0], _greenhouse_detail())
    assert record["job_id"] == "greenhouse:123"
    assert record["source"] == "greenhouse"
    assert record["title"] == "Machine Learning Engineer"
    assert record["company"] == "Stripe"
    assert record["location"] == "Remote"
    assert record["description"] == "Python and PyTorch required."
    assert "salary" not in str(record).lower()


def test_normalize_lever_maps_fields():
    record = boards_adapter.normalize_lever_posting(_lever_list()[0])
    assert record["job_id"] == "lever:abc"
    assert record["source"] == "lever"
    assert record["title"] == "Backend Engineer"
    assert record["employment_type"] == "Full-time"
    assert record["url"] == "https://jobs.lever.co/acme/abc"


def test_normalize_ashby_maps_fields():
    record = boards_adapter.normalize_ashby_job(_ashby_list()["jobs"][0])
    assert record["job_id"] == "ashby:ash-1"
    assert record["source"] == "ashby"
    assert record["location"] == "San Francisco"
    assert record["description"] == "Python research required."


def test_collect_boards_wires_all_three_with_dedupe():
    greenhouse_url = f"{boards_adapter.GREENHOUSE_BASE}/stripe/jobs"
    greenhouse_detail = f"{boards_adapter.GREENHOUSE_BASE}/stripe/jobs/123"
    lever_url = f"{boards_adapter.LEVER_BASE}/leverage"
    ashby_url = f"{boards_adapter.ASHBY_BASE}/openai"

    session = FakeSession(
        {
            greenhouse_url: _greenhouse_list(),
            greenhouse_detail: _greenhouse_detail(),
            lever_url: [],
            ashby_url: _ashby_list(),
        }
    )

    records, skills_by_job = boards_adapter.collect_boards(session=session)
    ids = {record["job_id"] for record in records}
    assert "greenhouse:123" in ids
    assert "ashby:ash-1" in ids
    assert skills_by_job
    # Same job twice in one board collapses to one record.
    assert len(records) == len(ids)


def test_collect_boards_skips_dead_board():
    class DeadSession:
        def get(self, url, **kwargs):
            response = Mock()
            response.raise_for_status.side_effect = Exception("404")
            return response

    records, _ = boards_adapter.collect_boards(
        boards={"greenhouse": ("no-such-slug",)},
        session=DeadSession(),
    )
    assert records == []


def test_run_ingest_merges_boards_records(tmp_path, monkeypatch):
    class FakeClient:
        def __init__(self, items):
            self.items = items

        def search(self, **kwargs):
            return self.items

        def remaining_quota(self):
            return 199

    def fake_item():
        return {
            "job_id": "abc123",
            "job_title": "Senior Python Developer",
            "employer_name": "Acme Corp",
            "job_city": None,
            "job_state": None,
            "job_country": "IN",
            "job_location": "Bengaluru, Karnataka, India",
            "job_description": "We need 3-5 years of experience with Python.",
            "job_apply_link": "https://example.com/apply",
            "job_employment_type": "FULLTIME",
            "job_is_remote": False,
            "job_posted_at_datetime_utc": "2026-11-01T00:00:00.000Z",
            "job_highlights": {},
        }

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "boards.db"))
    monkeypatch.setenv("ENABLE_JOBSPY", "false")
    monkeypatch.setenv("ENABLE_SKILL_EMBEDDINGS", "false")

    board_record = boards_adapter.normalize_greenhouse_job(
        _greenhouse_list()["jobs"][0], _greenhouse_detail()
    )
    board_skills = {"greenhouse:123": [{"skill_raw": "PyTorch", "skill_canonical": "PyTorch", "confidence": 1.0}]}

    from unittest.mock import patch

    with patch(
        "modules.boards_adapter.collect_boards",
        return_value=([board_record], board_skills),
    ):
        summary = ingestion.run_ingest(
            queries=["python"],
            client=FakeClient([fake_item()]),
            use_boards=True,
            check_quota=False,
        )

    assert summary["fetched"] == 2
    assert "boards" in summary["sources"]

    from modules import store

    postings = store.fetch_postings()
    assert len(postings) == 2
    assert any(str(row["source"]) == "greenhouse" for row in postings)