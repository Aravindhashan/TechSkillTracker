"""Free company-board ingests: Greenhouse + Lever + Ashby.

Unlike JSearch (aggregated, quota) and Jobspy (scraped, ToS-gray), these are
the companies' own **public job-board APIs** — no key, no quota, official
endpoints. That makes them the safest source for modern AI/ML roles, which
live on Greenhouse/Ashby boards and rarely surface under "software
developer" searches.

Shapes (verified against the live APIs):

* Greenhouse list: ``GET /v1/boards/{slug}/jobs`` -> ``{jobs: [...]}`` with
  ``id, title, absolute_url, location{name}, updated_at`` (no content).
  Detail: ``GET /v1/boards/{slug}/jobs/{id}`` -> same + ``content`` (HTML).
* Lever list: ``GET /v0/postings/{username}`` -> ``[{id, text, hostedUrl,
  categories{location, commitment}, description(HTML), createdAt}]``.
  NOTE: the public Lever endpoint returns 404 for several well-known slugs
  (``netflix``, ``leverage``, ``brex``). Boards that 404 are skipped.
* Ashby list: ``GET /posting-api/job-board/{name}`` -> ``{jobs: [...]}``
  with ``id, title, jobUrl, location(str), isRemote, publishedAt,
  descriptionHtml/descriptionPlain`` (full body inline, no detail call).

All three map onto the shared posting record shape used by
:mod:`modules.store`; the existing cross-source + MinHash dedup in
:func:`modules.ingestion.run_ingest` collapses overlaps with JSearch/Jobspy.

Off by default for the same reason Jobspy is: opt in with
``ENABLE_BOARDS=true`` (or ``--boards``) so quota-free runs stay explicit.
"""

from __future__ import annotations

import os
from typing import Iterable

import requests

from modules.ingestion import _clean_text, _stable_job_id, parse_experience_years

GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards"
LEVER_BASE = "https://api.lever.co/v0/postings"
ASHBY_BASE = "https://api.ashbyhq.com/posting-api/job-board"
REQUEST_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 20

DEFAULT_GREENHOUSE_SLUGS = (
    "stripe",
    "airbnb",
    "robinhood",
    "doordash",
    "twilio",
    "dropbox",
    "hubspot",
    "coinbase",
    "gitlab",
    "shopify",
)
# Lever public API is unreliable (see docstring); kept small and best-effort.
DEFAULT_LEVER_USERS = ("leverage",)
DEFAULT_ASHBY_BOARDS = ("openai",)

DEFAULT_BOARDS = {
    "greenhouse": DEFAULT_GREENHOUSE_SLUGS,
    "lever": DEFAULT_LEVER_USERS,
    "ashby": DEFAULT_ASHBY_BOARDS,
}

MAX_POSTINGS_PER_RUN = 100


def boards_enabled() -> bool:
    return os.getenv("ENABLE_BOARDS", "false").strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Normalizers (pure, unit-tested with fixture payloads)
# ---------------------------------------------------------------------------


def normalize_greenhouse_job(job: dict, detail: dict | None = None) -> dict:
    """Map one Greenhouse job (list item + optional detail) to a record."""
    detail = detail or {}
    job_id = str(job.get("id") or detail.get("id") or "")
    title = _clean_text(job.get("title") or detail.get("title"))
    company = _clean_text(job.get("company_name") or detail.get("company_name")) or "Unknown"
    location_obj = job.get("location") or detail.get("location") or {}
    location = _clean_text(location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj))
    description = _clean_text(detail.get("content") or job.get("content"))
    posted_at = str(detail.get("updated_at") or job.get("updated_at") or job.get("first_published") or "")[:10] or None
    return {
        "job_id": f"greenhouse:{job_id or _stable_job_id(title, company, location, posted_at or '')}",
        "source": "greenhouse",
        "title": title,
        "company": company,
        "location": location or "Unknown",
        "description": description,
        "url": detail.get("absolute_url") or job.get("absolute_url"),
        "employment_type": None,
        "is_remote": bool(detail.get("offices") and any("remote" in str(o).lower() for o in detail.get("offices", []))),
        "experience_years": parse_experience_years(description),
        "posted_at": posted_at,
        "raw": {**job, "detail_keys": sorted(detail.keys())} if detail else job,
    }


