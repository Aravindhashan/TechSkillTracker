"""Job ingestion from the JSearch (OpenWebNinja) API.

JSearch aggregates postings from Google Jobs, which includes LinkedIn,
Indeed and Glassdoor listings through a licensed API - no scraping, no ban
risk.  This module normalises those responses into the shared posting record
shape used by :mod:`modules.store`.

Usage::

    python -m modules.ingestion --queries "software developer" --dry-run
    python -m modules.ingestion --queries "python developer|data scientist"

Environment variables
---------------------
``JSEARCH_API_KEY``    required for live calls
``JSEARCH_BASE_URL``   defaults to ``https://api.openwebninja.com``
``JSEARCH_COUNTRY``    defaults to ``in`` (India)
``JSEARCH_QUERIES``    ``|``-separated default queries
``JSEARCH_NUM_PAGES``  pages per query (10 results per page), default 1
``ENABLE_JOBSPY``      ``true`` enables the optional Jobspy adapter
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Iterable

import requests

from modules import env  # noqa: F401  (loads .env before configuration is read)

DEFAULT_BASE_URL = "https://api.openwebninja.com"
USAGE_API_ID = "jsearch"
RESULTS_PER_PAGE = 10
REQUEST_INTERVAL_SECONDS = 1.5

_EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|\bplus\b)?\s*(?:-|to|–)?\s*(\d{1,2})?\s*(?:\+)?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class JSearchError(RuntimeError):
    pass


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(_HTML_TAG_RE.sub(" ", value))
    # JSearch sometimes returns replacement characters for dashes/arrows.
    text = text.replace("\ufffd", "-")
    return re.sub(r"\s+", " ", text).strip()


def _stable_job_id(*parts: str) -> str:
    payload = "|".join(part or "" for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


def parse_experience_years(text: str) -> float | None:
    """Best-effort extraction of required experience from a description."""
    if not text:
        return None
    match = _EXPERIENCE_RE.search(text)
    if not match:
        return None
    low = float(match.group(1))
    high = float(match.group(2)) if match.group(2) else low
    if high < low:
        low, high = high, low
    if high > 30:
        return None
    return round((low + high) / 2, 1)


INDIAN_CITIES = (
    "Bengaluru", "Bangalore", "Mumbai", "Pune", "Hyderabad", "Chennai", "Delhi",
    "New Delhi", "Noida", "Gurgaon", "Gurugram", "Kolkata", "Ahmedabad",
    "Jaipur", "Indore", "Coimbatore", "Kochi", "Chandigarh", "Trivandrum",
)


def _infer_city(text: str) -> str | None:
    for city in INDIAN_CITIES:
        if re.search(rf"(?<![A-Za-z]){re.escape(city)}(?![A-Za-z])", text or "", re.IGNORECASE):
            return city
    return None


def _format_location(item: dict, description: str = "") -> str:
    explicit = (item.get("job_location") or "").strip()
    city = item.get("job_city")
    state = item.get("job_state")

    if city:
        parts = [city, state, item.get("job_country")]
        return ", ".join(part for part in parts if part)

    inferred = _infer_city(description) or _infer_city(item.get("job_title") or "")
    if inferred:
        return inferred

    if explicit and explicit.upper() not in ("IN", "INDIA"):
        return explicit

    return explicit or state or (item.get("job_country") or "Unknown")


def normalize_jsearch_item(item: dict) -> dict:
    """Map one JSearch result onto the shared posting record shape."""
    title = _clean_text(item.get("job_title") or item.get("job_job_title"))
    company = _clean_text(item.get("employer_name")) or "Unknown"
    description = _clean_text(item.get("job_description"))
    location = _format_location(item, description)

    posted_at = item.get("job_posted_at_datetime_utc")
    if not posted_at and item.get("job_posted_at_timestamp"):
        posted_at = datetime.fromtimestamp(
            int(item["job_posted_at_timestamp"]), tz=timezone.utc
        ).isoformat()
    if posted_at:
        posted_at = str(posted_at)[:10]

    job_id = item.get("job_id") or _stable_job_id(title, company, location, posted_at or "")

    return {
        "job_id": str(job_id),
        "source": "jsearch",
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "url": item.get("job_apply_link") or item.get("job_google_link"),
        "employment_type": item.get("job_employment_type"),
        "is_remote": bool(item.get("job_is_remote")),
        "experience_years": parse_experience_years(description),
        "posted_at": posted_at,
        "raw": item,
    }


def skill_text_for(item: dict, record: dict) -> str:
    """Text used for skill extraction: title + description + highlights."""
    highlights = item.get("job_highlights") or {}
    highlight_text = " ".join(
        _clean_text(" ".join(value) if isinstance(value, list) else str(value))
        for value in highlights.values()
    )
    return f"{record.get('title') or ''} {record.get('description') or ''} {highlight_text}".strip()


class JSearchClient:
    """Small retrying client for the OpenWebNinja JSearch API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 4,
        session: requests.Session | None = None,
    ):
        self.api_key = (api_key or os.getenv("JSEARCH_API_KEY") or "").strip()
        self.base_url = (base_url or os.getenv("JSEARCH_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._last_request_at = 0.0

    def _headers(self) -> dict:
        if not self.api_key:
            raise JSearchError(
                "JSEARCH_API_KEY is not set. Put it in .env or export it in the environment."
            )
        return {"x-api-key": self.api_key, "Accept": "application/json"}

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < REQUEST_INTERVAL_SECONDS:
            time.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
        self._last_request_at = time.monotonic()

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                response = self.session.get(
                    url, params=params, headers=self._headers(), timeout=self.timeout
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2**attempt, 20))
                continue

            if response.status_code == 200:
                payload = response.json()
                if payload.get("status") not in (None, "OK"):
                    raise JSearchError(
                        f"JSearch returned status={payload.get('status')}: "
                        f"{payload.get('error') or payload.get('message')}"
                    )
                return payload

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 20)
                last_error = JSearchError(
                    f"JSearch HTTP {response.status_code} on attempt {attempt + 1}"
                )
                time.sleep(delay)
                continue

            body = response.text[:300].replace("\n", " ")
            raise JSearchError(f"JSearch HTTP {response.status_code}: {body}")

        raise JSearchError(f"JSearch request failed after {self.max_retries} attempts: {last_error}")

    def usage(self) -> dict:
        payload = self._get("/usage", {"api_id": USAGE_API_ID})
        return payload.get("data", {})

    def remaining_quota(self) -> int | None:
        try:
            data = self.usage()
        except Exception:
            return None
        for quota in data.get("quotas", []):
            if str(quota.get("name", "")).lower().startswith("request"):
                return int(quota.get("remaining", 0))
        return None

    def search(
        self,
        query: str,
        country: str = "in",
        page: int = 1,
        num_pages: int = 1,
        date_posted: str | None = None,
        employment_types: str | None = None,
        work_from_home: bool | None = None,
    ) -> list[dict]:
        params: dict = {
            "query": query,
            "page": page,
            "num_pages": num_pages,
            "country": country,
            "language": "en",
        }
        if date_posted:
            params["date_posted"] = date_posted
        if employment_types:
            params["employment_types"] = employment_types
        if work_from_home is not None:
            params["work_from_home"] = str(work_from_home).lower()

        payload = self._get("/jsearch/search", params)
        return payload.get("data") or []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


