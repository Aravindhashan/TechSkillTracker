import pandas as pd
import streamlit as st
import os
import glob


@st.cache_data
def load_job_data(data_directory="data"):
    """
    Load job listings from CSV files in the data directory
    Returns combined dataframe and number of files processed
    """
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
            df['Source File'] = filename
            all_data.append(df)
            files_processed += 1
        except Exception as e:
            st.error(f"Error loading file '{os.path.basename(file_path)}': {str(e)}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df, files_processed
    else:
        return pd.DataFrame(), 0


def get_required_columns():
    """Return list of required columns for job data"""
    return [
        "Job Title", "Tech Skill", "Company", "Location", 
        "Salary (in LPA)", "Experience Required (in years)", "Date Posted"
    ]
