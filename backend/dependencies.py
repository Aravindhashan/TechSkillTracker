"""Shared dependencies for the FastAPI backend.

These helpers are deliberately small and side-effect free: they return an
empty frame / empty list when the store is unavailable so endpoints can
degrade gracefully instead of 500-ing on an empty corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd


def _ensure_root_on_path() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_root_on_path()


def get_dataframe() -> pd.DataFrame:
    """Return a cleaned postings dataframe, or an empty frame."""
    try:
        from modules import data_loader, data_cleaner

        raw, _count = data_loader.load_job_data("data")
        if raw is None or getattr(raw, "empty", True):
            return pd.DataFrame()
        return data_cleaner.clean_job_data(raw)
    except Exception:
        return pd.DataFrame()


def get_search_records() -> list[dict[str, Any]]:
    """Return postings with skills attached (for semantic search)."""
    try:
        from modules import store as job_store

        if not job_store.store_available():
            return []
        return job_store.fetch_postings_with_skills(days=365, limit=500)
    except Exception:
        return []


def get_store_count() -> int:
    try:
        from modules import store as job_store

        return int(job_store.count_postings())
    except Exception:
        return 0


