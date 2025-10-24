# Tech Skill Tracker - Business Intelligence Dashboard

## Overview

Tech Skill Tracker is a professional Business Intelligence dashboard for analyzing tech skill demand trends in the Indian job market. The application combines data analytics with machine learning to provide actionable insights on skill demand, salary predictions, and career recommendations. Built with Streamlit, it offers a clean, formal interface for exploring job market data through visualizations, forecasting models, and intelligent recommendation systems.

The system processes job listing data to deliver:
- Real-time market analytics on skills, salaries, and geographic trends
- 12-month demand forecasting using time-series analysis (Prophet)
- Salary prediction based on skills, location, and experience (Random Forest)
- Skill recommendation engine for career development
- Professional, emoji-free formal presentation

## User Preferences

- Preferred communication style: Simple, everyday language
- Interface style: Formal, professional, no emojis
- Graph quality: Clean, dynamic, easy to understand
- Salary predictions: Simple statements based on record analysis

## System Architecture

### Application Framework
**Streamlit Web Application**: Single-page application with tab-based navigation for maximum real estate utilization and clean user experience. All emojis removed for professional appearance.

**Modular Design Pattern**: Core functionality separated into distinct modules:
- `data_loader.py` - CSV file ingestion and validation
- `data_cleaner.py` - Data preprocessing and standardization
- `ml_forecast.py` - Time-series forecasting with Prophet
- `salary_predictor.py` - Random Forest salary prediction
- `recommendation_engine.py` - Co-occurrence analysis for skill recommendations

### Data Pipeline Architecture

**Fixed Dataset Approach**: Application loads pre-stored CSV files from `/data/` directory for consistency and reliability. The data loader scans for all CSV files and combines them into a unified dataset.

**Caching Strategy**: Extensive use of `@st.cache_data` and `@st.cache_resource` decorators to prevent redundant computation. Data loading, cleaning, and model training operations are cached for improved performance.

**Data Validation**: System validates required columns and performs comprehensive cleaning:
- Removes duplicates and null values
- Converts dates to datetime objects
- Validates salary ranges (0-200 LPA) and experience ranges (0-50 years)
- Standardizes text formatting and location names

### Machine Learning Models

**Prophet-based Forecasting**: Facebook Prophet for time-series forecasting with trend and seasonality detection. Falls back to linear regression if Prophet unavailable. Improved visualization with professional, clean charts.

**Random Forest Salary Predictor**: Random Forest Regressor (100 estimators, max depth 10) trained on historical salary data with encoded tech skill, location, and experience. Provides simple, user-friendly predictions with record count context.

**Co-occurrence Recommendation Engine**: Analyzes which skills frequently appear together in company job postings. Lightweight approach for computational efficiency while providing valuable skill pairing insights.

### Visualization Layer

**Plotly Integration**: All charts use Plotly with professional styling:
- Clean white backgrounds
- Consistent color schemes
- Disabled mode bars for cleaner appearance
- Improved hover templates
- Better grid lines and spacing
- Optimized for performance and clarity

**Tab-based UI**: Five main tabs - Market Overview, Data Visualization, Demand Forecasting, Salary Analysis, Skill Recommendations

### Performance Optimizations

- Caching of data and ML models
- Efficient pandas operations
- Lazy loading of models
- Disabled unnecessary chart controls
- Optimized graph rendering

## External Dependencies

### Core Data Stack
- **Pandas**: Data manipulation
- **NumPy**: Numerical operations
- **Streamlit**: Web framework

### Visualization
- **Plotly**: Interactive charting with professional styling

### Machine Learning
- **Prophet** (optional): Time-series forecasting
- **scikit-learn**: RandomForestRegressor, LabelEncoder, train_test_split
- **joblib**: Model serialization

## Team

**Developers**: 
- Om Aravindhashan S (23MID0222)
- Raghul (23MID0322)

## Recent Updates (October 2024)

1. **Removed all emojis** - Professional formal interface throughout
2. **Improved graph performance** - Cleaner, more dynamic visualizations
3. **Simplified salary prediction** - Clear statements with record count context
4. **Enhanced forecast charts** - Professional styling with better clarity
5. **Updated footer** - Added team member information
