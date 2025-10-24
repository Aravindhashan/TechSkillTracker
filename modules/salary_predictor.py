import pandas as pd
import numpy as np
import streamlit as st
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os


@st.cache_resource
def train_salary_model(df):
    """
    Train Random Forest model for salary prediction
    Features: Tech Skill, Location, Experience
    """
    # Prepare data
    model_df = df[['Tech Skill', 'Location', 'Experience Required (in years)', 'Salary (in LPA)']].copy()
    model_df = model_df.dropna()
    
    if len(model_df) < 10:
        return None, None, None, "Insufficient data for training (need at least 10 records)"
    
    # Encode categorical variables
    le_skill = LabelEncoder()
    le_location = LabelEncoder()
    
    model_df['Skill_Encoded'] = le_skill.fit_transform(model_df['Tech Skill'].astype(str))
    model_df['Location_Encoded'] = le_location.fit_transform(model_df['Location'].astype(str))
    
    # Prepare features and target
    X = model_df[['Skill_Encoded', 'Location_Encoded', 'Experience Required (in years)']]
    y = model_df['Salary (in LPA)']
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    # Split and train
    if len(X) > 20:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model.fit(X_train, y_train)
        score = model.score(X_test, y_test)
    else:
        model.fit(X, y)
        score = model.score(X, y)
    
    return model, le_skill, le_location, f"Model trained successfully (R² score: {score:.2f})"


@st.cache_data
def predict_salary(_model, _le_skill, _le_location, skill, location, experience):
    """
    Predict salary based on input parameters
    """
    if _model is None:
        return None, "Model not trained"
    
    try:
        # Encode inputs
        skill_encoded = _le_skill.transform([skill])[0]
        location_encoded = _le_location.transform([location])[0]
        
        # Predict
        prediction = _model.predict([[skill_encoded, location_encoded, experience]])[0]
        
        return prediction, "success"
        
    except ValueError as e:
        # Handle unseen categories
        return None, f"Unseen category in input: {str(e)}"


def get_salary_distribution(df, skill=None, location=None):
    """
    Get salary distribution for given filters
    """
    filtered_df = df.copy()
    
    if skill:
        filtered_df = filtered_df[filtered_df['Tech Skill'] == skill]
    
    if location:
        filtered_df = filtered_df[filtered_df['Location'] == location]
    
    if len(filtered_df) == 0:
        return None
    
    stats = {
        'min': filtered_df['Salary (in LPA)'].min(),
        'max': filtered_df['Salary (in LPA)'].max(),
        'mean': filtered_df['Salary (in LPA)'].mean(),
        'median': filtered_df['Salary (in LPA)'].median(),
        'percentile_25': filtered_df['Salary (in LPA)'].quantile(0.25),
        'percentile_75': filtered_df['Salary (in LPA)'].quantile(0.75)
    }
    
    return stats


def get_salary_insights(df, skill, location=None):
    """
    Generate salary insights for a skill
    """
    insights = []
    
    skill_data = df[df['Tech Skill'] == skill]
    
    if len(skill_data) == 0:
        return ["No data available for this skill"]
    
    avg_salary = skill_data['Salary (in LPA)'].mean()
    market_avg = df['Salary (in LPA)'].mean()
    
    diff_pct = ((avg_salary - market_avg) / market_avg) * 100
    
    if diff_pct > 20:
        insights.append(f"💰 **High-Paying Skill**: {skill} offers {diff_pct:.1f}% higher salary than market average")
    elif diff_pct < -20:
        insights.append(f"📊 **Below Average**: {skill} offers {abs(diff_pct):.1f}% lower salary than market average")
    else:
        insights.append(f"💼 **Market Average**: {skill} offers salaries close to market average ({diff_pct:+.1f}%)")
    
    # Experience-based insight
    exp_corr = skill_data[['Experience Required (in years)', 'Salary (in LPA)']].corr().iloc[0, 1]
    if exp_corr > 0.7:
        insights.append(f"📈 **Experience Matters**: Strong correlation between experience and salary for {skill}")
    
    # Location insight
    if location:
        location_data = skill_data[skill_data['Location'] == location]
        if len(location_data) > 0:
            loc_avg = location_data['Salary (in LPA)'].mean()
            insights.append(f"📍 **{location}**: Average salary ₹{loc_avg:.1f}L for {skill}")
    
    return insights
