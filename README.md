# 📊 Tech Skill Tracker - BI Dashboard

A comprehensive Business Intelligence dashboard for analyzing tech skill demand trends in the Indian job market, powered by Machine Learning.

## 🌟 Features

### 📈 Data Analytics
- **Market Overview**: Real-time metrics on job openings, skills, companies, and salary trends
- **Interactive Visualizations**: Dynamic charts and graphs using Plotly
- **Skill Demand Trends**: Track how demand for different tech skills evolves over time
- **Location Analysis**: Compare job markets across major Indian cities

### 🤖 Machine Learning Models

1. **Demand Forecasting (Prophet)**
   - Time-series forecasting for skill demand
   - 3-12 month predictions with confidence intervals
   - Trend analysis and seasonality detection

2. **Salary Prediction (Random Forest)**
   - Predict salaries based on skill, location, and experience
   - Market comparison and salary range insights
   - Feature importance analysis

3. **Skill Recommendations (Co-occurrence Analysis)**
   - Find complementary skills that appear together in job postings
   - Identify required skills for target job roles
   - Generate personalized learning paths

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the project**
   ```bash
   cd tech-skill-tracker
   ```

2. **Create a virtual environment** (Recommended)
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install streamlit pandas numpy scikit-learn prophet joblib plotly
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**
   - The app will automatically open at `http://localhost:8501`
   - If not, manually navigate to the displayed URL

## 📁 Project Structure

```
tech-skill-tracker/
├── app.py                      # Main Streamlit application
├── data/                       # Dataset folder
│   └── job_listings.csv        # Job market data
├── modules/                    # Modular components
│   ├── __init__.py
│   ├── data_loader.py          # Data loading utilities
│   ├── data_cleaner.py         # Data cleaning and validation
│   ├── ml_forecast.py          # Forecasting with Prophet
│   ├── salary_predictor.py     # Salary prediction ML model
│   └── recommendation_engine.py # Skill recommendation system
├── models/                     # Trained ML models (auto-generated)
├── logs/                       # Application logs
└── README.md                   # This file
```

## 📊 Data Format

The application expects CSV files in the `/data` folder with the following columns:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| Job Title | String | Position name | "Data Scientist" |
| Tech Skill | String | Required technology | "Python" |
| Company | String | Hiring company | "Google" |
| Location | String | Job location | "Bengaluru" |
| Salary (in LPA) | Float | Annual salary in lakhs | 15.5 |
| Experience Required (in years) | Integer | Years of experience | 3 |
| Date Posted | Date | Posting date | "2024-01-15" |

### Adding Your Own Data

1. Place CSV files in the `/data` folder
2. Ensure columns match the required format
3. Restart the application
4. The app will automatically load and clean the data

## 🎯 How to Use

### 1. Overview Tab
- View key market metrics (total jobs, skills, companies, average salary)
- See top in-demand skills and location distributions
- Get a quick summary of the dataset

### 2. Visualization Tab
- **Skill Trends**: Track demand changes for top skills over time
- **Salary Analysis**: Compare salary distributions across skills
- **Skill Co-occurrence**: Discover which skills frequently appear together

### 3. Forecast Tab
- Select a skill to forecast
- Choose prediction timeframe (3-12 months)
- View predicted demand with confidence intervals
- Get growth/decline insights

### 4. Salary Insights Tab
- **Salary Predictor**: Enter skill, location, and experience to get salary estimate
- View market salary ranges (min, median, max)
- Get insights on high-paying vs. average skills
- See salary distributions for specific skills

### 5. Recommendations Tab
- **Complementary Skills**: Find skills that pair well with your current skill
- **Job Role Skills**: Discover required skills for your dream job
- **Learning Path**: Get a personalized roadmap from current skills to target role

## 🔧 How It Works

### Data Pipeline

