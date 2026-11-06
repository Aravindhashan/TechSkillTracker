import glob
import os

import pandas as pd
import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def load_job_data(data_directory="data", source="auto"):
    """
    Load job listings from the live store or the bundled CSV files.

    ``source``:
      * ``"auto"``  - live store when it has rows, otherwise CSV (default)
      * ``"live"``  - only the store
      * ``"csv"``   - only the CSV files

    Returns combined dataframe and number of sources processed.
    """
    if source in ("auto", "live"):
        store_df = _load_from_store()
        if store_df is not None and not store_df.empty:
            return store_df, 1
        if source == "live":
            return pd.DataFrame(), 0

    return _load_from_csv(data_directory)


def _load_from_store():
    """Return a dataframe from the store, or None when it is unavailable."""
    try:
        from modules import store as job_store

        if not job_store.store_available():
            return None
        frame = job_store.load_postings_dataframe(days=365)
        if frame.empty:
            return None
        frame["Source File"] = "live store"
        return frame
    except Exception:
        # A broken/unreachable DB must never take the dashboard down.
        return None


def _load_from_csv(data_directory="data"):
    """Original CSV loader, unchanged behaviour."""
    all_data = []
    files_processed = 0

    if not os.path.exists(data_directory):
        st.warning(f"Data directory '{data_directory}' not found.")
        return pd.DataFrame(), 0

    csv_files = glob.glob(os.path.join(data_directory, "*.csv"))

    if not csv_files:
        st.warning(f"No CSV files found in '{data_directory}' directory.")
        return pd.DataFrame(), 0

    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            filename = os.path.basename(file_path)
            df["Source File"] = filename
            all_data.append(df)
            files_processed += 1
        except Exception as e:
            st.error(f"Error loading file '{os.path.basename(file_path)}': {str(e)}")

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df, files_processed
    else:
        return pd.DataFrame(), 0


def available_sources():
    """Which data sources the app can offer right now."""
    try:
        from modules import store as job_store

        live = job_store.store_available()
    except Exception:
        live = False
    return {
        "live": live,
        "csv": bool(glob.glob(os.path.join("data", "*.csv"))),
    }


def get_data_source_info():
    """Describe where the current data came from (for the freshness badge)."""
    try:
        from modules import store as job_store

        if not job_store.store_available():
            return {"source": "csv", "rows": None, "age_hours": None, "last_run": None}
        return {
            "source": "postgres" if job_store.use_postgres() else "sqlite",
            "rows": job_store.count_postings(),
            "age_hours": job_store.data_age_hours(),
            "last_run": job_store.latest_ingest_run(),
        }
    except Exception:
        return {"source": "csv", "rows": None, "age_hours": None, "last_run": None}


def get_required_columns():
    """Return list of required columns for job data"""
    return [
        "Job Title", "Tech Skill", "Company", "Location", 
        "Salary (in LPA)", "Experience Required (in years)", "Date Posted"
    ]