def normalize_lever_posting(posting: dict) -> dict:
    job_id = str(posting.get("id") or "")
    categories = posting.get("categories") or {}
    title = _clean_text(posting.get("text") or posting.get("title"))
    company = _clean_text(posting.get("company") or "") or "Unknown"
    location = _clean_text(categories.get("location") or posting.get("location") or "")
    description = _clean_text(posting.get("description"))
    created_at = posting.get("createdAt") or posting.get("updatedAt")
    posted_at = str(created_at)[:10] if created_at else None
    return {
        "job_id": f"lever:{job_id or _stable_job_id(title, company, location, posted_at or '')}",
        "source": "lever",
        "title": title,
        "company": company,
        "location": location or "Unknown",
        "description": description,
        "url": posting.get("hostedUrl"),
        "employment_type": _clean_text(categories.get("commitment")) or None,
        "is_remote": "remote" in location.lower(),
        "experience_years": parse_experience_years(description),
        "posted_at": posted_at,
        "raw": {key: value for key, value in posting.items() if key != "description"},
    }


def normalize_ashby_job(job: dict) -> dict:
    job_id = str(job.get("id") or "")
    title = _clean_text(job.get("title"))
    company = _clean_text(job.get("companyName") or job.get("team") or "") or "Unknown"
    location = _clean_text(job.get("location") or job.get("locationName") or "")
    description = _clean_text(job.get("descriptionHtml") or job.get("descriptionPlain") or "")
    posted_at = str(job.get("publishedAt") or "")[:10] or None
    return {
        "job_id": f"ashby:{job_id or _stable_job_id(title, company, location, posted_at or '')}",
        "source": "ashby",
        "title": title,
        "company": company,
        "location": location or "Unknown",
        "description": description,
        "url": job.get("jobUrl") or job.get("applyUrl"),
        "employment_type": _clean_text(job.get("employmentType")) or None,
        "is_remote": bool(job.get("isRemote")),
        "experience_years": parse_experience_years(description),
        "posted_at": posted_at,
        "raw": {key: value for key, value in job.items() if key != "descriptionHtml"},
    }


# ---------------------------------------------------------------------------
# Fetchers (session-injected for offline tests)
# ---------------------------------------------------------------------------


def _get_json(session, url: str):
    response = session.get(url, timeout=TIMEOUT_SECONDS, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def fetch_greenhouse(slug: str, session=None, fetch_details: bool = True) -> list[dict]:
    session = session or requests.Session()
    payload = _get_json(session, f"{GREENHOUSE_BASE}/{slug}/jobs")
    jobs = payload.get("jobs") or []
    if not fetch_details:
        return [normalize_greenhouse_job(job) for job in jobs]
    records = []
    for job in jobs:
        detail = None
        try:
            detail = _get_json(session, f"{GREENHOUSE_BASE}/{slug}/jobs/{job.get('id')}")
        except Exception:
            detail = None  # list payload still usable
        records.append(normalize_greenhouse_job(job, detail))
    return records


def fetch_lever(username: str, session=None) -> list[dict]:
    session = session or requests.Session()
    payload = _get_json(session, f"{LEVER_BASE}/{username}")
    items = payload if isinstance(payload, list) else []
    return [normalize_lever_posting(item) for item in items]


def fetch_ashby(board: str, session=None) -> list[dict]:
    session = session or requests.Session()
    payload = _get_json(session, f"{ASHBY_BASE}/{board}")
    jobs = payload.get("jobs") or []
    return [normalize_ashby_job(job) for job in jobs]


def collect_boards(
    boards: dict[str, Iterable[str]] | None = None,
    session=None,
    max_postings: int = MAX_POSTINGS_PER_RUN,
    fetch_details: bool = True,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Fetch every configured board; returns records + extracted skills.

    A dead board (404/unknown slug) is skipped, never fatal.
    """
    from modules.normalizer import SkillNormalizer

    session = session or requests.Session()
    boards = boards or DEFAULT_BOARDS
    normalizer = SkillNormalizer(load_model=False)
    records: list[dict] = []
    skills_by_job: dict[str, list[dict]] = {}
    seen: set[str] = set()

    fetchers = {
        "greenhouse": lambda slug: fetch_greenhouse(slug, session=session, fetch_details=fetch_details),
        "lever": lambda slug: fetch_lever(slug, session=session),
        "ashby": lambda slug: fetch_ashby(slug, session=session),
    }

    for source, slugs in boards.items():
        fetcher = fetchers.get(source)
        if fetcher is None:
            continue
        for slug in slugs:
            try:
                fetched = fetcher(slug)
            except Exception:
                continue  # dead board -> skip, keep the run alive
            for record in fetched:
                if record["job_id"] in seen:
                    continue
                seen.add(record["job_id"])
                records.append(record)
                skills_by_job[record["job_id"]] = normalizer.extract_skills_from_text(
                    f"{record['title']} {record['description']}"
                )
                if len(records) >= max_postings:
                    return records, skills_by_job

    return records, skills_by_job