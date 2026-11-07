import os

import pandas as pd


def load_job_data(data_directory="data", source="auto", days=365):
    """Load job listings from the live store.

    The static CSV pipeline has been retired; all data comes from the scheduled
    ingestion job. Returns an empty frame when the store is empty so the app can
    show a helpful message.
    """
    store_df = _load_from_store(days=days)
    if store_df is not None and not store_df.empty:
        return store_df, 1
    return pd.DataFrame(), 0


def _load_from_store(days=365):
    """Return a dataframe from the store, or None when it is unavailable."""
    try:
        from modules import store as job_store

        if not job_store.store_available():
            return None
        frame = job_store.load_postings_dataframe(days=days)
        if frame.empty:
            return None
        frame["Source File"] = "live store"
        return frame
    except Exception:
        return None


def available_sources():
    try:
        from modules import store as job_store

        live = job_store.store_available()
    except Exception:
        live = False
    return {"live": live, "csv": False}


def get_data_source_info():
    """Describe where the current data came from (for the freshness badge)."""
    try:
        from modules import store as job_store

        if not job_store.store_available():
            return {"source": "none", "rows": None, "age_hours": None, "last_run": None}
        return {
            "source": "postgres" if job_store.use_postgres() else "sqlite",
            "rows": job_store.count_postings(),
            "age_hours": job_store.data_age_hours(),
            "last_run": job_store.latest_ingest_run(),
        }
    except Exception:
        return {"source": "none", "rows": None, "age_hours": None, "last_run": None}


def get_required_columns():
    """Return list of required columns for job data"""
    return [
        "Job Title", "Tech Skill", "Company", "Location",
        "Experience Required (in years)", "Date Posted"
    ]
