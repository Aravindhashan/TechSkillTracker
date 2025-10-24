import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import random
from datetime import datetime, timedelta
import io
import os
import glob
import csv
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import base64
from nlp_model import load_job_classifier, predict_job_role
from salary_model import load_salary_predictor, predict_salary

# Set page configuration
st.set_page_config(
    page_title="Tech Skills BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def validate_csv_structure(df):
    """
    Validate that the CSV has the required columns
    """
    required_columns = [
        "Job Title", "Tech Skill", "Company", "Location", 
        "Salary (in LPA)", "Experience Required (in years)", "Date Posted"
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, missing_columns
    
    return True, []

@st.cache_data
def load_local_csv_files(data_directory="data"):
    """
    Load all CSV files from a local directory and combine them into a single DataFrame
    """
    all_data = []
    files_processed = 0
    
    # Check if data directory exists
    if not os.path.exists(data_directory):
        st.warning(f"Data directory '{data_directory}' not found. Creating directory...")
        os.makedirs(data_directory)
        st.info(f"Please place your CSV files in the '{data_directory}' directory and refresh the page.")
        return pd.DataFrame(), 0
    
    # Find all CSV files in the directory
    csv_files = glob.glob(os.path.join(data_directory, "*.csv"))
    
    if not csv_files:
        st.warning(f"No CSV files found in the '{data_directory}' directory.")
        return pd.DataFrame(), 0
    
    for file_path in csv_files:
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            filename = os.path.basename(file_path)
            
            # Validate structure
            is_valid, missing_cols = validate_csv_structure(df)
            
            if not is_valid:
                st.error(f"File '{filename}' is missing required columns: {', '.join(missing_cols)}")
                continue
            
            # Clean and standardize the data
            df['Date Posted'] = pd.to_datetime(df['Date Posted'], errors='coerce')
            df['Salary (in LPA)'] = pd.to_numeric(df['Salary (in LPA)'], errors='coerce')
            df['Experience Required (in years)'] = pd.to_numeric(df['Experience Required (in years)'], errors='coerce')
            
            # Remove rows with invalid data
            original_count = len(df)
            df = df.dropna(subset=['Date Posted', 'Salary (in LPA)', 'Experience Required (in years)'])
            cleaned_count = len(df)
            
            # Add source file information
            df['Source File'] = filename
            
            all_data.append(df)
            files_processed += 1
            
        except Exception as e:
            st.error(f"Error processing file '{os.path.basename(file_path)}': {str(e)}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df, files_processed
    else:
        return pd.DataFrame(), 0

def display_data_setup_instructions():
    """Display instructions for setting up data directory"""
    st.markdown("""
    ### 📂 Data Setup Instructions
    
    **Step 1:** Create a `data` directory in your project folder
    
    **Step 2:** Place your CSV files in the `data` directory
    
    **Step 3:** Ensure each CSV file contains these required columns:
    
    - **Job Title**: The job position (e.g., "Data Scientist", "Backend Developer")
    - **Tech Skill**: The required technology skill (e.g., "Python", "JavaScript", "React")
    - **Company**: The company name (e.g., "Google", "Microsoft")
    - **Location**: The job location (e.g., "Bengaluru", "Mumbai")
    - **Salary (in LPA)**: The salary in Lakhs Per Annum (numeric value)
    - **Experience Required (in years)**: Required experience in years (numeric value)
    - **Date Posted**: The job posting date (YYYY-MM-DD format or any standard date format)
    
    **Step 4:** Refresh the page to load your data
    """)
    
    # Show sample data format
    sample_data = pd.DataFrame({
        'Job Title': ['Data Scientist', 'Backend Developer', 'Frontend Developer'],
        'Tech Skill': ['Python', 'Java', 'React'],
        'Company': ['Google', 'Amazon', 'Microsoft'],
        'Location': ['Bengaluru', 'Hyderabad', 'Pune'],
        'Salary (in LPA)': [15.5, 12.0, 10.5],
        'Experience Required (in years)': [3, 2, 1],
        'Date Posted': ['2024-01-15', '2024-01-10', '2024-01-08']
    })
    
    st.write("**Sample CSV Format:**")
    st.dataframe(sample_data, use_container_width=True, hide_index=True)

def create_top_skills_chart(df):
    """Create bar chart for top 10 most in-demand tech skills"""
    skill_counts = df['Tech Skill'].value_counts().head(10)
    
    fig = px.bar(
        x=skill_counts.values,
        y=skill_counts.index,
        orientation='h',
        title="Top 10 Most In-Demand Tech Skills",
        labels={'x': 'Number of Job Openings', 'y': 'Tech Skills'},
        color=skill_counts.values,
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )
    
    return fig

def create_location_pie_chart(df):
    """Create pie chart for job openings by location"""
    location_counts = df['Location'].value_counts()
    
    fig = px.pie(
        values=location_counts.values,
        names=location_counts.index,
        title="Job Openings Distribution by Location"
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=500)
    
    return fig

def create_skill_trends_chart(df):
    """Create line graph showing skill demand trends over time"""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=500, title="Skill Demand Trends Over Time")
        return fig
    
    # Convert Date Posted to datetime
    df = df.copy()
    df['Date Posted'] = pd.to_datetime(df['Date Posted'])
    
    # Get top 5 skills from the filtered data
    top_skills = df['Tech Skill'].value_counts().head(5).index
    
    # Create monthly aggregation with proper sorting
    df['Year-Month'] = df['Date Posted'].dt.to_period('M')
    
    # Get full range of months in the data
    all_months = sorted(df['Year-Month'].unique())
    
    trend_data = []
    for skill in top_skills:
        skill_df = df[df['Tech Skill'] == skill]
        monthly_counts = skill_df.groupby('Year-Month').size().reindex(all_months, fill_value=0)
        
        for period, count in monthly_counts.items():
            trend_data.append({
                'Month': period.start_time,  # Convert to timestamp for proper sorting
                'Tech Skill': skill,
                'Job Openings': count
            })
    
    if trend_data:
        trends_df = pd.DataFrame(trend_data)
        trends_df = trends_df.sort_values('Month')  # Ensure proper chronological order
        
        fig = px.line(
            trends_df,
            x='Month',
            y='Job Openings',
            color='Tech Skill',
            title="Skill Demand Trends Over Time (Top 5 Skills)",
            markers=True
        )
        
        # Format x-axis to show months clearly
        fig.update_xaxes(
            title="Time Period",
            tickformat="%Y-%m",
            dtick="M1"
        )
        
        fig.update_layout(
            height=500,
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        
        return fig
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=500, title="Skill Demand Trends Over Time")
        return fig

def create_skill_comparison_chart(df, skill_a, skill_b, location=None):
    """Create comparison chart between two skills"""
    df = df.copy()
    df['Date Posted'] = pd.to_datetime(df['Date Posted'])
    
    # Filter by location if specified
    if location and location != "All Locations":
        df = df[df['Location'] == location]
    
    # Filter data for both skills
    skill_a_data = df[df['Tech Skill'] == skill_a]
    skill_b_data = df[df['Tech Skill'] == skill_b]
    
    # Create yearly aggregation
    df['Year'] = df['Date Posted'].dt.year
    skill_a_yearly = skill_a_data.groupby(skill_a_data['Date Posted'].dt.year).size().reset_index()
    skill_b_yearly = skill_b_data.groupby(skill_b_data['Date Posted'].dt.year).size().reset_index()
    
    skill_a_yearly.columns = ['Year', 'Job Openings']
    skill_b_yearly.columns = ['Year', 'Job Openings']
    
    skill_a_yearly['Skill'] = skill_a
    skill_b_yearly['Skill'] = skill_b
    
    # Combine data
    comparison_data = pd.concat([skill_a_yearly, skill_b_yearly], ignore_index=True)
    
    if not comparison_data.empty:
        location_text = f" in {location}" if location and location != "All Locations" else ""
        title = f"Skill Demand Comparison: {skill_a} vs {skill_b}{location_text}"
        
        fig = px.line(
            comparison_data,
            x='Year',
            y='Job Openings',
            color='Skill',
            title=title,
            markers=True,
            line_shape='linear'
        )
        
        fig.update_layout(
            height=500,
            xaxis_title="Year",
            yaxis_title="Number of Job Openings"
        )
        
        return fig
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for selected skills/location",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=500, title="Skill Comparison")
        return fig

def create_salary_comparison_chart(df, skill_a, skill_b, location=None):
    """Create salary comparison chart between two skills"""
    df = df.copy()
    
    # Filter by location if specified
    if location and location != "All Locations":
        df = df[df['Location'] == location]
    
    # Filter data for both skills
    skill_a_data = df[df['Tech Skill'] == skill_a]
    skill_b_data = df[df['Tech Skill'] == skill_b]
    
    if not skill_a_data.empty and not skill_b_data.empty:
        # Create salary comparison data
        comparison_data = pd.concat([
            skill_a_data[['Salary (in LPA)', 'Tech Skill']],
            skill_b_data[['Salary (in LPA)', 'Tech Skill']]
        ])
        
        location_text = f" in {location}" if location and location != "All Locations" else ""
        title = f"Salary Distribution: {skill_a} vs {skill_b}{location_text}"
        
        fig = px.box(
            comparison_data,
            x='Tech Skill',
            y='Salary (in LPA)',
            title=title,
            color='Tech Skill'
        )
        
        fig.update_layout(height=400)
        return fig
    else:
        fig = go.Figure()
        fig.add_annotation(
            text="Insufficient data for salary comparison",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=400, title="Salary Comparison")
        return fig

def create_skill_cooccurrence_heatmap(df):
    """Create skill co-occurrence heatmap"""
    # Get companies that require multiple skills
    company_skills = df.groupby('Company')['Tech Skill'].apply(list).reset_index()
    
    # Create co-occurrence matrix
    from itertools import combinations
    import pandas as pd
    
    cooccurrence_data = []
    all_skills = df['Tech Skill'].unique()
    
    for skills_list in company_skills['Tech Skill']:
        if len(skills_list) > 1:
            for skill1, skill2 in combinations(set(skills_list), 2):
                cooccurrence_data.append({'Skill1': skill1, 'Skill2': skill2})
    
    if not cooccurrence_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No skill co-occurrence data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(height=500, title="Skill Co-occurrence Analysis")
        return fig
    
    cooccurrence_df = pd.DataFrame(cooccurrence_data)
    cooccurrence_counts = cooccurrence_df.groupby(['Skill1', 'Skill2']).size().reset_index(name='Count')
    
    # Get top skill pairs
    top_pairs = cooccurrence_counts.nlargest(20, 'Count')
    
    fig = px.bar(
        top_pairs,
        x='Count',
        y=[f"{row['Skill1']} + {row['Skill2']}" for _, row in top_pairs.iterrows()],
        orientation='h',
        title="Top 20 Skill Co-occurrences in Job Postings",
        labels={'x': 'Number of Co-occurrences', 'y': 'Skill Combinations'}
    )
    
    fig.update_layout(
        height=600,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return fig

def create_demand_saturation_index(df):
    """Calculate and visualize demand saturation index"""
    # Calculate jobs per skill per unique company
    saturation_data = df.groupby('Tech Skill').agg({
        'Job Title': 'count',
        'Company': 'nunique'
    }).reset_index()
    
    saturation_data['Saturation_Index'] = saturation_data['Job Title'] / saturation_data['Company']
    saturation_data = saturation_data.sort_values('Saturation_Index', ascending=False).head(15)
    
    fig = px.scatter(
        saturation_data,
        x='Company',
        y='Job Title',
        size='Saturation_Index',
        color='Saturation_Index',
        hover_name='Tech Skill',
        title="Demand Saturation Index (Jobs per Skill / Unique Companies)",
        labels={
            'Company': 'Number of Unique Companies',
            'Job Title': 'Total Job Openings',
            'Saturation_Index': 'Saturation Index'
        }
    )
    
    fig.update_layout(height=500)
    return fig

def create_trend_forecast(df, skill_name):
    """Create trend forecast for a specific skill"""
    try:
        # Simple linear trend forecast (fallback if Prophet not available)
        skill_data = df[df['Tech Skill'] == skill_name].copy()
        skill_data['Date Posted'] = pd.to_datetime(skill_data['Date Posted'])
        
        # Group by month
        monthly_data = skill_data.groupby(skill_data['Date Posted'].dt.to_period('M')).size().reset_index()
        monthly_data['Date Posted'] = monthly_data['Date Posted'].dt.to_timestamp()
        monthly_data.columns = ['Date', 'Count']
        
        if len(monthly_data) < 3:
            return None
        
        # Simple linear regression for trend
        from datetime import timedelta
        import numpy as np
        
        x = np.arange(len(monthly_data))
        y = monthly_data['Count'].values
        
        # Calculate trend
        slope, intercept = np.polyfit(x, y, 1)
        
        # Forecast next 3 months
        future_months = 3
        future_x = np.arange(len(monthly_data), len(monthly_data) + future_months)
        future_y = slope * future_x + intercept
        
        # Create forecast dataframe
        last_date = monthly_data['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=30*i) for i in range(1, future_months + 1)]
        
        forecast_df = pd.DataFrame({
            'Date': future_dates,
            'Forecast': future_y,
            'Type': 'Forecast'
        })
        
        # Combine historical and forecast
        historical_df = monthly_data.copy()
        historical_df['Type'] = 'Historical'
        historical_df['Forecast'] = historical_df['Count']
        
        combined_df = pd.concat([
            historical_df[['Date', 'Forecast', 'Type']],
            forecast_df
        ], ignore_index=True)
        
        fig = px.line(
            combined_df,
            x='Date',
            y='Forecast',
            color='Type',
            title=f"Demand Forecast for {skill_name}",
            markers=True
        )
        
        # Calculate growth percentage
        if len(monthly_data) >= 2:
            current_avg = monthly_data['Count'].tail(3).mean()
            forecast_avg = future_y.mean()
            growth_pct = ((forecast_avg - current_avg) / current_avg) * 100
            
            fig.add_annotation(
                text=f"Predicted growth: {growth_pct:.1f}% over next quarter",
                xref="paper", yref="paper",
                x=0.02, y=0.98, showarrow=False,
                bgcolor="lightblue", bordercolor="blue"
            )
        
        fig.update_layout(height=400)
        return fig
        
    except Exception as e:
        return None

def create_comprehensive_pdf_report(df, user_email=None, dream_job=None, target_location=None, filtered_df=None):
    """Create a comprehensive PDF report with personalized analytics based on user selections"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Title page
    story.append(Paragraph("Tech Skills Business Intelligence Report", title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    if user_email:
        story.append(Paragraph(f"Prepared for: {user_email}", styles['Normal']))
    if dream_job:
        story.append(Paragraph(f"Dream Job Focus: {dream_job}", styles['Normal']))
    if target_location and target_location != "Any Location":
        story.append(Paragraph(f"Target Location: {target_location}", styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    # Calculate key metrics
    total_jobs = len(df)
    unique_skills = df['Tech Skill'].nunique()
    unique_companies = df['Company'].nunique()
    unique_locations = df['Location'].nunique()
    avg_salary = df['Salary (in LPA)'].mean()
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Job Openings', f"{total_jobs:,}"],
        ['Unique Tech Skills', f"{unique_skills:,}"],
        ['Unique Companies', f"{unique_companies:,}"],
        ['Unique Locations', f"{unique_locations:,}"],
        ['Average Salary', f"₹{avg_salary:.1f}L"]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Key Insights
    story.append(Paragraph("Key Market Insights", heading_style))
    
    most_frequent_skill = df['Tech Skill'].value_counts().index[0]
    skill_counts = df['Tech Skill'].value_counts()
    location_counts = df['Location'].value_counts()
    high_paying_skills = df.groupby('Tech Skill')['Salary (in LPA)'].mean().nlargest(3)
    
    insights = [
        f"• {most_frequent_skill} is the most demanded skill with {skill_counts.iloc[0]} job listings ({(skill_counts.iloc[0]/len(df)*100):.1f}% of all opportunities)",
        f"• {location_counts.index[0]} leads in job opportunities with {location_counts.iloc[0]} openings",
        f"• {high_paying_skills.index[0]} offers the highest average salary at ₹{high_paying_skills.iloc[0]:.1f}L",
        f"• The market spans across {unique_locations} major locations with {unique_companies} active companies"
    ]
    
    for insight in insights:
        story.append(Paragraph(insight, styles['Normal']))
        story.append(Spacer(1, 8))
    
    story.append(Spacer(1, 20))
    
    # Dream Job Roadmap Section (if provided)
    if dream_job:
        story.append(Paragraph(f"Career Roadmap for {dream_job}", heading_style))
        
        # Career roadmaps database
        roadmaps = {
            "data scientist": {
                "core_skills": ["Python", "Machine Learning", "Statistics", "SQL"],
                "salary_range": "₹8-60L based on experience",
                "career_path": "Data Analyst → Data Scientist → Senior Data Scientist → Lead Data Scientist"
            },
            "full stack developer": {
                "core_skills": ["JavaScript", "React", "Node.js", "HTML", "CSS"],
                "salary_range": "₹6-50L based on experience", 
                "career_path": "Junior Developer → Full Stack Developer → Senior Developer → Tech Lead"
            },
            "ml engineer": {
                "core_skills": ["Python", "Machine Learning", "TensorFlow", "Docker"],
                "salary_range": "₹10-70L based on experience",
                "career_path": "ML Intern → ML Engineer → Senior ML Engineer → ML Architect"
            },
            "devops engineer": {
                "core_skills": ["Docker", "Kubernetes", "AWS", "Jenkins"],
                "salary_range": "₹8-55L based on experience",
                "career_path": "System Admin → DevOps Engineer → Senior DevOps → DevOps Architect"
            }
        }
        
        # Find matching roadmap
        dream_job_lower = dream_job.lower().strip()
        matching_roadmap = None
        
        for key, roadmap in roadmaps.items():
            if key in dream_job_lower or any(word in dream_job_lower for word in key.split()):
                matching_roadmap = roadmap
                break
        
        if matching_roadmap:
            story.append(Paragraph(f"Core Skills Required: {', '.join(matching_roadmap['core_skills'])}", styles['Normal']))
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Expected Salary Range: {matching_roadmap['salary_range']}", styles['Normal']))
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Career Progression: {matching_roadmap['career_path']}", styles['Normal']))
            story.append(Spacer(1, 8))
            
            # Find relevant opportunities in target location
            if target_location and target_location != "Any Location":
                location_data = df[df['Location'] == target_location]
                relevant_skills = matching_roadmap["core_skills"]
                relevant_jobs = location_data[location_data['Tech Skill'].isin(relevant_skills)]
                
                if not relevant_jobs.empty:
                    avg_salary_location = relevant_jobs['Salary (in LPA)'].mean()
                    story.append(Paragraph(f"Market Opportunity in {target_location}: {len(relevant_jobs)} relevant positions with average salary ₹{avg_salary_location:.1f}L", styles['Normal']))
                    story.append(Spacer(1, 8))
        else:
            # Generic advice for unlisted roles
            story.append(Paragraph(f"Market Analysis: Based on current data, focus on building skills in high-demand technologies and consider locations with active job markets.", styles['Normal']))
            story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 20))

    # Skill Trend Forecast
    story.append(Paragraph("Skill Trend Forecast", heading_style))
    story.append(Paragraph("This section provides a 12-month forecast for the top 3 most in-demand skills.", styles["Normal"]))
    story.append(Spacer(1, 8))

    top_3_skills = df["Tech Skill"].value_counts().head(3).index.tolist()
    for skill in top_3_skills:
        forecast_fig = create_trend_forecast(df, skill)
        if forecast_fig:
            img_buffer = io.BytesIO()
            forecast_fig.write_image(img_buffer, format="png")
            img_buffer.seek(0)
            story.append(Image(img_buffer, width=400, height=300))
            story.append(Paragraph(f"Forecast for {skill}", styles["Normal"]))
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph(f"No sufficient data to forecast for {skill}.", styles["Normal"]))
        story.append(Spacer(1, 20))

    # Top Skills Analysis
    story.append(Paragraph("Top 10 In-Demand Skills", heading_style))
    
    top_skills = df['Tech Skill'].value_counts().head(10)
    skills_data = [['Rank', 'Skill', 'Job Openings', 'Market Share']]
    
    for i, (skill, count) in enumerate(top_skills.items(), 1):
        percentage = (count / len(df)) * 100
        skills_data.append([str(i), skill, str(count), f"{percentage:.1f}%"])
    
    skills_table = Table(skills_data)
    skills_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10)
    ]))
    
    story.append(skills_table)
    story.append(Spacer(1, 20))

    # Skill Recommendation
    story.append(Paragraph("Skill Recommendations", heading_style))
    story.append(Paragraph("Based on your profile, here are some recommended skills to learn:", styles["Normal"]))
    story.append(Spacer(1, 8))

    recommendations = get_skill_recommendations(df, top_3_skills, top_n=5)
    if not recommendations.empty:
        for index, row in recommendations.iterrows():
            story.append(Paragraph(f"- **{row['Recommended Skill']}**: Pairs well with {row['Base Skill']}", styles["Normal"]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No specific recommendations at this time. Broaden your skill set with emerging technologies.", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Job Role Classification
    story.append(Paragraph("Job Role Classification", heading_style))
    story.append(Paragraph("This section classifies job titles into broader roles using an NLP model.", styles["Normal"]))
    story.append(Spacer(1, 8))

    if not df.empty:
        # Get unique job titles
        unique_job_titles = df["Job Title"].unique().tolist()
        
        # Classify a sample of job titles
        sample_job_titles = random.sample(unique_job_titles, min(5, len(unique_job_titles)))
        
        job_classification_data = [["Job Title", "Predicted Role"]]
        for job_title in sample_job_titles:
            predicted_role = predict_job_role(job_title)
            job_classification_data.append([job_title, predicted_role])
        
        job_classification_table = Table(job_classification_data)
        job_classification_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkcyan),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.lightcyan),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 10)
        ]))
        story.append(job_classification_table)
        story.append(Spacer(1, 20))
    else:
        story.append(Paragraph("No job titles available for classification.", styles["Normal"]))
        story.append(Spacer(1, 20))

    # Salary Prediction
    story.append(Paragraph("Salary Predictions", heading_style))
    story.append(Paragraph("This section provides salary predictions for sample job profiles based on a machine learning model.", styles["Normal"]))
    story.append(Spacer(1, 8))

    if not df.empty:
        # Create a few sample profiles for prediction
        sample_profiles = [
            {"job_role": "Data Scientist", "skills": ["Python", "Machine Learning"], "location": "Bengaluru", "experience": 5},
            {"job_role": "Full Stack Developer", "skills": ["JavaScript", "React", "Node.js"], "location": "Pune", "experience": 3},
            {"job_role": "ML Engineer", "skills": ["Python", "TensorFlow"], "location": "Hyderabad", "experience": 2}
        ]

        salary_prediction_data = [["Profile", "Predicted Salary (LPA)"]]
        for profile in sample_profiles:
            predicted_salary = predict_salary(profile["job_role"], profile["skills"], profile["location"], profile["experience"])
            profile_str = f"{profile['job_role']} in {profile['location']} with {profile['experience']} years exp."
            salary_prediction_data.append([profile_str, f"₹{predicted_salary:.1f}L"])

        salary_prediction_table = Table(salary_prediction_data)
        salary_prediction_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkred),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.lightcoral),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTSIZE", (0, 1), (-1, -1), 10)
        ]))
        story.append(salary_prediction_table)
        story.append(Spacer(1, 20))
    else:
        story.append(Paragraph("No data available for salary prediction.", styles["Normal"]))
        story.append(Spacer(1, 20))

    # Salary Analysis
    story.append(Paragraph("Salary Analysis by Skills", heading_style))
    
    salary_by_skill = df.groupby('Tech Skill')['Salary (in LPA)'].agg(['mean', 'median', 'count']).round(1)
    salary_by_skill = salary_by_skill.sort_values('mean', ascending=False).head(10)
    
    salary_data = [['Skill', 'Avg Salary (₹L)', 'Median (₹L)', 'Job Count']]
    for skill, row in salary_by_skill.iterrows():
        salary_data.append([skill, f"{row['mean']:.1f}", f"{row['median']:.1f}", str(int(row['count']))])
    
    salary_table = Table(salary_data)
    salary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10)
    ]))
    
    story.append(salary_table)
    story.append(Spacer(1, 20))
    
    # Geographic Distribution
    story.append(Paragraph("Geographic Distribution", heading_style))
    
    location_analysis = df['Location'].value_counts().head(10)
    location_data = [['Rank', 'Location', 'Job Openings', 'Percentage']]
    
    for i, (location, count) in enumerate(location_analysis.items(), 1):
        percentage = (count / len(df)) * 100
        location_data.append([str(i), location, str(count), f"{percentage:.1f}%"])
    
    location_table = Table(location_data)
    location_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lavender),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10)
    ]))
    
    story.append(location_table)
    story.append(Spacer(1, 20))
    
    # Company Analysis
    story.append(Paragraph("Top Hiring Companies", heading_style))
    
    company_analysis = df['Company'].value_counts().head(10)
    company_data = [['Rank', 'Company', 'Job Openings']]
    
    for i, (company, count) in enumerate(company_analysis.items(), 1):
        company_data.append([str(i), company, str(count)])
    
    company_table = Table(company_data)
    company_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.maroon),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.pink),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10)
    ]))
    
    story.append(company_table)
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("This report was generated by the Tech Skills BI Dashboard", styles['Normal']))
    story.append(Paragraph("Team: Om Aravindhashan | Raghul", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def display_career_roadmap(df, dream_job, target_location):
    """Display personalized career roadmap based on dream job and location"""
    
    # Career roadmaps database
    roadmaps = {
        "data scientist": {
            "core_skills": ["Python", "Machine Learning", "Statistics", "SQL", "Pandas", "NumPy", "Scikit-learn"],
            "advanced_skills": ["Deep Learning", "TensorFlow", "PyTorch", "R", "Tableau", "Power BI"],
            "soft_skills": ["Problem Solving", "Communication", "Business Acumen"],
            "experience_levels": {
                "Entry Level (0-2 years)": "₹8-15L",
                "Mid Level (2-5 years)": "₹15-30L", 
                "Senior Level (5+ years)": "₹30-60L"
            },
            "career_path": [
                "Data Analyst → Data Scientist → Senior Data Scientist → Lead Data Scientist → Chief Data Officer"
            ]
        },
        "full stack developer": {
            "core_skills": ["JavaScript", "React", "Node.js", "HTML", "CSS", "Git", "REST APIs"],
            "advanced_skills": ["TypeScript", "GraphQL", "Docker", "AWS", "MongoDB", "PostgreSQL"],
            "soft_skills": ["Problem Solving", "Team Collaboration", "Project Management"],
            "experience_levels": {
                "Entry Level (0-2 years)": "₹6-12L",
                "Mid Level (2-5 years)": "₹12-25L",
                "Senior Level (5+ years)": "₹25-50L"
            },
            "career_path": [
                "Junior Developer → Full Stack Developer → Senior Developer → Tech Lead → Engineering Manager"
            ]
        },
        "ml engineer": {
            "core_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "Docker", "Kubernetes"],
            "advanced_skills": ["MLOps", "AWS", "Azure", "Apache Spark", "Kafka", "Microservices"],
            "soft_skills": ["System Design", "Problem Solving", "Technical Communication"],
            "experience_levels": {
                "Entry Level (0-2 years)": "₹10-18L",
                "Mid Level (2-5 years)": "₹18-35L",
                "Senior Level (5+ years)": "₹35-70L"
            },
            "career_path": [
                "ML Intern → ML Engineer → Senior ML Engineer → ML Architect → Head of ML"
            ]
        },
        "devops engineer": {
            "core_skills": ["Docker", "Kubernetes", "AWS", "Jenkins", "Git", "Linux", "Python"],
            "advanced_skills": ["Terraform", "Ansible", "Prometheus", "Grafana", "ELK Stack"],
            "soft_skills": ["Automation Mindset", "Troubleshooting", "Collaboration"],
            "experience_levels": {
                "Entry Level (0-2 years)": "₹8-15L",
                "Mid Level (2-5 years)": "₹15-30L",
                "Senior Level (5+ years)": "₹30-55L"
            },
            "career_path": [
                "System Admin → DevOps Engineer → Senior DevOps → DevOps Architect → VP Engineering"
            ]
        }
    }
    
    # Find matching roadmap
    dream_job_lower = dream_job.lower().strip()
    matching_roadmap = None
    
    for key, roadmap in roadmaps.items():
        if key in dream_job_lower or any(word in dream_job_lower for word in key.split()):
            matching_roadmap = roadmap
            break
    
    if not matching_roadmap:
        # Create generic roadmap based on available data
        st.info(f"Creating personalized roadmap for **{dream_job}** based on market data...")
        
        # Find similar skills in dataset
        similar_skills = []
        job_words = dream_job.lower().split()
        for skill in df['Tech Skill'].unique():
            if any(word in skill.lower() for word in job_words):
                similar_skills.append(skill)
        
        if similar_skills:
            st.success(f"Found {len(similar_skills)} relevant skills in the market for **{dream_job}**")
            
            # Display relevant skills with market data
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📋 Relevant Market Skills:**")
                for skill in similar_skills[:8]:  # Show top 8
                    skill_data = df[df['Tech Skill'] == skill]
                    avg_salary = skill_data['Salary (in LPA)'].mean()
                    job_count = len(skill_data)
                    st.write(f"• **{skill}** - {job_count} jobs, ₹{avg_salary:.1f}L avg")
            
            with col2:
                st.markdown("**💰 Salary Insights:**")
                if target_location != "Any Location":
                    location_data = df[df['Location'] == target_location]
                    if not location_data.empty:
                        avg_salary_location = location_data['Salary (in LPA)'].mean()
                        st.write(f"Average salary in **{target_location}**: ₹{avg_salary_location:.1f}L")
                        
                        # Find relevant jobs in location
                        relevant_jobs = location_data[location_data['Tech Skill'].isin(similar_skills)]
                        if not relevant_jobs.empty:
                            st.write(f"**{len(relevant_jobs)}** relevant positions in {target_location}")
                            top_companies = relevant_jobs['Company'].value_counts().head(3)
                            st.write("Top hiring companies:")
                            for company, count in top_companies.items():
                                st.write(f"• {company} ({count} positions)")
        else:
            st.warning(f"No direct matches found for **{dream_job}** in current market data. Consider exploring related roles or upskilling in trending technologies.")
        
        return
    
    # Display structured roadmap
    st.success(f"Career roadmap generated for **{dream_job.title()}**")
    
    # Create tabs for different aspects
    roadmap_tab1, roadmap_tab2, roadmap_tab3, roadmap_tab4 = st.tabs([
        "📚 Skills Required", "💰 Salary Expectations", "🛤️ Career Path", "📍 Location Insights"
    ])
    
    with roadmap_tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Core Skills (Must Have):**")
            for skill in matching_roadmap["core_skills"]:
                # Check if skill exists in dataset
                skill_data = df[df['Tech Skill'].str.contains(skill, case=False, na=False)]
                if not skill_data.empty:
                    job_count = len(skill_data)
                    avg_salary = skill_data['Salary (in LPA)'].mean()
                    st.write(f"✅ **{skill}** - {job_count} jobs, ₹{avg_salary:.1f}L avg")
                else:
                    st.write(f"📚 **{skill}** - High demand skill")
        
        with col2:
            st.markdown("**Advanced Skills (Nice to Have):**")
            for skill in matching_roadmap["advanced_skills"]:
                skill_data = df[df['Tech Skill'].str.contains(skill, case=False, na=False)]
                if not skill_data.empty:
                    job_count = len(skill_data)
                    avg_salary = skill_data['Salary (in LPA)'].mean()
                    st.write(f"🚀 **{skill}** - {job_count} jobs, ₹{avg_salary:.1f}L avg")
                else:
                    st.write(f"🎯 **{skill}** - Emerging technology")
    
    with roadmap_tab2:
        st.markdown("**Expected Salary Ranges:**")
        for level, salary_range in matching_roadmap["experience_levels"].items():
            st.write(f"• **{level}**: {salary_range}")
        
        # Show location-specific data if available
        if target_location != "Any Location":
            location_data = df[df['Location'] == target_location]
            if not location_data.empty:
                avg_salary_location = location_data['Salary (in LPA)'].mean()
                st.info(f"Average salary in **{target_location}**: ₹{avg_salary_location:.1f}L per annum")
    
    with roadmap_tab3:
        st.markdown("**Career Progression Path:**")
        for path in matching_roadmap["career_path"]:
            st.write(f"📈 {path}")
        
        st.markdown("**Soft Skills Development:**")
        for skill in matching_roadmap["soft_skills"]:
            st.write(f"• {skill}")
    
    with roadmap_tab4:
        if target_location != "Any Location":
            location_data = df[df['Location'] == target_location]
            if not location_data.empty:
                # Find relevant jobs
                relevant_skills = matching_roadmap["core_skills"] + matching_roadmap["advanced_skills"]
                relevant_jobs = location_data[location_data['Tech Skill'].isin(relevant_skills)]
                
                if not relevant_jobs.empty:
                    st.write(f"**{len(relevant_jobs)}** relevant positions found in {target_location}")
                    
                    # Top companies
                    top_companies = relevant_jobs['Company'].value_counts().head(5)
                    st.markdown("**Top Hiring Companies:**")
                    for i, (company, count) in enumerate(top_companies.items(), 1):
                        st.write(f"{i}. **{company}** - {count} positions")
                    
                    # Average salary for relevant positions
                    avg_relevant_salary = relevant_jobs['Salary (in LPA)'].mean()
                    st.success(f"Average salary for {dream_job} roles in {target_location}: ₹{avg_relevant_salary:.1f}L")
                else:
                    st.warning(f"Limited opportunities found for {dream_job} in {target_location}. Consider expanding your location preferences.")
            else:
                st.warning(f"No data available for {target_location} in current dataset.")
        else:
            # Show top locations for this role
            relevant_skills = matching_roadmap["core_skills"] + matching_roadmap["advanced_skills"]
            relevant_jobs = df[df['Tech Skill'].isin(relevant_skills)]
            
            if not relevant_jobs.empty:
                top_locations = relevant_jobs['Location'].value_counts().head(5)
                st.markdown("**Best Locations for Your Dream Job:**")
                for i, (location, count) in enumerate(top_locations.items(), 1):
                    location_avg_salary = relevant_jobs[relevant_jobs['Location'] == location]['Salary (in LPA)'].mean()
                    st.write(f"{i}. **{location}** - {count} jobs, ₹{location_avg_salary:.1f}L avg salary")

def send_thank_you_email(user_email):
    """Send a creative thank you email (placeholder for now)"""
    # Since no email authentication is needed, we'll show a creative message
    thank_you_message = f"""
    🌟 Thank you for connecting with us, {user_email}! 🌟
    
    Welcome to the future of tech skills intelligence! 
    
    You've just joined an exclusive community of forward-thinking professionals who stay ahead 
    of the curve in the rapidly evolving tech landscape. 
    
    🚀 What's Next?
    • Get insights on emerging technologies before they become mainstream
    • Discover salary trends that help you negotiate better compensation  
    • Identify high-growth locations for your next career move
    • Track demand patterns for strategic skill development
    
    💡 Pro Tip: The most successful professionals don't just follow trends - they anticipate them!
    
    Stay curious, stay innovative, and let data guide your career decisions.
    
    Best regards,
    The Tech Skills BI Team
    Om Aravindhashan.S (23MID0222) & Raghul (23MID0322)
    
    P.S. Keep this dashboard bookmarked - we're constantly adding new features and insights! 📊✨
    """
    return thank_you_message

def main():
    """Main function to run the Streamlit app"""
    st.set_page_config(
        page_title="Tech Skills BI Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load data first
    df, files_processed = load_local_csv_files("data")
    
    if df.empty:
        st.error("No valid data found. Please ensure CSV files are available in the data directory.")
        display_data_setup_instructions()
        return
    
    # Theme toggle
    with st.sidebar:
        st.markdown("### Settings")
        theme_option = st.selectbox(
            "Theme",
            ["Light", "Dark"],
            index=0
        )
        
        # PDF Export button
        if st.button("📄 Export Full Report as PDF"):
            try:
                # Get dream job and location from session state if available
                dream_job_for_pdf = st.session_state.get('dream_job_input', None)
                target_location_for_pdf = st.session_state.get('target_location_select', None)
                
                pdf_buffer = create_comprehensive_pdf_report(df, None, dream_job_for_pdf, target_location_for_pdf)
                st.download_button(
                    label="📥 Download Report",
                    data=pdf_buffer.getvalue(),
                    file_name=f"tech_skills_comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    help="Download comprehensive market analysis report"
                )
                st.success("Report generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
        
        st.markdown("---")
    
    # Apply dark theme CSS if selected
    if theme_option == "Dark":
        st.markdown("""
            <style>
                .stApp {
                    background-color: #0e1117;
                    color: #fafafa;
                }
                .stSelectbox > div > div {
                    background-color: #262730;
                    border-color: #4f4f4f;
                }
                .stMultiSelect > div > div {
                    background-color: #262730;
                    border-color: #4f4f4f;
                }
                .stSlider > div > div > div {
                    background-color: #262730;
                }
                .stDateInput > div > div > input {
                    background-color: #262730;
                    border-color: #4f4f4f;
                    color: #fafafa;
                }
                .stTextInput > div > div > input {
                    background-color: #262730;
                    border-color: #4f4f4f;
                    color: #fafafa;
                }
            </style>
        """, unsafe_allow_html=True)
    
    # Title and description
    st.title("Tech Skills Business Intelligence Dashboard")
    st.markdown("### Comprehensive analysis of tech skill demand trends in the job market")
    
    # Animated scrolling metric cards
    st.markdown("""
        <style>
        .metrics-container {
            overflow: hidden;
            white-space: nowrap;
            padding: 1rem 0;
            margin: 1rem 0;
            position: relative;
        }
        .metrics-scroll {
            display: inline-block;
            animation: scroll-left 20s linear infinite;
            white-space: nowrap;
        }
        .metric-card {
            display: inline-block;
            padding: 1rem 3rem;
            text-align: center;
            margin: 0 1rem;
            border-right: 2px solid rgba(128,128,128,0.3);
            vertical-align: top;
            min-width: 250px;
        }
        .metric-card:last-child {
            border-right: none;
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: bold;
            margin: 0.5rem 0;
            line-height: 1.2;
            color: #1f77b4;
        }
        .metric-label {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #333;
        }
        .metric-delta {
            font-size: 0.85rem;
            margin-top: 0.5rem;
            background: rgba(31, 119, 180, 0.1);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            display: inline-block;
            color: #1f77b4;
        }
        @keyframes scroll-left {
            0% {
                transform: translateX(100%);
            }
            100% {
                transform: translateX(-100%);
            }
        }
        .metrics-container:hover .metrics-scroll {
            animation-play-state: paused;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Calculate key metrics
    most_frequent_skill = df['Tech Skill'].value_counts().index[0]
    most_common_company = df['Company'].value_counts().index[0]
    top_location = df['Location'].value_counts().index[0]
    avg_salary = df['Salary (in LPA)'].mean()
    
    # Create scrolling metrics HTML
    metrics_html = f"""
    <div class="metrics-container">
        <div class="metrics-scroll">
            <div class="metric-card">
                <div class="metric-label">Most Frequent Skill</div>
                <div class="metric-value">{most_frequent_skill}</div>
                <div class="metric-delta">↗ {df['Tech Skill'].value_counts().iloc[0]} jobs</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Most Common Company</div>
                <div class="metric-value">{most_common_company}</div>
                <div class="metric-delta">↗ {df['Company'].value_counts().iloc[0]} openings</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Top Hiring Location</div>
                <div class="metric-value">{top_location}</div>
                <div class="metric-delta">↗ {df['Location'].value_counts().iloc[0]} positions</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Average Salary</div>
                <div class="metric-value">₹{avg_salary:.1f}L</div>
                <div class="metric-delta">₹{df['Salary (in LPA)'].median():.1f}L median</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(metrics_html, unsafe_allow_html=True)
    
    # Smart Insights Box
    st.markdown("---")
    st.subheader("Smart Insights")
    
    # Generate insights from data analysis
    total_skills = df['Tech Skill'].nunique()
    skill_counts = df['Tech Skill'].value_counts()
    location_counts = df['Location'].value_counts()
    
    insights_col1, insights_col2 = st.columns(2)
    
    with insights_col1:
        st.info(
            f"**{most_frequent_skill}** is the most demanded skill appearing in "
            f"**{skill_counts.iloc[0]}** job listings, representing "
            f"**{(skill_counts.iloc[0]/len(df)*100):.1f}%** of all opportunities."
        )
        
        # Top 3 skills insight
        top_3_skills = skill_counts.head(3)
        if len(top_3_skills) >= 3:
            top_3_names = ", ".join([str(x) for x in top_3_skills.index[:2]]) + f", and {str(top_3_skills.index[2])}"
            st.info(
                f"The top 3 skills (**{top_3_names}**) account for "
                f"**{(top_3_skills.sum()/len(df)*100):.1f}%** of all job postings."
            )
        else:
            st.info(f"Currently tracking **{len(skill_counts)}** different tech skills in the market.")
    
    with insights_col2:
        if len(location_counts) >= 2:
            st.info(
                f"Most jobs are in **{top_location}** with **{location_counts.iloc[0]}** openings, "
                f"followed by **{str(location_counts.index[1])}** with **{location_counts.iloc[1]}** positions."
            )
        else:
            st.info(f"All job opportunities are concentrated in **{top_location}**.")
        
        # Salary insight
        high_paying_skills = df.groupby('Tech Skill')['Salary (in LPA)'].mean().nlargest(3)
        highest_paying = high_paying_skills.index[0]
        st.info(
            f"**{highest_paying}** offers the highest average salary at "
            f"**₹{high_paying_skills.iloc[0]:.1f}L**, which is "
            f"**{((high_paying_skills.iloc[0] - avg_salary)/avg_salary*100):.1f}%** above market average."
        )
    
    # Dream Job Roadmap Section
    st.markdown("---")
    st.subheader("Career Roadmap & Personalized Insights")
    st.markdown("Get personalized career guidance based on your dream job and target location")
    
    roadmap_col1, roadmap_col2 = st.columns([2, 1])
    
    with roadmap_col1:
        dream_job = st.text_input(
            "What's your dream job role?",
            placeholder="e.g., Data Scientist, Full Stack Developer, ML Engineer",
            help="Enter your target job role to get personalized career guidance and skill requirements",
            key="dream_job_input"
        )
    
    with roadmap_col2:
        target_location = st.selectbox(
            "Preferred Location",
            ["Any Location"] + sorted(df['Location'].unique().tolist()),
            help="Select your target work location for localized insights",
            key="target_location_select"
        )
    
    # Display roadmap if dream job is provided
    if dream_job:
        display_career_roadmap(df, dream_job, target_location)
    
    # Email Subscription Feature
    st.markdown("---")
    st.subheader("Get Your Personalized Report")
    st.markdown("Subscribe to receive a comprehensive PDF report tailored to your career goals and selected preferences")
    
    subscription_col1, subscription_col2 = st.columns([3, 1])
    
    with subscription_col1:
        user_email = st.text_input(
            "Enter your email to get personalized report",
            placeholder="your.email@example.com",
            help="We'll send you insights about trending skills and market changes",
            key="email_subscription_input"
        )
    
    with subscription_col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        if st.button("Subscribe & Get PDF Report", type="primary"):
            if user_email and "@" in user_email and "." in user_email:
                # Save email to file
                try:
                    # Create emails directory if it doesn't exist
                    if not os.path.exists("emails"):
                        os.makedirs("emails")
                    
                    # Save to CSV file
                    email_file = "emails/subscriptions.csv"
                    file_exists = os.path.isfile(email_file)
                    
                    with open(email_file, 'a', newline='') as csvfile:
                        fieldnames = ['email', 'subscription_date', 'ip_info']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        
                        if not file_exists:
                            writer.writeheader()
                        
                        writer.writerow({
                            'email': user_email,
                            'subscription_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'ip_info': 'dashboard_subscription'
                        })
                    
                    # Generate PDF report with personalized content
                    pdf_buffer = create_comprehensive_pdf_report(df, user_email, dream_job, target_location)
                    
                    # Display thank you message
                    thank_you_msg = send_thank_you_email(user_email)
                    st.success("Subscribed successfully!")
                    
                    # Show creative thank you message
                    st.info(thank_you_msg)
                    
                    # Provide PDF download
                    st.download_button(
                        label="📄 Download Your Comprehensive Report",
                        data=pdf_buffer.getvalue(),
                        file_name=f"tech_skills_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        help="Download your personalized tech skills market analysis report"
                    )
                    
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
                    st.success("Subscribed successfully! You'll receive updates on rising tech skills.")
            else:
                st.error("Please enter a valid email address")
    
     # Create tabs for different sections
    tabs = ["Over    tabs = ["Overv    tabs = ["Overview", "Visualizations", "Raw Data", "Dynamic Learning Path"]
    selected_tab = st.sidebar.radio("Navigation", tabs), tabs)", tabs)

    # Main content based on tab selection
    if selected_tab == "Dynamic Learning Path":
        st.header(" Personalized Learning Path Generator")
        user_skills_input = st.text_input("Enter your current skills (comma-separated)", "Python, Pandas, SQL")
        user_skills = [skill.strip() for skill in user_skills_input.split(",")]
        dream_job_input = st.text_input("Enter your dream job", "Data Scientist")
        target_location_select = st.selectbox("Select Target Location", ["Any Location"] + sorted(df["Location"].unique().tolist()))

        if st.button("Generate Learning Path"):
            if user_skills and dream_job_input:
                generate_dynamic_learning_path(df, user_skills, dream_job_input, target_location_select)
            else:
                st.warning("Please enter your skills and dream job.")
idebar.header("Filters")
    
    # Skill filter
    all_skills = sorted(df['Tech Skill'].unique())
    selected_skills = st.sidebar.multiselect(
        "Select Tech Skills",
        options=all_skills,
        default=all_skills,
        help="Select one or more tech skills to filter the data"
    )
    
    # Location filter
    all_locations = sorted(df['Location'].unique())
    selected_locations = st.sidebar.multiselect(
        "Select Locations",
        options=all_locations,
        default=all_locations,
        help="Select one or more locations to filter the data"
    )
    
    # Experience range filter
    min_exp, max_exp = st.sidebar.slider(
        "Experience Range (years)",
        min_value=int(df['Experience Required (in years)'].min()),
        max_value=int(df['Experience Required (in years)'].max()),
        value=(
            int(df['Experience Required (in years)'].min()),
            int(df['Experience Required (in years)'].max())
        ),
        help="Select the experience range in years"
    )
    
    # Date range filter with month/year options
    df_copy = df.copy()
    df_copy['Date Posted'] = pd.to_datetime(df_copy['Date Posted'])
    min_date = df_copy['Date Posted'].min().date()
    max_date = df_copy['Date Posted'].max().date()
    
    # Add filter type selection
    filter_type = st.sidebar.radio(
        "Date Filter Type",
        ["Date Range", "Month/Year"],
        help="Choose how to filter by date"
    )
    
    if filter_type == "Date Range":
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Select the date range for job postings"
        )
    else:
        # Month/Year selection
        years = sorted(df_copy['Date Posted'].dt.year.unique())
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            from_year = st.selectbox("From Year", years, index=0)
            from_month = st.selectbox("From Month", months, index=0)
        with col2:
            to_year = st.selectbox("To Year", years, index=len(years)-1)
            to_month = st.selectbox("To Month", months, index=len(months)-1)
        
        # Convert to date range
        from_date = datetime(from_year, months.index(from_month) + 1, 1).date()
        to_date = datetime(to_year, months.index(to_month) + 1, 
                          28 if months.index(to_month) + 1 == 2 else 30 if months.index(to_month) + 1 in [4,6,9,11] else 31).date()
        date_range = (from_date, to_date)
    
    # Apply filters to create filtered dataset
    filtered_df = df.copy()
    filtered_df['Date Posted'] = pd.to_datetime(filtered_df['Date Posted'])
    
    filtered_df = filtered_df[
        (filtered_df['Tech Skill'].isin(selected_skills)) &
        (filtered_df['Location'].isin(selected_locations)) &
        (filtered_df['Experience Required (in years)'] >= min_exp) &
        (filtered_df['Experience Required (in years)'] <= max_exp)
    ]
    
    # Apply date filter if both dates are selected
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['Date Posted'].dt.date >= start_date) &
            (filtered_df['Date Posted'].dt.date <= end_date)
        ]
    
    with tab1:
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Job Openings", len(filtered_df))
        
        with col2:
            st.metric("Unique Skills", filtered_df['Tech Skill'].nunique())
        
        with col3:
            st.metric("Unique Companies", filtered_df['Company'].nunique())
        
        with col4:
            avg_salary = filtered_df['Salary (in LPA)'].mean()
            st.metric("Avg Salary (LPA)", f"{avg_salary:.1f}" if not pd.isna(avg_salary) else "N/A")
        
        # Check if filtered data is empty
        if filtered_df.empty:
            st.warning("No data matches the selected filters. Please adjust your filter criteria.")
            return
        
        # Key insights section
        st.markdown("---")
        st.subheader("Key Insights")
        
        # Top skill
        top_skill = filtered_df['Tech Skill'].value_counts().index[0]
        top_skill_count = filtered_df['Tech Skill'].value_counts().iloc[0]
        
        # Top paying skill
        top_paying_skill = filtered_df.groupby('Tech Skill')['Salary (in LPA)'].mean().idxmax()
        top_paying_salary = filtered_df.groupby('Tech Skill')['Salary (in LPA)'].mean().max()
        
        # Most hiring location
        top_location = filtered_df['Location'].value_counts().index[0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"Most In-Demand Skill: **{top_skill}** ({top_skill_count} openings)")
        with col2:
            st.info(f"Highest Paying Skill: **{top_paying_skill}** (₹{top_paying_salary:.1f}L avg)")
        with col3:
            st.info(f"Top Hiring Location: **{top_location}**")
    
    with tab2:
        if filtered_df.empty:
            st.warning("No data matches the selected filters.")
            return
            
        st.subheader("Visualizations")
        
        # Create visualization options
        viz_option = st.selectbox(
            "Select Visualization Type",
            ["Skills Analysis", "Salary Analysis", "Geographic Analysis", "Temporal Trends", 
             "Skill Comparison", "Skill Co-occurrence", "Demand Saturation", "Trend Forecasting"]
        )
        
        if viz_option == "Skills Analysis":
            # Top skills chart
            st.subheader("Most In-Demand Tech Skills")
            skills_chart = create_top_skills_chart(filtered_df)
            st.plotly_chart(skills_chart, use_container_width=True)
            
        elif viz_option == "Salary Analysis":
            # Interactive salary vs skills
            st.subheader("Interactive Salary Analysis")
            
            # Salary by skill
            salary_by_skill = filtered_df.groupby('Tech Skill')['Salary (in LPA)'].agg(['mean', 'median', 'count']).reset_index()
            salary_by_skill = salary_by_skill.sort_values('mean', ascending=False).head(15)
            
            fig = px.bar(
                salary_by_skill,
                x='Tech Skill',
                y='mean',
                title="Average Salary by Tech Skill",
                labels={'mean': 'Average Salary (LPA)', 'Tech Skill': 'Technology Skill'},
                hover_data={'median': True, 'count': True}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Salary by location
            salary_by_location = filtered_df.groupby('Location')['Salary (in LPA)'].mean().reset_index()
            salary_by_location = salary_by_location.sort_values('Salary (in LPA)', ascending=False)
            
            fig2 = px.bar(
                salary_by_location,
                x='Location',
                y='Salary (in LPA)',
                title="Average Salary by Location",
                labels={'Salary (in LPA)': 'Average Salary (LPA)'}
            )
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
            
        elif viz_option == "Geographic Analysis":
            # Location distribution
            st.subheader("Job Distribution by Location")
            location_chart = create_location_pie_chart(filtered_df)
            st.plotly_chart(location_chart, use_container_width=True)
            
        elif viz_option == "Temporal Trends":
            # Skill demand trends
            st.subheader("Skill Demand Trends Over Time")
            trends_chart = create_skill_trends_chart(filtered_df)
            st.plotly_chart(trends_chart, use_container_width=True)
            
        elif viz_option == "Skill Comparison":
            # Skill comparison interface
            st.subheader("Compare Two Tech Skills")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                skill_a = st.selectbox(
                    "Select First Skill",
                    options=sorted(filtered_df['Tech Skill'].unique()),
                    index=0,
                    key="skill_a_viz"
                )
            
            with col2:
                skill_b = st.selectbox(
                    "Select Second Skill",
                    options=sorted(filtered_df['Tech Skill'].unique()),
                    index=1 if len(sorted(filtered_df['Tech Skill'].unique())) > 1 else 0,
                    key="skill_b_viz"
                )
            
            with col3:
                comparison_location = st.selectbox(
                    "Select Location (Optional)",
                    options=["All Locations"] + sorted(filtered_df['Location'].unique()),
                    index=0,
                    key="comparison_location_viz"
                )
            
            if skill_a != skill_b:
                # Demand comparison
                comparison_chart = create_skill_comparison_chart(
                    filtered_df, skill_a, skill_b, 
                    comparison_location if comparison_location != "All Locations" else None
                )
                st.plotly_chart(comparison_chart, use_container_width=True)
                
                # Salary comparison
                salary_chart = create_salary_comparison_chart(
                    filtered_df, skill_a, skill_b,
                    comparison_location if comparison_location != "All Locations" else None
                )
                st.plotly_chart(salary_chart, use_container_width=True)
            else:
                st.warning("Please select two different skills for comparison.")
                
        elif viz_option == "Skill Co-occurrence":
            st.subheader("Skill Co-occurrence Analysis")
            st.write("Shows which skills often appear together in job postings")
            
            # Create skill co-occurrence matrix
            skill_cooccurrence = create_skill_cooccurrence_heatmap(filtered_df)
            st.plotly_chart(skill_cooccurrence, use_container_width=True)
            
        elif viz_option == "Demand Saturation":
            st.subheader("Demand Saturation Index")
            st.write("Shows the ratio of job openings to unique companies for each skill")
            
            # Create demand saturation visualization
            saturation_chart = create_demand_saturation_index(filtered_df)
            st.plotly_chart(saturation_chart, use_container_width=True)
            
            # Add explanation
            st.info("Higher saturation index indicates more jobs per company, suggesting higher demand relative to market saturation.")
            
        elif viz_option == "Trend Forecasting":
            st.subheader("Trend Forecasting")
            st.write("Predict future demand trends for specific skills")
            
            # Skill selection for forecasting
            forecast_skill = st.selectbox(
                "Select Skill for Forecasting",
                options=sorted(filtered_df['Tech Skill'].unique()),
                key="forecast_skill"
            )
            
            if forecast_skill:
                forecast_chart = create_trend_forecast(filtered_df, forecast_skill)
                if forecast_chart:
                    st.plotly_chart(forecast_chart, use_container_width=True)
                else:
                    st.warning("Insufficient data for forecasting this skill. Need at least 3 months of data.")
    
    with tab3:
        st.subheader("Raw Data")
        
        if filtered_df.empty:
            st.warning("No data matches the selected filters.")
            return
            
        # Show filtered data count
        st.write(f"Showing {len(filtered_df):,} records (filtered from {len(df):,} total records)")
        
        # Data table with search functionality
        search_term = st.text_input("Search in data", placeholder="Type to search...")
        
        if search_term:
            # Search across all string columns
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            display_df = filtered_df[mask]
            st.write(f"Found {len(display_df)} records matching '{search_term}'")
        else:
            display_df = filtered_df
        
        # Remove Source File column for cleaner display
        if 'Source File' in display_df.columns:
            display_columns = [col for col in display_df.columns if col != 'Source File']
            display_df = display_df[display_columns]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p><strong>Tech Skills Business Intelligence Dashboard</strong></p>
            <p>Team Members: Om Aravindhashan.S (23MID0222) | Raghul (23MID0322)</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()


def generate_dynamic_learning_path(df, user_skills, dream_job, target_location):
    st.subheader(f"Dynamic Learning Path for: {dream_job}")

    # 1. Get recommendations based on current skills
    recommendations = get_skill_recommendations(df, user_skills, top_n=10)

    # 2. Find skills required for the dream job from existing roadmaps or data
    dream_job_skills = []
    roadmaps = {
        "data scientist": ["Python", "Machine Learning", "SQL"],
        "full stack developer": ["JavaScript", "React", "Node.js"],
        "ml engineer": ["Python", "TensorFlow", "PyTorch"],
        "devops engineer": ["Docker", "Kubernetes", "AWS"]
    }
    dream_job_lower = dream_job.lower()
    for key, skills in roadmaps.items():
        if key in dream_job_lower:
            dream_job_skills = skills
            break

    if not dream_job_skills:
        # Fallback to data-driven skill extraction if no roadmap matches
        dream_job_skills = df[df["Job Title"].str.contains(dream_job, case=False, na=False)]["Tech Skill"].value_counts().head(5).index.tolist()

    # 3. Combine and prioritize skills
    learning_path = []
    if not recommendations.empty:
        st.write("**Recommended skills to learn based on your current skillset:**")
        for skill in recommendations["Recommended Skill"]:
            if skill not in user_skills:
                learning_path.append(skill)
                st.write(f"- **{skill}** (High co-occurrence with your skills)")

    if dream_job_skills:
        st.write(f"**Core skills for a {dream_job}:**")
        for skill in dream_job_skills:
            if skill not in user_skills and skill not in learning_path:
                learning_path.append(skill)
                st.write(f"- **{skill}** (Essential for this role)")

    if not learning_path:
        st.success("You already have a strong skill set for this role! Consider exploring advanced topics.")
    else:
        st.write("**Your Personalized Learning Path:**")
        for i, skill in enumerate(learning_path, 1):
            st.write(f"{i}. {skill}")


