import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Import custom modules
from modules.data_loader import load_job_data, get_data_source_info, available_sources
from modules.data_cleaner import clean_job_data, validate_data, get_data_summary
from modules.ml_forecast import forecast_skill_demand, get_forecast_insights
from modules.recommendation_engine import recommend_skills, recommend_for_job_role, get_skill_pairs, get_learning_path
from modules.learning_resources import get_learning_path_with_resources
from modules.resume_analyzer import analyze_resume, extract_text, save_report

# Page configuration
st.set_page_config(
    page_title="Tech Skill Tracker - Business Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        color: #2c3e50;
        text-align: center;
        padding: 1.5rem 0;
        border-bottom: 3px solid #3498db;
        margin-bottom: 2rem;
    }
    .subheader-text {
        font-size: 1rem;
        color: #7f8c8d;
        text-align: center;
        margin-top: -1rem;
        margin-bottom: 2rem;
    }
    .stPlotlyChart {
        background-color: white;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def create_professional_forecast_chart(forecast_df, skill_name):
    """Create clean, professional forecast visualization"""
    fig = go.Figure()
    
    # Historical data
    historical = forecast_df[forecast_df['Actual'].notna()]
    if not historical.empty:
        fig.add_trace(go.Scatter(
            x=historical['Date'],
            y=historical['Actual'],
            mode='lines+markers',
            name='Historical Data',
            line=dict(color='#3498db', width=3),
            marker=dict(size=8, symbol='circle'),
            hovertemplate='<b>Date:</b> %{x|%Y-%m}<br><b>Jobs:</b> %{y}<extra></extra>'
        ))
    
    # Forecast data
    forecast = forecast_df[forecast_df['Forecast'].notna() & forecast_df['Actual'].isna()]
    if not forecast.empty:
        fig.add_trace(go.Scatter(
            x=forecast['Date'],
            y=forecast['Forecast'],
            mode='lines+markers',
            name='Predicted Demand',
            line=dict(color='#e74c3c', width=3, dash='dash'),
            marker=dict(size=8, symbol='diamond'),
            hovertemplate='<b>Date:</b> %{x|%Y-%m}<br><b>Forecast:</b> %{y:.0f}<extra></extra>'
        ))
    
    # Confidence interval (if available)
    if 'Upper_Bound' in forecast_df.columns and forecast_df['Upper_Bound'].notna().any():
        forecast_with_bounds = forecast_df[forecast_df['Upper_Bound'].notna()]
        fig.add_trace(go.Scatter(
            x=forecast_with_bounds['Date'],
            y=forecast_with_bounds['Upper_Bound'],
            mode='lines',
            name='Upper Confidence',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=forecast_with_bounds['Date'],
            y=forecast_with_bounds['Lower_Bound'],
            mode='lines',
            name='Confidence Interval',
            line=dict(width=0),
            fillcolor='rgba(231, 76, 60, 0.15)',
            fill='tonexty',
            hovertemplate='<b>Range:</b> %{y:.0f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(
            text=f'Demand Forecast Analysis: {skill_name}',
            font=dict(size=18, color='#2c3e50', family='Arial')
        ),
        xaxis=dict(
            title='Time Period',
            showgrid=True,
            gridcolor='#ecf0f1',
            title_font=dict(size=14, color='#34495e')
        ),
        yaxis=dict(
            title='Number of Job Openings',
            showgrid=True,
            gridcolor='#444444',
            title_font=dict(size=14, color='#FFFFFF')
        ),
        hovermode='x unified',
        height=500,
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
        font=dict(color='#FFFFFF'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color='#FFFFFF')
        ),
        margin=dict(t=80, b=60, l=60, r=40)
    )
    
    return fig


