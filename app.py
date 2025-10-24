import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Import custom modules
from modules.data_loader import load_job_data
from modules.data_cleaner import clean_job_data, validate_data, get_data_summary
from modules.ml_forecast import forecast_skill_demand, create_forecast_chart, get_forecast_insights
from modules.salary_predictor import train_salary_model, predict_salary, get_salary_distribution, get_salary_insights
from modules.recommendation_engine import recommend_skills, recommend_for_job_role, get_skill_pairs, get_learning_path

# Page configuration
st.set_page_config(
    page_title="Tech Skill Tracker - BI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application function"""
    
    # Header
    st.markdown('<div class="main-header">📊 Tech Skill Tracker - BI Dashboard</div>', unsafe_allow_html=True)
    st.markdown("### Data-Driven Insights for the Indian Tech Job Market")
    st.markdown("---")
    
    # Load and clean data
    with st.spinner("Loading data..."):
        df_raw, files_count = load_job_data("data")
        
        if df_raw.empty:
            st.error("❌ No data found! Please add CSV files to the `/data` folder.")
            st.info("**Required columns:** Job Title, Tech Skill, Company, Location, Salary (in LPA), Experience Required (in years), Date Posted")
            st.stop()
        
        # Clean data
        df = clean_job_data(df_raw)
        
        # Validate
        is_valid, message = validate_data(df)
        if not is_valid:
            st.error(f"❌ Data validation failed: {message}")
            st.stop()
        
        st.success(f"✅ Loaded and cleaned data from {files_count} file(s) - {len(df)} records ready for analysis")
    
    # Train ML models (cached)
    with st.spinner("Training ML models..."):
        salary_model, le_skill, le_location, model_status = train_salary_model(df)
        if "successfully" in model_status:
            st.success(f"🤖 {model_status}")
    
    # Sidebar filters
    st.sidebar.header("🎛️ Filters")
    
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
        "Tech Skills",
        options=all_skills,
        default=all_skills
    )
    
    # Location filter
    all_locations = sorted(df['Location'].unique())
    selected_locations = st.sidebar.multiselect(
        "Locations",
        options=all_locations,
        default=all_locations
    )
    
    # Experience filter
    min_exp = int(df['Experience Required (in years)'].min())
    max_exp = int(df['Experience Required (in years)'].max())
    exp_range = st.sidebar.slider(
        "Experience (years)",
        min_value=min_exp,
        max_value=max_exp,
        value=(min_exp, max_exp)
    )
    
    # Apply filters
    if len(date_range) == 2:
        df_filtered = df[
            (df['Date Posted'].dt.date >= date_range[0]) &
            (df['Date Posted'].dt.date <= date_range[1]) &
            (df['Tech Skill'].isin(selected_skills)) &
            (df['Location'].isin(selected_locations)) &
            (df['Experience Required (in years)'] >= exp_range[0]) &
            (df['Experience Required (in years)'] <= exp_range[1])
        ]
    else:
        df_filtered = df
    
    if df_filtered.empty:
        st.warning("⚠️ No data matches your filters. Please adjust your selection.")
        st.stop()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview",
        "📊 Visualization",
        "🔮 Forecast",
        "💰 Salary Insights",
        "🎯 Recommendations"
    ])
    
    # TAB 1: OVERVIEW
    with tab1:
        st.header("Market Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Jobs", f"{len(df_filtered):,}")
        with col2:
            st.metric("Unique Skills", f"{df_filtered['Tech Skill'].nunique():,}")
        with col3:
            st.metric("Companies", f"{df_filtered['Company'].nunique():,}")
        with col4:
            st.metric("Avg Salary", f"₹{df_filtered['Salary (in LPA)'].mean():.1f}L")
        
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
                labels={'x': 'Job Count', 'y': 'Skill'},
                color=top_skills.values,
                color_continuous_scale='blues'
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Job Distribution by Location")
            location_counts = df_filtered['Location'].value_counts().head(10)
            fig = px.pie(
                values=location_counts.values,
                names=location_counts.index,
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Data summary
        st.subheader("Dataset Summary")
        summary = get_data_summary(df_filtered)
        cols = st.columns(3)
        for idx, (key, value) in enumerate(summary.items()):
            with cols[idx % 3]:
                st.info(f"**{key}:** {value}")
    
    # TAB 2: VISUALIZATION
    with tab2:
        st.header("Interactive Visualizations")
        
        viz_tab1, viz_tab2, viz_tab3 = st.tabs([
            "Skill Trends",
            "Salary Analysis",
            "Skill Co-occurrence"
        ])
        
        with viz_tab1:
            st.subheader("Skill Demand Trends Over Time")
            
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
                    title="Top 5 Skills - Monthly Demand Trends"
                )
                fig.update_layout(height=500, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
        
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
                    title="Salary Distribution by Top 10 Skills",
                    color='Tech Skill'
                )
                fig.update_layout(showlegend=False, height=400)
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Salary by experience
                fig = px.scatter(
                    df_filtered,
                    x='Experience Required (in years)',
                    y='Salary (in LPA)',
                    color='Tech Skill',
                    title="Salary vs Experience",
                    opacity=0.6,
                    size_max=10
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with viz_tab3:
            st.subheader("Skill Co-occurrence Analysis")
            st.write("Skills that frequently appear together in job postings")
            
            skill_pairs = get_skill_pairs(df_filtered, min_cooccurrence=2)
            
            if skill_pairs:
                pairs_df = pd.DataFrame([
                    {'Skill Pair': f"{pair[0]} + {pair[1]}", 'Co-occurrences': count}
                    for pair, count in skill_pairs[:15]
                ])
                
                fig = px.bar(
                    pairs_df,
                    x='Co-occurrences',
                    y='Skill Pair',
                    orientation='h',
                    title="Top 15 Skill Combinations",
                    color='Co-occurrences',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data to show skill co-occurrences")
    
    # TAB 3: FORECAST
    with tab3:
        st.header("Demand Forecasting")
        st.write("Predict future demand for tech skills using machine learning")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_skill_forecast = st.selectbox(
                "Select Skill to Forecast",
                options=sorted(df_filtered['Tech Skill'].unique()),
                key="forecast_skill"
            )
        
        with col2:
            months_ahead = st.slider("Months to Forecast", 3, 12, 6)
        
        if st.button("Generate Forecast", type="primary"):
            with st.spinner("Running forecast model..."):
                forecast_df, status = forecast_skill_demand(df, selected_skill_forecast, months_ahead)
                
                if forecast_df is not None:
                    # Show chart
                    fig = create_forecast_chart(forecast_df, selected_skill_forecast)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show insights
                    insights = get_forecast_insights(forecast_df, selected_skill_forecast)
                    if insights:
                        st.subheader("Forecast Insights")
                        for insight in insights:
                            st.markdown(insight)
                else:
                    st.warning(f"⚠️ {status}")
        
        # Top growing skills
        st.markdown("---")
        st.subheader("Quick Insights: Most In-Demand Skills")
        
        top_skills_current = df_filtered['Tech Skill'].value_counts().head(5)
        cols = st.columns(5)
        for idx, (skill, count) in enumerate(top_skills_current.items()):
            with cols[idx]:
                st.metric(skill, f"{count} jobs")
    
    # TAB 4: SALARY INSIGHTS
    with tab4:
        st.header("Salary Prediction & Insights")
        
        st.subheader("🔮 Salary Predictor")
        st.write("Estimate salary based on skill, location, and experience")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            pred_skill = st.selectbox(
                "Tech Skill",
                options=sorted(df['Tech Skill'].unique()),
                key="pred_skill"
            )
        
        with col2:
            pred_location = st.selectbox(
                "Location",
                options=sorted(df['Location'].unique()),
                key="pred_location"
            )
        
        with col3:
            pred_experience = st.number_input(
                "Experience (years)",
                min_value=0,
                max_value=30,
                value=3,
                key="pred_exp"
            )
        
        if st.button("Predict Salary", type="primary"):
            if salary_model:
                predicted_salary, status = predict_salary(
                    salary_model, le_skill, le_location,
                    pred_skill, pred_location, pred_experience
                )
                
                if predicted_salary:
                    st.success(f"### Predicted Salary: ₹{predicted_salary:.2f} LPA")
                    
                    # Show market comparison
                    dist = get_salary_distribution(df, pred_skill, pred_location)
                    if dist:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Market Min", f"₹{dist['min']:.1f}L")
                        with col2:
                            st.metric("Market Median", f"₹{dist['median']:.1f}L")
                        with col3:
                            st.metric("Market Max", f"₹{dist['max']:.1f}L")
                else:
                    st.error(f"❌ {status}")
            else:
                st.error("Model not available")
        
        # Salary insights
        st.markdown("---")
        st.subheader("💡 Salary Insights by Skill")
        
        insight_skill = st.selectbox(
            "Select Skill for Insights",
            options=sorted(df['Tech Skill'].unique()),
            key="insight_skill"
        )
        
        insights = get_salary_insights(df, insight_skill)
        for insight in insights:
            st.markdown(insight)
        
        # Salary distribution chart
        skill_data = df[df['Tech Skill'] == insight_skill]
        if len(skill_data) > 0:
            fig = px.histogram(
                skill_data,
                x='Salary (in LPA)',
                nbins=20,
                title=f"Salary Distribution for {insight_skill}",
                color_discrete_sequence=['#636EFA']
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 5: RECOMMENDATIONS
    with tab5:
        st.header("Skill Recommendations")
        
        rec_tab1, rec_tab2, rec_tab3 = st.tabs([
            "Complementary Skills",
            "Skills for Job Role",
            "Learning Path"
        ])
        
        with rec_tab1:
            st.subheader("🔗 Find Complementary Skills")
            st.write("Discover skills that often appear together in job postings")
            
            current_skill = st.selectbox(
                "Your Current Skill",
                options=sorted(df['Tech Skill'].unique()),
                key="current_skill"
            )
            
            if st.button("Get Recommendations", key="rec_btn1"):
                recs, status = recommend_skills(df, current_skill, top_n=10)
                
                if recs:
                    st.success(f"✅ Top complementary skills for **{current_skill}**:")
                    
                    for idx, rec in enumerate(recs, 1):
                        with st.expander(f"{idx}. {rec['skill']} - {rec['co_occurrence_score']} co-occurrences"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Average Salary", f"₹{rec['avg_salary']:.1f}L")
                            with col2:
                                st.metric("Job Openings", f"{rec['job_count']}")
                else:
                    st.warning(status)
        
        with rec_tab2:
            st.subheader("🎯 Skills Required for Job Role")
            st.write("Find out which skills are most common for your dream job")
            
            dream_job = st.text_input(
                "Enter Job Role",
                placeholder="e.g., Data Scientist, Full Stack Developer",
                key="dream_job"
            )
            
            if dream_job and st.button("Find Skills", key="rec_btn2"):
                recs, status = recommend_for_job_role(df, dream_job, top_n=10)
                
                if recs:
                    st.success(f"✅ Top skills for **{dream_job}**:")
                    
                    # Create dataframe for visualization
                    rec_df = pd.DataFrame(recs)
                    
                    fig = px.bar(
                        rec_df,
                        x='frequency',
                        y='skill',
                        orientation='h',
                        title=f"Most Common Skills for {dream_job}",
                        labels={'frequency': 'Number of Jobs', 'skill': 'Skill'},
                        color='avg_salary',
                        color_continuous_scale='viridis',
                        hover_data=['percentage']
                    )
                    fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show detailed list
                    for idx, rec in enumerate(recs, 1):
                        st.write(f"{idx}. **{rec['skill']}** - {rec['frequency']} jobs ({rec['percentage']:.1f}%), Avg Salary: ₹{rec['avg_salary']:.1f}L")
                else:
                    st.warning(status)
        
        with rec_tab3:
            st.subheader("🛤️ Personalized Learning Path")
            st.write("Get a customized skill roadmap from your current skills to your dream job")
            
            col1, col2 = st.columns(2)
            
            with col1:
                current_skills_input = st.text_input(
                    "Your Current Skills (comma-separated)",
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
                    st.success(f"✅ Learning path to become a **{target_role}**:")
                    
                    st.write("### Skills You Should Learn:")
                    for idx, skill in enumerate(learning_path[:10], 1):
                        st.write(f"{idx}. **{skill['skill']}** - {skill['frequency']} jobs, ₹{skill['avg_salary']:.1f}L avg salary")
                else:
                    st.warning(status)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <p><strong>Tech Skill Tracker - BI Dashboard for Indian Tech Market</strong></p>
        <p>Built with Streamlit • Powered by Machine Learning</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
