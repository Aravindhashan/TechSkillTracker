# 09: Data ingestion and Postgres store

**What to build:** Replace the static CSV pipeline with a scheduled ingestion job that pulls job postings from a legal API (Adzuna or JSearch) every 6 hours, dedupes by job ID, tracks first_seen/last_seen, and persists to Neon Postgres (SQLite locally). Skill strings are normalized via sentence-transformer embeddings before storage.

**Blocked by:** None (can start immediately)

**Status:** implemented (2026-11-07)

- [x] Create Postgres schema (job_postings, resume_jobs, skill_taxonomy) and SQLite mirror for local dev
- [x] Implement Adzuna/JSearch ingestion client with retry + rate-limit handling
- [x] Add Jobspy opt-in scraper (off by default) with stealth pacing, fallback to Indeed/Glassdoor
- [x] Add 6-hour GitHub Actions cron that runs ingestion and upserts by job_id
- [x] Skill normalization: all-MiniLM-L6-v2 embeddings map raw skill strings to canonical taxonomy
- [x] Track first_seen/last_seen per posting for survival analysis later

**Implemented by:** `modules/store.py`, `modules/ingestion.py`, `modules/jobspy_adapter.py`,
`modules/normalizer.py`, `modules/env.py`, `modules/data_loader.py`,
`.github/workflows/ingest.yml`, `tests/test_{store,normalizer,ingestion}.py`.

**Notes:** JSearch's free plan is 200 requests/month; the run cadence uses one search
per 6-hour run (~120/month). Indian listings usually omit salary, so missing salaries
are stored as `NULL` and the dashboard reports `N/A` rather than dropping postings.
The app keeps a sidebar data-source switch so the bundled CSV stays usable.