# Cross-source deduplication key: the same posting on JSearch and Jobspy
# collapses to one record so demand counts are not inflated.
def _cross_source_key(record: dict) -> str:
    import re

    def _norm(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

    return "|".join(
        _norm(record.get(field))
        for field in ("title", "company", "location")
    )


def _split_queries(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        value = os.getenv("JSEARCH_QUERIES", "software developer")
    if isinstance(value, str):
        queries = [part.strip() for part in re.split(r"[|;]", value) if part.strip()]
    else:
        queries = [str(part).strip() for part in value if str(part).strip()]
    return queries or ["software developer"]


def collect_jsearch(
    queries: Iterable[str] | str | None = None,
    country: str | None = None,
    num_pages: int | None = None,
    date_posted: str | None = None,
    client: JSearchClient | None = None,
    max_records: int = 500,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Fetch postings and their extracted skills.

    Returns ``(records, skills_by_job)`` ready for :func:`store.upsert_postings`.
    """
    from modules.normalizer import SkillNormalizer

    client = client or JSearchClient()
    country = country or os.getenv("JSEARCH_COUNTRY", "in")
    num_pages = num_pages or int(os.getenv("JSEARCH_NUM_PAGES", "1"))
    normalizer = SkillNormalizer(load_model=False)

    records: list[dict] = []
    skills_by_job: dict[str, list[dict]] = {}
    seen_ids: set[str] = set()

    for query in _split_queries(queries):
        results = client.search(
            query=query,
            country=country,
            num_pages=num_pages,
            date_posted=date_posted,
        )
        for item in results:
            record = normalize_jsearch_item(item)
            if record["job_id"] in seen_ids:
                continue
            seen_ids.add(record["job_id"])
            skill_text = skill_text_for(item, record)
            records.append(record)
            skills_by_job[record["job_id"]] = normalizer.extract_skills_from_text(skill_text)
            if len(records) >= max_records:
                break
        if len(records) >= max_records:
            break

    return records, skills_by_job


def run_ingest(
    queries: Iterable[str] | str | None = None,
    country: str | None = None,
    num_pages: int | None = None,
    date_posted: str | None = None,
    use_jobspy: bool | None = None,
    close_after_days: int = 14,
    dry_run: bool = False,
    check_quota: bool | None = None,
    client: JSearchClient | None = None,
) -> dict:
    """Full ingestion cycle: fetch -> normalise -> upsert -> close stale.

    ``check_quota`` costs one extra API request, so it is off by default.  At
    the 6-hour cadence (4 runs/day, one search each) the free 200-request
    monthly quota fits without probing it on every run.
    """
    from modules import store

    summary: dict = {
        "status": "success",
        "fetched": 0,
        "inserted": 0,
        "updated": 0,
        "skills": 0,
        "closed": 0,
        "sources": [],
        "quota_remaining": None,
        "dry_run": dry_run,
    }

    client = client or JSearchClient()
    if check_quota is None:
        check_quota = os.getenv("JSEARCH_CHECK_QUOTA", "false").lower() in ("1", "true", "yes")

    if check_quota:
        remaining = client.remaining_quota()
        summary["quota_remaining"] = remaining
        if remaining is not None and remaining <= 0:
            summary["status"] = "skipped_quota"
            if not dry_run:
                print("[ingest] JSearch quota exhausted - skipping this run.")
            return summary

    records, skills_by_job = collect_jsearch(
        queries=queries,
        country=country,
        num_pages=num_pages,
        date_posted=date_posted,
        client=client,
    )
    summary["sources"].append("jsearch")

    if use_jobspy is None:
        use_jobspy = os.getenv("ENABLE_JOBSPY", "").lower() in ("1", "true", "yes")

    if use_jobspy:
        try:
            from modules.jobspy_adapter import collect_jobspy

            jobspy_records, jobspy_skills = collect_jobspy()
            existing = {record["job_id"] for record in records}
            for record in jobspy_records:
                if record["job_id"] in existing:
                    continue
                records.append(record)
                skills_by_job[record["job_id"]] = jobspy_skills.get(record["job_id"], [])
            if jobspy_records:
                summary["sources"].append("jobspy")
        except Exception as exc:  # optional path must never break the run
            print(f"[ingest] Jobspy adapter skipped: {exc}", file=sys.stderr)

    # Cross-source dedup: the same posting on JSearch and Jobspy must not be
    # counted twice.  Keep the first record for each key.
    by_key: dict[str, tuple[dict, list[dict]]] = {}
    for record in records:
        key = _cross_source_key(record)
        skills = skills_by_job.get(record["job_id"], [])
        if key not in by_key:
            by_key[key] = (record, skills)
    records = [value[0] for value in by_key.values()]
    skills_by_job = {value[0]["job_id"]: value[1] for value in by_key.values()}

    # MinHash LSH dedup: collapse near-duplicate postings (paraphrased titles).
    try:
        from modules.demand_science import minhash_dedupe

        before = len(records)
        deduped_records = minhash_dedupe(records, threshold=0.85)
        if len(deduped_records) < before:
            kept_ids = {r["job_id"] for r in deduped_records}
            records = deduped_records
            skills_by_job = {jid: sk for jid, sk in skills_by_job.items() if jid in kept_ids}
    except Exception:
        pass

    summary["fetched"] = len(records)

    if dry_run:
        for record in records[:10]:
            print(
                f"  {record['title'] or '(no title)'} @ {record['company']} - "
                f"{record['location']} - skills={len(skills_by_job.get(record['job_id'], []))}"
            )
        print(f"[ingest] dry run: {len(records)} postings fetched, nothing written.")
        return summary

    store.init_db()
    use_embeddings = os.getenv("ENABLE_SKILL_EMBEDDINGS", "true").lower() not in ("0", "false", "no")
    try:
        from modules.normalizer import SkillNormalizer

        SkillNormalizer(load_model=use_embeddings).seed_store(with_embeddings=use_embeddings)
    except Exception as exc:
        print(f"[ingest] taxonomy seed skipped: {exc}", file=sys.stderr)

    run_id = store.start_ingest_run("jsearch")
    try:
        counts = store.upsert_postings(records, skills_by_job)
        summary.update(counts)
        # Closing is opt-in: a single narrow query sees only a handful of the
        # corpus, so marking everything else inactive would corrupt the
        # first_seen/last_seen history needed for survival analysis.
        if close_after_days and close_after_days > 0:
            summary["closed"] = store.close_stale_postings(days=close_after_days)
        store.finish_ingest_run(
            run_id,
            fetched=summary["fetched"],
            inserted=summary["inserted"],
            updated=summary["updated"],
            status="success",
        )
    except Exception as exc:
        store.finish_ingest_run(
            run_id,
            fetched=summary["fetched"],
            inserted=summary["inserted"],
            updated=summary["updated"],
            status="error",
            error=str(exc)[:500],
        )
        summary["status"] = "error"
        summary["error"] = str(exc)
        raise

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest job postings via JSearch")
    parser.add_argument("--queries", default=None, help="'|' or ';' separated search queries")
    parser.add_argument("--country", default=None, help="ISO country code, default in")
    parser.add_argument("--num-pages", type=int, default=None, help="pages per query (10 per page)")
    parser.add_argument("--date-posted", default=None, help="all | today | 3days | week | month")
    parser.add_argument("--jobspy", action="store_true", help="also run the opt-in Jobspy scraper")
    parser.add_argument("--close-after-days", type=int, default=0,
                        help="mark postings unseen for N days inactive; 0 disables (default)")
    parser.add_argument("--check-quota", action="store_true", help="probe /usage first (costs a request)")
    parser.add_argument("--dry-run", action="store_true", help="fetch but do not write")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    try:
        summary = run_ingest(
            queries=args.queries,
            country=args.country,
            num_pages=args.num_pages,
            date_posted=args.date_posted,
            use_jobspy=args.jobspy or None,
            close_after_days=args.close_after_days,
            dry_run=args.dry_run,
            check_quota=args.check_quota or None,
        )
    except JSearchError as exc:
        print(f"[ingest] failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        print(
            "[ingest] {status}: fetched={fetched} inserted={inserted} "
            "updated={updated} skills={skills} closed={closed} quota_left={quota_remaining}".format(
                **summary
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
