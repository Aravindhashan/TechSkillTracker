"""Persistence layer for job postings.

Works against Neon/Postgres in production (set ``DATABASE_URL``) and a local
SQLite file in development.  Both backends share one schema and one API so the
rest of the app never has to care which one is active.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Iterator

from modules import env  # noqa: F401  (loads .env before configuration is read)

DEFAULT_SQLITE_PATH = os.path.join("data", "techskill.db")

POSTGRES_PREFIXES = ("postgres://", "postgresql://")


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------


def database_url() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def use_postgres() -> bool:
    return database_url().startswith(POSTGRES_PREFIXES)


def sqlite_path() -> str:
    return os.getenv("SQLITE_PATH") or DEFAULT_SQLITE_PATH


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def get_connection() -> Iterator[Any]:
    """Yield a DB-API connection, committing on success and always closing."""
    if use_postgres():
        import psycopg2  # imported lazily so SQLite users need no driver

        conn = psycopg2.connect(database_url())
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        path = sqlite_path()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _cursor(conn: Any) -> Any:
    if use_postgres():
        from psycopg2.extras import RealDictCursor

        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def _ph() -> str:
    """Placeholder token for the active backend."""
    return "%s" if use_postgres() else "?"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS job_postings (
        job_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        title TEXT,
        company TEXT,
        location TEXT,
        description TEXT,
        url TEXT,
        employment_type TEXT,
        is_remote BOOLEAN DEFAULT FALSE,
        salary_min DOUBLE PRECISION,
        salary_max DOUBLE PRECISION,
        salary_currency TEXT,
        salary_period TEXT,
        salary_lpa DOUBLE PRECISION,
        experience_years DOUBLE PRECISION,
        posted_at TEXT,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        raw JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS job_skills (
        job_id TEXT NOT NULL,
        skill_raw TEXT NOT NULL,
        skill_canonical TEXT NOT NULL,
        confidence DOUBLE PRECISION DEFAULT 1.0,
        PRIMARY KEY (job_id, skill_raw)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skill_taxonomy (
        canonical TEXT PRIMARY KEY,
        aliases JSON,
        embedding JSON,
        updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resume_jobs (
        resume_id TEXT PRIMARY KEY,
        filename TEXT,
        extracted_skills JSON,
        experience_years DOUBLE PRECISION,
        education TEXT,
        report JSON,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingest_runs (
        run_id TEXT PRIMARY KEY,
        source TEXT,
        started_at TEXT,
        finished_at TEXT,
        fetched INTEGER DEFAULT 0,
        inserted INTEGER DEFAULT 0,
        updated INTEGER DEFAULT 0,
        status TEXT,
        error TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_job_postings_last_seen ON job_postings (last_seen)",
    "CREATE INDEX IF NOT EXISTS idx_job_skills_canonical ON job_skills (skill_canonical)",
]


def init_db() -> None:
    """Create every table and index if they do not exist yet."""
    with get_connection() as conn:
        cur = _cursor(conn)
        for statement in SCHEMA_STATEMENTS:
            cur.execute(statement)


# ---------------------------------------------------------------------------
# Postings
# ---------------------------------------------------------------------------

_POSTING_COLUMNS = [
    "job_id",
    "source",
    "title",
    "company",
    "location",
    "description",
    "url",
    "employment_type",
    "is_remote",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
    "salary_lpa",
    "experience_years",
    "posted_at",
    "first_seen",
    "last_seen",
    "is_active",
    "raw",
]


def _posting_row(record: dict, seen_at: str) -> list:
    raw = record.get("raw")
    if raw is not None and not isinstance(raw, str):
        raw = json.dumps(raw, default=str)
    return [
        record.get("job_id"),
        record.get("source") or "unknown",
        record.get("title"),
        record.get("company"),
        record.get("location"),
        record.get("description"),
        record.get("url"),
        record.get("employment_type"),
        bool(record.get("is_remote", False)),
        record.get("salary_min"),
        record.get("salary_max"),
        record.get("salary_currency"),
        record.get("salary_period"),
        record.get("salary_lpa"),
        record.get("experience_years"),
        record.get("posted_at"),
        record.get("first_seen") or seen_at,
        record.get("last_seen") or seen_at,
        True,
        raw,
    ]


_UPSERT_SQL = """
INSERT INTO job_postings ({cols})
VALUES ({placeholders})
ON CONFLICT (job_id) DO UPDATE SET
    last_seen = EXCLUDED.last_seen,
    is_active = TRUE,
    title = COALESCE(EXCLUDED.title, job_postings.title),
    company = COALESCE(EXCLUDED.company, job_postings.company),
    location = COALESCE(EXCLUDED.location, job_postings.location),
    description = COALESCE(EXCLUDED.description, job_postings.description),
    url = COALESCE(EXCLUDED.url, job_postings.url),
    employment_type = COALESCE(EXCLUDED.employment_type, job_postings.employment_type),
    salary_min = COALESCE(EXCLUDED.salary_min, job_postings.salary_min),
    salary_max = COALESCE(EXCLUDED.salary_max, job_postings.salary_max),
    salary_currency = COALESCE(EXCLUDED.salary_currency, job_postings.salary_currency),
    salary_period = COALESCE(EXCLUDED.salary_period, job_postings.salary_period),
    salary_lpa = COALESCE(EXCLUDED.salary_lpa, job_postings.salary_lpa),
    experience_years = COALESCE(EXCLUDED.experience_years, job_postings.experience_years),
    posted_at = COALESCE(EXCLUDED.posted_at, job_postings.posted_at),
    raw = COALESCE(EXCLUDED.raw, job_postings.raw)