def main():
    """Main application function"""
    
    # Header
    st.markdown('<div class="main-header">Tech Skill Tracker - Business Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="subheader-text">Comprehensive Analytics for the Indian Tech Job Market</div>', unsafe_allow_html=True)
    
    # Data source selector (only shown when both live and historical data exist)
    data_source = "auto"
    sources = available_sources()
    if sources["live"] and sources["csv"]:
        source_choice = st.sidebar.radio(
            "Data source",
            ["Live (ingested)", "Historical CSV"],
            help="Live postings come from the scheduled JSearch ingestion. "
                 "Historical CSV is the bundled sample with salary data.",
        )
        data_source = "live" if source_choice.startswith("Live") else "csv"

    # Load and clean data
    with st.spinner("Loading data..."):
        df_raw, files_count = load_job_data("data", source=data_source)
        
        if df_raw.empty:
            st.error("No data found. Please add CSV files to the data folder.")
            st.info("Required columns: Job Title, Tech Skill, Company, Location, Salary (in LPA), Experience Required (in years), Date Posted")
            st.stop()
        
        # Clean data
        df = clean_job_data(df_raw)
        
        # Validate
        is_valid, message = validate_data(df)
        if not is_valid:
            st.error(f"Data validation failed: {message}")
            st.stop()
        
        st.success(f"Data loaded successfully: {len(df)} records from {files_count} source(s)")

        source_info = get_data_source_info()
        if (
            data_source in ("auto", "live")
            and source_info["source"] in ("sqlite", "postgres")
            and source_info["age_hours"] is not None
        ):
            st.caption(
                f"Live store: {source_info['rows']:,} postings · "
                f"last updated {source_info['age_hours']:.1f}h ago · "
                f"source: {source_info['source']}"
            )
    
    # Train ML models (cached) - forecasting only
    with st.spinner("Initializing machine learning models..."):
        st.success("Forecasting models ready")
    
    # Sidebar filters
    st.sidebar.header("Filter Options")
    
    # Date range filter
    min_date = df['Date Posted'].min().date()
    max_date = df['Date Posted'].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Skill filter
    all_skills = sorted(df['Tech Skill'].unique())
    selected_skills = st.sidebar.multiselect(
        "Technology Skills",
        options=all_skills,
        default=all_skills
    )
    
    # Location filter
    all_locations = sorted(df['Location'].unique())
    selected_locations = st.sidebar.multiselect(
        "Job Locations",
        options=all_locations,
        default=all_locations
    )
    
    # Experience filter (live postings may not state experience)
    exp_values = df['Experience Required (in years)'].dropna()
    min_exp = int(exp_values.min()) if not exp_values.empty else 0
    max_exp = int(exp_values.max()) if not exp_values.empty else 10
    if max_exp <= min_exp:
        max_exp = min_exp + 1
    exp_range = st.sidebar.slider(
        "Experience Range (years)",
        min_value=min_exp,
        max_value=max_exp,
        value=(min_exp, max_exp)
    )
    
    # Apply filters
    exp_series = df['Experience Required (in years)'].fillna(min_exp)
    if len(date_range) == 2:
        df_filtered = df[
            (df['Date Posted'].dt.date >= date_range[0]) &
            (df['Date Posted'].dt.date <= date_range[1]) &
            (df['Tech Skill'].isin(selected_skills)) &
            (df['Location'].isin(selected_locations)) &
            (exp_series >= exp_range[0]) &
            (exp_series <= exp_range[1])
        ]
    else:
        df_filtered = df
    
    if df_filtered.empty:
        st.warning("No data matches the selected filters. Please adjust your criteria.")
        st.stop()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Market Overview",
        "Data Visualization",
        "Demand Forecasting",
        "Skill Recommendations",
        "Resume Analysis"
    ])
    
    # TAB 1: MARKET OVERVIEW
    with tab1:
        st.header("Market Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_openings = (
                df_filtered["Job ID"].nunique()
                if "Job ID" in df_filtered.columns
                else len(df_filtered)
            )
            st.metric("Total Job Openings", f"{total_openings:,}")
        with col2:
            st.metric("Unique Technologies", f"{df_filtered['Tech Skill'].nunique():,}")
        with col3:
            st.metric("Companies Hiring", f"{df_filtered['Company'].nunique():,}")
        with col4:
            avg_salary = df_filtered['Salary (in LPA)'].mean()
            st.metric("Average Salary", f"₹{avg_salary:.1f}L" if pd.notna(avg_salary) else "N/A")
        
        st.markdown("---")
        
        # Top insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 In-Demand Skills")
            top_skills = df_filtered['Tech Skill'].value_counts().head(10)
            fig = px.bar(
                x=top_skills.values,
                y=top_skills.index,
                orientation='h',
                labels={'x': 'Number of Openings', 'y': 'Technology'},
                color=top_skills.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                showlegend=False,
                height=450,
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                yaxis={'categoryorder': 'total ascending', 'color': '#FFFFFF'},
                xaxis={'color': '#FFFFFF', 'gridcolor': '#444444'},
                font=dict(size=11, color='#FFFFFF')
            )
            fig.update_traces(marker_line_color='rgb(8,48,107)', marker_line_width=1.5)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with col2:
            st.subheader("Job Distribution by Location")
            location_counts = df_filtered['Location'].value_counts().head(10)
            fig = px.pie(
                values=location_counts.values,
                names=location_counts.index,
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont_size=11,
                marker=dict(line=dict(color='white', width=2))
            )
            fig.update_layout(height=450, plot_bgcolor='#000000', paper_bgcolor='#000000', font=dict(color='#FFFFFF'))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        # Data summary
        st.subheader("Dataset Statistics")
        summary = get_data_summary(df_filtered)
        cols = st.columns(3)
        for idx, (key, value) in enumerate(summary.items()):
            with cols[idx % 3]:
                st.info(f"**{key}:** {value}")
    
    # TAB 2: DATA VISUALIZATION
    with tab2:
        st.header("Interactive Data Visualizations")
        
        viz_tab1, viz_tab2, viz_tab3 = st.tabs([
            "Demand Trends",
            "Salary Distribution",
            "Skill Relationships"
        ])
        
        with viz_tab1:
            st.subheader("Technology Demand Trends Over Time")
            
            # Get top 5 skills
            top_5_skills = df_filtered['Tech Skill'].value_counts().head(5).index.tolist()
            
            # Monthly trends
            df_temp = df_filtered.copy()
            df_temp['Month'] = df_temp['Date Posted'].dt.to_period('M')
            
            trend_data = []
            for skill in top_5_skills:
                skill_df = df_temp[df_temp['Tech Skill'] == skill]
                monthly = skill_df.groupby('Month').size().reset_index(name='Count')
                monthly['Month'] = monthly['Month'].dt.to_timestamp()
                monthly['Skill'] = skill
                trend_data.append(monthly)
            
            if trend_data:
                trend_df = pd.concat(trend_data)
                fig = px.line(
                    trend_df,
                    x='Month',
                    y='Count',
                    color='Skill',
                    markers=True,
                    title="Monthly Job Posting Trends for Top 5 Skills"
                )
                fig.update_layout(
                    height=500,
                    hovermode='x unified',
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    xaxis=dict(showgrid=True, gridcolor='#444444', color='#FFFFFF'),
                    yaxis=dict(showgrid=True, gridcolor='#444444', color='#FFFFFF'),
                    font=dict(size=11, color='#FFFFFF'),
                    legend=dict(font=dict(color='#FFFFFF'))
                )
                fig.update_traces(line=dict(width=3), marker=dict(size=8))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with viz_tab2:
            st.subheader("Salary Distribution Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Salary by skill
                top_10_skills = df_filtered['Tech Skill'].value_counts().head(10).index
                salary_by_skill = df_filtered[df_filtered['Tech Skill'].isin(top_10_skills)]
                
                fig = px.box(
                    salary_by_skill,
                    x='Tech Skill',
                    y='Salary (in LPA)',
                    title="Salary Distribution by Technology",
                    color='Tech Skill',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    xaxis=dict(title_font=dict(size=12, color='#FFFFFF'), color='#FFFFFF', gridcolor='#444444'),
                    yaxis=dict(title_font=dict(size=12, color='#FFFFFF'), color='#FFFFFF', gridcolor='#444444'),
                    font=dict(color='#FFFFFF')
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            with col2:
                # Salary by experience
                fig = px.scatter(
                    df_filtered,
                    x='Experience Required (in years)',
                    y='Salary (in LPA)',
                    color='Location',
                    title="Salary vs Experience Correlation",
                    opacity=0.7,
                    size_max=8
                )
                fig.update_layout(
                    height=400,
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    xaxis=dict(title_font=dict(size=12, color='#FFFFFF'), color='#FFFFFF', gridcolor='#444444'),
                    yaxis=dict(title_font=dict(size=12, color='#FFFFFF'), color='#FFFFFF', gridcolor='#444444'),
                    font=dict(color='#FFFFFF'),
                    legend=dict(font=dict(color='#FFFFFF'))
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with viz_tab3:
            st.subheader("Skill Co-occurrence Analysis")
            st.write("Technologies that frequently appear together in job requirements")
            
            skill_pairs = get_skill_pairs(df_filtered, min_cooccurrence=2)
            
            if skill_pairs:
                pairs_df = pd.DataFrame([
                    {'Skill Combination': f"{pair[0]} + {pair[1]}", 'Frequency': count}
                    for pair, count in skill_pairs[:15]
                ])
                
                fig = px.bar(
                    pairs_df,
                    x='Frequency',
                    y='Skill Combination',
                    orientation='h',
                    title="Most Common Skill Combinations in Job Postings",
                    color='Frequency',
                    color_continuous_scale='Viridis'
                )
                fig.update_layout(
                    height=500,
                    yaxis={'categoryorder': 'total ascending', 'color': '#FFFFFF'},
                    xaxis={'color': '#FFFFFF', 'gridcolor': '#444444'},
                    plot_bgcolor='#000000',
                    paper_bgcolor='#000000',
                    font=dict(size=11, color='#FFFFFF')
                )
                fig.update_traces(marker_line_color='rgb(8,48,107)', marker_line_width=1)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Insufficient data to display skill co-occurrences with current filters.")
    
    # TAB 3: DEMAND FORECASTING
    with tab3:
        st.header("Demand Forecasting")
        st.write("Predict future market demand for technology skills using time-series analysis")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_skill_forecast = st.selectbox(
                "Select Technology for Forecast",
                options=sorted(df_filtered['Tech Skill'].unique()),
                key="forecast_skill"
            )
        
        with col2:
            months_ahead = st.slider("Forecast Period (months)", 3, 12, 6)
        
        with col3:
            forecast_engine_label = st.selectbox(
                "Forecasting Engine",
                options=[
                    "Auto (best by backtest MAPE)",
                    "Gradient Boosting",
                    "SARIMAX",
                    "Prophet",
                    "Croston (intermittent)",
                    "Exponential Smoothing",
                    "Linear Regression"
                ],
                key="forecast_engine"
            )
        
        engine_map = {
            "Auto (best by backtest MAPE)": "auto",
            "Gradient Boosting": "gradient_boosting",
            "SARIMAX": "sarimax",
            "Prophet": "prophet",
            "Croston (intermittent)": "croston",
            "Exponential Smoothing": "exponential_smoothing",
            "Linear Regression": "linear"
        }
        
        if st.button("Generate Forecast", type="primary"):
            with st.spinner("Running predictive model..."):
                forecast_df, status = forecast_skill_demand(
                    df,
                    selected_skill_forecast,
                    months_ahead,
                    engine_map[forecast_engine_label]
                )
                
                if forecast_df is not None:
                    st.caption(f"Engine used: {forecast_df.attrs.get('engine', 'Unknown')}")
                    
                    # Show professional chart
                    fig = create_professional_forecast_chart(forecast_df, selected_skill_forecast)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    # Show insights
                    insights = get_forecast_insights(forecast_df, selected_skill_forecast)
                    if insights:
                        st.subheader("Forecast Insights")
                        for insight in insights:
                            # Remove emojis from insights
                            clean_insight = insight.replace('📈', '').replace('📉', '').replace('📊', '').replace('💼', '')
                            st.markdown(clean_insight)
                else:
                    st.warning(f"Unable to generate forecast: {status}")
        
        # Top skills summary
        st.markdown("---")
        st.subheader("Current Market Leaders")
        
        top_skills_current = df_filtered['Tech Skill'].value_counts().head(5)
        cols = st.columns(5)
        for idx, (skill, count) in enumerate(top_skills_current.items()):
            with cols[idx]:
                st.metric(skill, f"{count} openings")
    
    # TAB 4: SKILL RECOMMENDATIONS
    with tab4:
        st.header("Skill Recommendations")
        
        rec_tab1, rec_tab2, rec_tab3 = st.tabs([
            "Complementary Skills",
            "Job Role Analysis",
            "Learning Roadmap"
        ])
        
        with rec_tab1:
            st.subheader("Find Complementary Skills")
            st.write("Discover technologies that commonly pair with your current expertise")
            
            current_skill = st.selectbox(
                "Select Your Current Skill",
                options=sorted(df['Tech Skill'].unique()),
                key="current_skill"
            )
            
            if st.button("Get Recommendations", key="rec_btn1"):
                recs, status = recommend_skills(df, current_skill, top_n=10)
                
                if recs:
                    st.success(f"Recommended complementary skills for {current_skill}:")
                    
                    for idx, rec in enumerate(recs, 1):
                        with st.expander(f"{idx}. {rec['skill']} ({rec['co_occurrence_score']} co-occurrences)"):
                            col1, col2 = st.columns(2)
                            with col1:
                                avg = rec.get('avg_salary')
                                st.metric("Average Salary", f"₹{avg:.1f}L" if pd.notna(avg) else "N/A")
                            with col2:
                                st.metric("Job Openings", f"{rec['job_count']}")
                else:
                    st.warning(status)
        
        with rec_tab2:
            st.subheader("Job Role Skill Requirements")
            st.write("Analyze the most common skills required for specific job roles")
            
            dream_job = st.text_input(
                "Enter Job Role",
                placeholder="e.g., Data Scientist, Full Stack Developer",
                key="dream_job"
            )
            
            if dream_job and st.button("Analyze Skills", key="rec_btn2"):
                recs, status = recommend_for_job_role(df, dream_job, top_n=10)
                
                if recs:
                    st.success(f"Most common skills for {dream_job} positions:")
                    
                    # Create dataframe for visualization
                    rec_df = pd.DataFrame(recs)
                    
                    fig = px.bar(
                        rec_df,
                        x='frequency',
                        y='skill',
                        orientation='h',
                        title=f"Skill Requirements for {dream_job}",
                        labels={'frequency': 'Number of Jobs', 'skill': 'Technology'},
                        color='avg_salary',
                        color_continuous_scale='Viridis',
                        hover_data=['percentage']
                    )
                    fig.update_layout(
                        height=400,
                        yaxis={'categoryorder': 'total ascending', 'color': '#FFFFFF'},
                        xaxis={'color': '#FFFFFF', 'gridcolor': '#444444'},
                        plot_bgcolor='#000000',
                        paper_bgcolor='#000000',
                        font=dict(color='#FFFFFF')
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    # Show detailed list
                    for idx, rec in enumerate(recs, 1):
                        st.write(f"{idx}. **{rec['skill']}** - {rec['frequency']} jobs ({rec['percentage']:.1f}%), Average Salary: {'₹' + format(rec['avg_salary'], '.1f') + 'L' if pd.notna(rec.get('avg_salary')) else 'N/A'}")
                else:
                    st.warning(status)
        
        with rec_tab3:
            st.subheader("Personalized Learning Roadmap")
            st.write("Generate a customized skill development path based on your current abilities and career goals")
            
            col1, col2 = st.columns(2)
            
            with col1:
                current_skills_input = st.text_input(
                    "Current Skills (comma-separated)",
                    placeholder="Python, SQL, Pandas",
                    key="current_skills"
                )
            
            with col2:
                target_role = st.text_input(
                    "Target Job Role",
                    placeholder="Data Scientist",
                    key="target_role"
                )
            
            if current_skills_input and target_role and st.button("Generate Learning Path", key="rec_btn3"):
                current_skills_list = [s.strip() for s in current_skills_input.split(",")]
                
                learning_path, status = get_learning_path(df, current_skills_list, target_role)
                
                if learning_path:
                    st.success(f"Recommended learning path to become {target_role}:")
                    
                    # Show priority skills to develop
                    st.write("### Priority Skills to Develop:")
                    missing_skills = []
                    for idx, skill in enumerate(learning_path[:10], 1):
                        st.write(f"{idx}. **{skill['skill']}** - {skill['frequency']} job openings, {'₹' + format(skill['avg_salary'], '.1f') + 'L average salary' if pd.notna(skill.get('avg_salary')) else 'N/A average salary'}")
                        missing_skills.append(skill['skill'])
                    
                    # Add learning resources section
                    st.markdown("---")
                    st.markdown("## Learning Resources Panel")
                    st.info("Auto-suggested courses, tutorials, and videos to help you acquire these skills")
                    
                    # Generate learning path with resources for all missing skills
                    get_learning_path_with_resources(missing_skills[:5])  # Show resources for top 5 skills
                    
                else:
                    st.warning(status)
    
    # TAB 5: RESUME SKILL-GAP
    with tab5:
        st.header("Resume Skill-Gap Analysis")
        st.write("Upload your resume (PDF or DOCX) to see how well it matches the live job market and which skills to learn next.")

        uploaded = st.file_uploader(
            "Choose a resume",
            type=["pdf", "docx"],
            key="resume_uploader",
        )

        if uploaded is not None:
            with st.spinner("Extracting and analysing your resume..."):
                try:
                    text = extract_text(uploaded, uploaded.name)
                except Exception as exc:
                    st.error(f"Could not read the file: {exc}")
                    text = ""

            if text.strip():
                st.success(f"Extracted {len(text.split())} words from {uploaded.name}")

                # Quick facts
                experience = None
                education = []
                try:
                    from modules.resume_analyzer import extract_experience_years, extract_education

                    experience = extract_experience_years(text)
                    education = extract_education(text)
                except Exception:
                    pass

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Experience", f"{experience} yrs" if experience is not None else "N/A")
                with col2:
                    st.metric("Education", ", ".join(education) if education else "N/A")
                with col3:
                    st.metric("Words extracted", len(text.split()))

                with st.spinner("Scoring against live postings..."):
                    analysis = analyze_resume(text, df)

                # Fix the detected-skills metric now that we have the analysis
                # (rerun-safe: Streamlit re-executes top-down, so this is fine)

                st.subheader("Match with the live market")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Match %", f"{analysis['match_percentage']}%")
                with col2:
                    st.metric("Weighted match", f"{analysis['weighted_match_percentage']}%")
                with col3:
                    st.metric("Skills you have", len(analysis["resume_skills"]))
                with col4:
                    st.metric("In-demand skills", analysis["total_demand_skills"])

                st.caption(
                    f"Based on {analysis['total_postings']} live postings covering "
                    f"{analysis['total_demand_skills']} distinct skills."
                )

                if analysis["resume_skills"]:
                    st.write("**Skills detected in your resume:**")
                    st.write(", ".join(analysis["resume_skills"]))

                if analysis["matched_skills"]:
                    st.success("You already cover: " + ", ".join(analysis["matched_skills"]))

                missing = analysis["missing_skills"]
                if missing:
                    st.subheader(f"Top missing skills ({len(missing)})")
                    top_missing = missing[:15]
                    miss_df = pd.DataFrame(
                        [
                            {
                                "Skill": m["skill"],
                                "Demand (postings)": m["demand"],
                                "% of postings": m["percentage"],
                                "Avg salary (LPA)": m["avg_salary"] if m["avg_salary"] is not None else "N/A",
                            }
                            for m in top_missing
                        ]
                    )
                    st.dataframe(miss_df, use_container_width=True, hide_index=True)

                    # Bar chart of top missing by demand
                    chart_df = pd.DataFrame(
                        [{"Skill": m["skill"], "Demand": m["demand"]} for m in top_missing[:10]]
                    )
                    if not chart_df.empty:
                        fig = px.bar(
                            chart_df,
                            x="Demand",
                            y="Skill",
                            orientation="h",
                            title="Most in-demand skills missing from your resume",
                            color="Demand",
                            color_continuous_scale="Reds",
                        )
                        fig.update_layout(
                            height=400,
                            yaxis={"categoryorder": "total ascending", "color": "#FFFFFF"},
                            xaxis={"color": "#FFFFFF", "gridcolor": "#444444"},
                            plot_bgcolor="#000000",
                            paper_bgcolor="#000000",
                            font=dict(color="#FFFFFF"),
                            showlegend=False,
                        )
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                    # Learning resources for the top 5 missing skills
                    st.markdown("---")
                    st.subheader("Where to learn the missing skills")
                    for m in top_missing[:5]:
                        with st.expander(f"{m['skill']} — {m['demand']} postings"):
                            resources = m["resources"]
                            cols = st.columns(3)
                            for idx, (name, info) in enumerate(list(resources.items())[:6]):
                                with cols[idx % 3]:
                                    st.markdown(f"[{info['icon']} {name}]({info['url']})")
                                    st.caption(info["description"])

                    # Persist the report
                    try:
                        from modules import store as job_store

                        if job_store.store_available():
                            rid = save_report(uploaded.name, analysis)
                            if rid:
                                st.caption(f"Report saved (id: {rid[:8]}…)")
                    except Exception:
                        pass
                else:
                    st.success("You already cover every in-demand skill in the live market.")
            else:
                st.warning("No readable text found in the file. Try a text-based PDF or DOCX.")

    # Professional Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #7f8c8d; padding: 2rem 0; font-family: Arial, sans-serif;'>
        <p style='font-size: 1.1rem; font-weight: 600; color: #2c3e50; margin-bottom: 0.5rem;'>
            Tech Skill Tracker - Business Intelligence
        </p>
        <p style='font-size: 0.9rem; margin: 0.3rem 0;'>
            Team Members: Om Aravindhashan S (23MID0222) | Raghul (23MID0322)
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
