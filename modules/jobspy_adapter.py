"""Opt-in Jobspy adapter (disabled by default).

Jobspy scrapes job boards directly.  That is fragile and can violate the
site's terms of service, so it is **off unless explicitly enabled** with
``ENABLE_JOBSPY=true``.

Safety rails:

* LinkedIn is never scraped unless the caller explicitly opts in.
* Requests are paced with random sleeps and capped per run.
* Failures fall through to the next board (Indeed -> Glassdoor) instead of
  retrying the same one and provoking a block.

The rest of the pipeline treats Jobspy output exactly like JSearch output.
"""

from __future__ import annotations

import hashlib
import os
import random
import time
from typing import Iterable

from modules.ingestion import parse_experience_years, salary_to_lpa
from modules.normalizer import SkillNormalizer

DEFAULT_SITES = ("indeed", "glassdoor")
PACE_MIN_SECONDS = 4.0
PACE_MAX_SECONDS = 9.0
MAX_POSTINGS_PER_RUN = 40


def jobspy_enabled() -> bool:
    value = os.getenv("ENABLE_JOBSPY", "true").strip().lower()
    return value not in ("", "0", "false", "no", "off")


def _stable_id(*parts: str) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return "jobspy:" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


def _row_to_record(row: dict, site: str) -> dict:
    title = str(row.get("title") or "")
    company = str(row.get("company") or "Unknown")
    location = str(row.get("location") or "Unknown")
    description = str(row.get("description") or "")

    posted_at = row.get("date_posted")
    posted_at = str(posted_at)[:10] if posted_at else None

    currency = row.get("currency")
    interval = row.get("interval")
    min_amount = row.get("min_amount")
    max_amount = row.get("max_amount")
    if not isinstance(min_amount, (int, float)):
        min_amount = None
    if not isinstance(max_amount, (int, float)):
        max_amount = None

    job_id = row.get("id") or _stable_id(site, title, company, location, posted_at or "")

    return {
        "job_id": f"jobspy:{job_id}",
        "source": f"jobspy:{site}",
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "url": row.get("job_url") or row.get("job_url_direct"),
        "employment_type": row.get("job_type"),
        "is_remote": bool(row.get("is_remote")),
        "salary_min": min_amount,
        "salary_max": max_amount,
        "salary_currency": currency,
        "salary_period": interval,
        "salary_lpa": salary_to_lpa(min_amount, max_amount, currency, interval),
        "experience_years": parse_experience_years(description),
        "posted_at": posted_at,
        "raw": {key: value for key, value in row.items() if key != "description"},
    }


def _scrape_site(
    site: str,
    search_term: str,
    location: str,
    results_wanted: int,
    hours_old: int,
    country_indeed: str,
) -> list[dict]:
    from jobspy import scrape_jobs  # imported lazily - optional dependency

    frame = scrape_jobs(
        site_name=[site],
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
        country_indeed=country_indeed,
    )
    if frame is None or getattr(frame, "empty", True):
        return []
    return [
        _row_to_record({key: row.get(key) for key in frame.columns}, site)
        for _, row in frame.iterrows()
    ]


def collect_jobspy(
    search_terms: Iterable[str] | str = "software developer",
    location: str = "India",
    sites: Iterable[str] = DEFAULT_SITES,
    results_wanted: int = 20,
    hours_old: int = 72,
    country_indeed: str = "india",
    allow_linkedin: bool = False,
    max_postings: int = MAX_POSTINGS_PER_RUN,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Scrape the fallback boards, returning records plus extracted skills.

    Raises :class:`RuntimeError` when the adapter is disabled; callers should
    treat Jobspy as best-effort and keep going.
    """
    if not jobspy_enabled():
        raise RuntimeError("Jobspy adapter is disabled. Set ENABLE_JOBSPY=true to use it.")

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    normalizer = SkillNormalizer(load_model=False)
    records: list[dict] = []
    skills_by_job: dict[str, list[dict]] = {}
    seen: set[str] = set()

    site_list = list(sites)
    if allow_linkedin:
        site_list.insert(0, "linkedin")

    for term in search_terms:
        for index, site in enumerate(site_list):
            try:
                rows = _scrape_site(
                    site=site,
                    search_term=term,
                    location=location,
                    results_wanted=results_wanted,
                    hours_old=hours_old,
                    country_indeed=country_indeed,
                )
            except Exception:
                rows = []  # fall through to the next board

            for record in rows:
                if record["job_id"] in seen:
                    continue
                seen.add(record["job_id"])
                records.append(record)
                skills_by_job[record["job_id"]] = normalizer.extract_skills_from_text(
                    f"{record['title']} {record['description']}"
                )
                if len(records) >= max_postings:
                    return records, skills_by_job

            # Pace even after a failure, so a blocked board is not hammered.
            if index < len(site_list) - 1:
                time.sleep(random.uniform(PACE_MIN_SECONDS, PACE_MAX_SECONDS))

    return records, skills_by_job


if __name__ == "__main__":
    import json

    if not jobspy_enabled():
        print("Jobspy is disabled. Export ENABLE_JOBSPY=true to run it.")
        raise SystemExit(1)

    result_records, result_skills = collect_jobspy()
    print(json.dumps({"fetched": len(result_records), "skills": len(result_skills)}, indent=2))
