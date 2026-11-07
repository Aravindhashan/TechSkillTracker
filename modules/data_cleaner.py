import re

import pandas as pd


# Maps any city alias found inside a location string to one canonical name.
# The entries whose key equals the value (e.g. "mumbai": "Mumbai") are needed
# because matching is substring-based: "Mumbai, Maharashtra, India" must still
# collapse to "Mumbai".
LOCATION_MAPPING = {
    "bangalore": "Bengaluru",
    "bengalore": "Bengaluru",
    "bombay": "Mumbai",
    "delhi": "New Delhi",
    "ncr": "New Delhi",
    "hyd": "Hyderabad",
    "calcutta": "Kolkata",
    "gurugram": "Gurgaon",
    "gurgaon": "Gurgaon",
    "noida": "Noida",
    "mumbai": "Mumbai",
    "hyderabad": "Hyderabad",
    "chennai": "Chennai",
    "pune": "Pune",
    "kolkata": "Kolkata",
    "bengaluru": "Bengaluru",
    "new delhi": "New Delhi",
}


def _normalize_location(value) -> str:
    """Map 'Bangalore, Karnataka, India' and 'bangalore' to 'Bengaluru'."""
    if not isinstance(value, str) or not value.strip():
        return "Unknown"
    lowered = value.lower()
    for alias, canonical in LOCATION_MAPPING.items():
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", lowered):
            return canonical
    return value.strip().title()


@st.cache_data
@st.cache_data
def clean_job_data(df):
    """
    Clean and standardize job data.

    Live postings often have no salary or no stated experience, so those
    fields are kept as NaN instead of dropping the whole posting. Charts that
    need them filter them out locally; skill-demand views keep every row.
    """
    if df.empty:
        return df

    df = df.copy()
    original_count = len(df)

    # Remove exact duplicates
    df = df.drop_duplicates()

    # Convert Date Posted to datetime
    df["Date Posted"] = pd.to_datetime(df["Date Posted"], errors="coerce")

    # Convert numerics (invalid values become NaN, not crashes)
    df["Experience Required (in years)"] = pd.to_numeric(
        df["Experience Required (in years)"], errors="coerce"
    )

    # Only the posting date is critical - everything else can be missing
    df = df.dropna(subset=["Date Posted"])

    # Drop impossible experience values but keep missing ones
    df = df[
        df["Experience Required (in years)"].isna()
        | ((df["Experience Required (in years)"] >= 0) & (df["Experience Required (in years)"] <= 50))
    ]

    # Standardize text fields
    for column in ("Tech Skill", "Location", "Company", "Job Title"):
        if column in df.columns:
            df[column] = df[column].fillna("Unknown").astype(str).str.strip()

    df["Location"] = df["Location"].map(_normalize_location)

    cleaned_count = len(df)
    removed_count = original_count - cleaned_count

    if removed_count > 0:
        import logging

        logging.getLogger(__name__).info(
            "Cleaned data: Removed %d invalid/duplicate records (%.1f%%)",
            removed_count,
            removed_count / original_count * 100,
        )

    return df


def validate_data(df):
    """
    Validate that dataframe has required columns and data
    """
    required_columns = [
        "Job Title", "Tech Skill", "Company", "Location", 
        "Experience Required (in years)", "Date Posted"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    if len(df) == 0:
        return False, "No data available after cleaning"
    
    return True, "Data validated successfully"


def get_data_summary(df):
    """
    Get summary statistics of the dataset
    """
    experience = df["Experience Required (in years)"].dropna()

    if experience.empty:
        experience_range = "No experience data"
    else:
        experience_range = f"{experience.min():.0f} - {experience.max():.0f} years"

    summary = {
        'Total Records': len(df),
        'Unique Skills': df['Tech Skill'].nunique(),
        'Unique Companies': df['Company'].nunique(),
        'Unique Locations': df['Location'].nunique(),
        'Date Range': f"{df['Date Posted'].min().date()} to {df['Date Posted'].max().date()}",
        'Experience Range': experience_range
    }
    return summary