""".format(
    cols=", ".join(_POSTING_COLUMNS),
    placeholders=", ".join(["?"] * len(_POSTING_COLUMNS)),
)


def upsert_postings(
    records: Iterable[dict],
    skills_by_job: dict[str, Iterable[dict]] | None = None,
) -> dict[str, int]:
    """Insert new postings and refresh ``last_seen`` on existing ones.

    ``skills_by_job`` maps ``job_id`` to a list of
    ``{"skill_raw", "skill_canonical", "confidence"}`` dicts.  Existing skill
    rows for a posting are replaced so re-normalisation stays consistent.

    Returns ``{"inserted", "updated", "skills"}`` counts.
    """
    seen_at = _now()
    inserted = updated = skill_rows = 0
    skills_by_job = skills_by_job or {}

    with get_connection() as conn:
        cur = _cursor(conn)
        # Postgres uses %s placeholders; normalise the shared SQL per backend.
        sql = _UPSERT_SQL.replace("?", _ph())

        for record in records:
            if not record.get("job_id"):
                continue
            cur.execute(
                f"SELECT 1 FROM job_postings WHERE job_id = {_ph()}",
                (record["job_id"],),
            )
            exists = cur.fetchone() is not None
            cur.execute(sql, _posting_row(record, seen_at))
            if exists:
                updated += 1
            else:
                inserted += 1

            for skill in skills_by_job.get(record["job_id"], []):
                raw = (skill.get("skill_raw") or "").strip()
                canonical = (skill.get("skill_canonical") or raw).strip()
                if not raw or not canonical:
                    continue
                cur.execute(
                    f"DELETE FROM job_skills WHERE job_id = {_ph()} AND skill_raw = {_ph()}",
                    (record["job_id"], raw),
                )
                cur.execute(
                    f"INSERT INTO job_skills (job_id, skill_raw, skill_canonical, confidence)"
                    f" VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()})",
                    (
                        record["job_id"],
                        raw,
                        canonical,
                        float(skill.get("confidence", 1.0)),
                    ),
                )
                skill_rows += 1

    return {"inserted": inserted, "updated": updated, "skills": skill_rows}


def fetch_postings(
    days: int | None = None,
    active_only: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Return postings as plain dicts, newest first."""
    where, params = _posting_where(days, active_only)
    sql = "SELECT * FROM job_postings" + where
    sql += " ORDER BY COALESCE(posted_at, last_seen) DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"

    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    return [dict(row) for row in rows]


