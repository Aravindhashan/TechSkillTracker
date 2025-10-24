import pandas as pd
import numpy as np
import streamlit as st


@st.cache_data
def clean_job_data(df):
    """
    Clean and standardize job data
    - Removes duplicates
    - Handles missing values
    - Standardizes formats
    - Validates data types
    """
    if df.empty:
        return df
    
    df = df.copy()
    original_count = len(df)
    
    # Remove exact duplicates
    df = df.drop_duplicates()
    
    # Convert Date Posted to datetime
    df['Date Posted'] = pd.to_datetime(df['Date Posted'], errors='coerce')
    
    # Convert Salary to numeric
    df['Salary (in LPA)'] = pd.to_numeric(df['Salary (in LPA)'], errors='coerce')
    
    # Convert Experience to numeric
    df['Experience Required (in years)'] = pd.to_numeric(
        df['Experience Required (in years)'], errors='coerce'
    )
    
    # Remove rows with invalid critical fields
    df = df.dropna(subset=['Date Posted', 'Salary (in LPA)', 'Experience Required (in years)'])
    
    # Remove invalid salaries (negative or extremely high)
    df = df[(df['Salary (in LPA)'] > 0) & (df['Salary (in LPA)'] < 200)]
    
    # Remove invalid experience (negative or extremely high)
    df = df[(df['Experience Required (in years)'] >= 0) & (df['Experience Required (in years)'] <= 50)]
    
    # Standardize text fields
    df['Tech Skill'] = df['Tech Skill'].str.strip()
    df['Location'] = df['Location'].str.strip()
    df['Company'] = df['Company'].str.strip()
    df['Job Title'] = df['Job Title'].str.strip()
    
    # Standardize location names
    location_mapping = {
        'bangalore': 'Bengaluru',
        'bengalore': 'Bengaluru', 
        'mumbai': 'Mumbai',
        'bombay': 'Mumbai',
        'delhi': 'New Delhi',
        'ncr': 'New Delhi',
        'hyderabad': 'Hyderabad',
        'hyd': 'Hyderabad',
        'chennai': 'Chennai',
        'pune': 'Pune',
        'kolkata': 'Kolkata',
        'calcutta': 'Kolkata'
    }
    
    df['Location'] = df['Location'].str.lower().replace(location_mapping)
    df['Location'] = df['Location'].str.title()
    
    cleaned_count = len(df)
    removed_count = original_count - cleaned_count
    
    if removed_count > 0:
        st.info(f"Cleaned data: Removed {removed_count} invalid/duplicate records ({removed_count/original_count*100:.1f}%)")
    
    return df


def validate_data(df):
    """
    Validate that dataframe has required columns and data
    """
    required_columns = [
        "Job Title", "Tech Skill", "Company", "Location", 
        "Salary (in LPA)", "Experience Required (in years)", "Date Posted"
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
    summary = {
        'Total Records': len(df),
        'Unique Skills': df['Tech Skill'].nunique(),
        'Unique Companies': df['Company'].nunique(),
        'Unique Locations': df['Location'].nunique(),
        'Date Range': f"{df['Date Posted'].min().date()} to {df['Date Posted'].max().date()}",
        'Salary Range': f"₹{df['Salary (in LPA)'].min():.1f}L - ₹{df['Salary (in LPA)'].max():.1f}L",
        'Experience Range': f"{df['Experience Required (in years)'].min():.0f} - {df['Experience Required (in years)'].max():.0f} years"
    }
    return summary