1. **Loading**: CSV files are loaded from `/data` folder using pandas
2. **Cleaning**: Data is validated, duplicates removed, formats standardized
3. **Caching**: Streamlit caches cleaned data for fast performance
4. **Filtering**: Users can filter by date, skills, location, and experience

### Machine Learning Models

#### 1. Demand Forecasting (Prophet)
```python
from modules.ml_forecast import forecast_skill_demand

# Forecast demand for Python over next 6 months
forecast_df, status = forecast_skill_demand(df, "Python", months_ahead=6)
```

- Uses Facebook's Prophet library for time-series forecasting
- Handles trend, seasonality, and holiday effects
- Falls back to linear regression if Prophet unavailable
- Provides confidence intervals for predictions

#### 2. Salary Prediction (Random Forest)
```python
from modules.salary_predictor import train_salary_model, predict_salary

# Train model
model, le_skill, le_location, status = train_salary_model(df)

# Predict salary
salary, status = predict_salary(model, le_skill, le_location, 
                                 "Python", "Bengaluru", 3)
```

- Random Forest Regressor with 100 estimators
- Features: Encoded skill, location, and experience
- Label encoding for categorical variables
- Handles unseen categories gracefully

#### 3. Skill Recommendations (Co-occurrence)
```python
from modules.recommendation_engine import recommend_skills

# Get complementary skills
recommendations, status = recommend_skills(df, "Python", top_n=5)
```

- Builds co-occurrence matrix from company hiring patterns
- Analyzes which skills appear together in job postings
- Scores skills based on frequency of co-occurrence
- Provides salary and job count for each recommendation

### Performance Optimizations

- **@st.cache_data**: Caches loaded and cleaned data
- **@st.cache_resource**: Caches trained ML models
- **Lazy Loading**: Models trained only when needed
- **Efficient Filtering**: Uses pandas vectorized operations

## 🛠️ Troubleshooting

### Common Issues

**Problem**: "No data found! Please add CSV files to the `/data` folder"
- **Solution**: Ensure CSV files exist in the `/data` directory with correct column names

**Problem**: "Prophet not available, using linear regression"
- **Solution**: Install Prophet: `pip install prophet`

**Problem**: "Model not trained successfully"
- **Solution**: Ensure dataset has at least 10 records with valid salary and experience data

**Problem**: Charts not displaying
- **Solution**: Update Plotly: `pip install --upgrade plotly`

**Problem**: Slow performance
- **Solution**: Clear Streamlit cache using "Clear Cache" in settings menu (⋮)

## 📈 Extending the Project

### Adding New Features

1. **Custom Visualizations**: Add charts in `app.py` under respective tabs
2. **New ML Models**: Create module in `/modules` folder
3. **Additional Data Sources**: Add CSV files to `/data` folder
4. **Export Functionality**: Use Streamlit's download buttons

### Example: Adding a New Tab

```python
# In app.py
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Overview", "📊 Visualization", "🔮 Forecast", 
    "💰 Salary Insights", "🎯 Recommendations", "📄 Your New Tab"
])

with tab6:
    st.header("Your New Feature")
    # Add your code here
```

## 🔒 Data Privacy

- All data processing happens locally on your machine
- No data is sent to external servers
- ML models are trained and stored locally in `/models` folder

## 📝 Technical Stack

- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **ML Libraries**: Scikit-learn, Prophet
- **Visualization**: Plotly
- **Model Persistence**: Joblib

## 🤝 Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available for educational and commercial use.

## 💡 Tips for Best Results

1. **Data Quality**: Ensure clean, complete data for accurate predictions
2. **Regular Updates**: Update dataset regularly to capture market trends
3. **Filtering**: Use filters to focus on specific segments
4. **Combinations**: Explore skill co-occurrences for career planning
5. **Context**: Consider predictions as guidance, not absolute truth

## 🆘 Support

For issues, questions, or suggestions:
- Check the troubleshooting section above
- Review the data format requirements
- Ensure all dependencies are properly installed

---

**Built with ❤️ using Streamlit and Machine Learning**