def fetch_postings_with_skills(
    days: int | None = None,
    active_only: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Return postings with a ``skills`` list attached to each record.

    Used by semantic search and skill-ROI views, which need the description and
    canonical skills together but do not want the skill-expanded dataframe.
    """
    postings = fetch_postings(days=days, active_only=active_only, limit=limit)
    if not postings:
        return postings

    ids = [posting["job_id"] for posting in postings if posting.get("job_id")]
    if not ids:
        return postings

    placeholders = ", ".join([_ph()] * len(ids))
    sql = (
        "SELECT job_id, skill_canonical FROM job_skills"
        f" WHERE job_id IN ({placeholders})"
    )
    skills_by_job: dict[str, set[str]] = {}
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(sql, tuple(ids))
        for row in cur.fetchall():
            item = dict(row)
            canonical = item.get("skill_canonical")
            if canonical:
                skills_by_job.setdefault(item["job_id"], set()).add(canonical)

    for posting in postings:
        posting["skills"] = sorted(skills_by_job.get(posting.get("job_id"), set()))
    return postings


def _posting_where(days: int | None, active_only: bool, alias: str = "") -> tuple[str, list]:
    """Shared WHERE builder for posting queries (SQLite and Postgres)."""
    prefix = f"{alias}." if alias else ""
    clauses: list[str] = []
    params: list[Any] = []
    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0)
        clauses.append(f"{prefix}last_seen >= {_ph()}")
        params.append(cutoff.isoformat())
    if active_only:
        clauses.append(f"{prefix}is_active = TRUE")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def load_postings_dataframe(days: int = 365, active_only: bool = False):
    """Return postings + skills in the legacy CSV column shape.

    One row per (posting, skill) so existing charts keep working unchanged.
    ``Job ID`` is included so the UI can count postings rather than skill rows.
    """
    import pandas as pd

    where, params = _posting_where(days, active_only, alias="p")
    sql = f"""
        SELECT
            p.job_id AS "Job ID",
            p.title AS "Job Title",
            COALESCE(s.skill_canonical, s.skill_raw, 'General') AS "Tech Skill",
            p.company AS "Company",
            p.location AS "Location",
            p.experience_years AS "Experience Required (in years)",
            SUBSTR(COALESCE(p.posted_at, p.last_seen), 1, 10) AS "Date Posted",
            p.first_seen AS "first_seen",
            p.last_seen AS "last_seen",
            p.is_active AS "is_active"
        FROM job_postings p
        LEFT JOIN job_skills s ON s.job_id = p.job_id
        {where}
    """

    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn, params=tuple(params))

    if df.empty:
        return df

    df["Date Posted"] = pd.to_datetime(df["Date Posted"], format="mixed", errors="coerce")
    df = df.dropna(subset=["Date Posted"]).sort_values("Date Posted", ascending=False)
    return df.reset_index(drop=True)


def count_postings() -> int:
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT COUNT(*) AS n FROM job_postings")
        row = cur.fetchone()
    return int(row["n"] if isinstance(row, dict) else row[0])


def store_available() -> bool:
    """True when a DB is configured and already contains postings.

    Checks file existence first so a read-only page load never creates an
    empty SQLite file as a side effect.
    """
    try:
        if not use_postgres() and not os.path.exists(sqlite_path()):
            return False
        return count_postings() > 0
    except Exception:
        return False


def close_stale_postings(days: int = 14) -> int:
    """Mark postings unseen for ``days`` as inactive (proxy for 'closed').

    Safety valve: never close more than 50% of the active corpus in one run,
    so a narrow query can't wipe the history needed for survival analysis.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0)
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(
            f"SELECT COUNT(*) AS n FROM job_postings WHERE is_active = TRUE"
        )
        row = cur.fetchone()
        total_active = int(row["n"] if isinstance(row, dict) else row[0])
        cur.execute(
            f"SELECT COUNT(*) AS n FROM job_postings WHERE is_active = TRUE AND last_seen < {_ph()}",
            (cutoff.isoformat(),),
        )
        row = cur.fetchone()
        to_close = int(row["n"] if isinstance(row, dict) else row[0])

        if total_active >= 4 and to_close > total_active // 2:
            return 0

        cur.execute(
            f"UPDATE job_postings SET is_active = FALSE"
            f" WHERE is_active = TRUE AND last_seen < {_ph()}",
            (cutoff.isoformat(),),
        )
        changed = cur.rowcount or 0
    return int(changed)


# ---------------------------------------------------------------------------
# Skill taxonomy
# ---------------------------------------------------------------------------


def save_skill_taxonomy(entries: Iterable[dict]) -> int:
    """Upsert canonical skills with their aliases and optional embedding."""
    updated_at = _now()
    count = 0
    with get_connection() as conn:
        cur = _cursor(conn)
        for entry in entries:
            canonical = (entry.get("canonical") or "").strip()
            if not canonical:
                continue
            aliases = json.dumps(sorted(set(entry.get("aliases") or [])), default=str)
            embedding = entry.get("embedding")
            embedding_json = json.dumps(embedding) if embedding is not None else None
            cur.execute(
                f"""
                INSERT INTO skill_taxonomy (canonical, aliases, embedding, updated_at)
                VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()})
                ON CONFLICT (canonical) DO UPDATE SET
                    aliases = EXCLUDED.aliases,
                    embedding = COALESCE(EXCLUDED.embedding, skill_taxonomy.embedding),
                    updated_at = EXCLUDED.updated_at
                """,
                (canonical, aliases, embedding_json, updated_at),
            )
            count += 1
    return count


def fetch_skill_taxonomy() -> list[dict]:
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT canonical, aliases, embedding FROM skill_taxonomy ORDER BY canonical")
        rows = cur.fetchall()
    results = []
    for row in rows:
        item = dict(row)
        for key in ("aliases", "embedding"):
            if isinstance(item.get(key), str):
                try:
                    item[key] = json.loads(item[key])
                except json.JSONDecodeError:
                    item[key] = None
        results.append(item)
    return results


# ---------------------------------------------------------------------------
# Resume reports (used by ticket 13)
# ---------------------------------------------------------------------------


def save_resume_report(
    filename: str,
    extracted_skills: Iterable[str],
    experience_years: float | None,
    education: str | None,
    report: dict,
) -> str:
    resume_id = uuid.uuid4().hex
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(
            f"""
            INSERT INTO resume_jobs
                (resume_id, filename, extracted_skills, experience_years, education, report, created_at)
            VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()}, {_ph()})
            """,
            (
                resume_id,
                filename,
                json.dumps(sorted(set(extracted_skills))),
                experience_years,
                education,
                json.dumps(report, default=str),
                _now(),
            ),
        )
    return resume_id


# ---------------------------------------------------------------------------
# Ingest run bookkeeping
# ---------------------------------------------------------------------------


def start_ingest_run(source: str) -> str:
    run_id = uuid.uuid4().hex
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(
            f"""
            INSERT INTO ingest_runs (run_id, source, started_at, status)
            VALUES ({_ph()}, {_ph()}, {_ph()}, {_ph()})
            """,
            (run_id, source, _now(), "running"),
        )
    return run_id


def finish_ingest_run(
    run_id: str,
    fetched: int = 0,
    inserted: int = 0,
    updated: int = 0,
    status: str = "success",
    error: str | None = None,
) -> None:
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute(
            f"""
            UPDATE ingest_runs
            SET finished_at = {_ph()}, fetched = {_ph()}, inserted = {_ph()},
                updated = {_ph()}, status = {_ph()}, error = {_ph()}
            WHERE run_id = {_ph()}
            """,
            (_now(), fetched, inserted, updated, status, error, run_id),
        )


def latest_ingest_run() -> dict | None:
    """Most recent run, used by the UI's data-age badge."""
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT * FROM ingest_runs ORDER BY started_at DESC LIMIT 1")
        row = cur.fetchone()
    return dict(row) if row else None


def data_age_hours() -> float | None:
    """Hours since the newest posting was seen, or ``None`` if empty."""
    with get_connection() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT MAX(last_seen) AS newest FROM job_postings")
        row = cur.fetchone()
    newest = (row["newest"] if isinstance(row, dict) else row[0]) if row else None
    if not newest:
        return None
    try:
        seen = datetime.fromisoformat(str(newest).replace("Z", "+00:00"))
    except ValueError:
        return None
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - seen).total_seconds() / 3600, 2)
