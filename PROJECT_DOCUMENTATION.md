# Tech Skill Tracker - Complete Project Documentation

## 📋 Project Overview

Tech Skill Tracker is a comprehensive Business Intelligence dashboard for analyzing tech skill demand trends in the Indian job market. It combines data analytics with machine learning to provide actionable insights for career planning and market analysis.

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Web Interface                   │
│  (5 Tabs: Overview | Visualization | Forecast | Salary | Rec)│
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │        app.py (Main)          │
           └───────────────┬───────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼────┐         ┌───────▼────────┐    ┌──────▼───────┐
│ Data   │         │   ML Models    │    │Visualization │
│ Layer  │         │                │    │   (Plotly)   │
└───┬────┘         └───────┬────────┘    └──────────────┘
    │                      │
    │              ┌───────┴────────┐
    │              │                │
┌───▼────────┐ ┌──▼──────┐  ┌─────▼─────┐
│data_loader │ │forecast │  │ salary    │
│data_cleaner│ │         │  │ predictor │
└────────────┘ └─────────┘  └───────────┘
                              │
                        ┌─────▼──────┐
                        │recommendation│
                        └────────────┘
```

### Module Structure

```
tech-skill-tracker/
│
├── app.py                          # Main Streamlit application (UI layer)
│
├── data/                           # Dataset storage
│   └── job_listings.csv            # 1000 sample job records
│
├── modules/                        # Core business logic (modular design)
│   ├── __init__.py
│   ├── data_loader.py              # Data ingestion from CSV
│   ├── data_cleaner.py             # Data validation & cleaning
│   ├── ml_forecast.py              # Prophet time-series forecasting
│   ├── salary_predictor.py         # Random Forest salary prediction
│   └── recommendation_engine.py    # Co-occurrence skill recommendations
│
├── models/                         # Trained ML models (auto-generated)
│   └── (Generated at runtime)
│
├── logs/                           # Application logs
│
├── .streamlit/                     # Streamlit configuration
│   └── config.toml                 # Server settings
│
└── README.md                       # User documentation
```

---

## 🔬 Machine Learning Implementation

### 1. Demand Forecasting (Time-Series)

**File**: `modules/ml_forecast.py`

**Algorithm**: Facebook Prophet (with Linear Regression fallback)

**Purpose**: Predict future demand for tech skills over 3-12 months

**How it works**:
```python
# Data Preparation
skill_data = df[df['Tech Skill'] == skill_name]
monthly_data = skill_data.groupby('Month').size()

# Prophet Model
model = Prophet(yearly_seasonality=True)
model.fit(monthly_data)
future = model.make_future_dataframe(periods=months_ahead, freq='MS')
forecast = model.predict(future)

# Output: Historical + Forecast with confidence intervals
```

**Features**:
- Handles trend, seasonality, and holiday effects
- Provides confidence intervals (upper/lower bounds)
- Fallback to linear regression if Prophet unavailable
- Automatic growth/decline insights

**Use Case**: "Will demand for Python increase next quarter?"

---

### 2. Salary Prediction (Regression)

**File**: `modules/salary_predictor.py`

**Algorithm**: Random Forest Regressor (100 trees)

**Purpose**: Predict salary based on skill, location, and experience

**How it works**:
```python
# Feature Engineering
X = [Skill_Encoded, Location_Encoded, Experience_Years]
y = Salary_in_LPA

# Model Training
model = RandomForestRegressor(n_estimators=100, max_depth=10)
model.fit(X_train, y_train)

# Prediction
predicted_salary = model.predict([[skill, location, exp]])[0]
```

**Features**:
- Label encoding for categorical variables (skill, location)
- Handles unseen categories gracefully
- Provides R² score for model accuracy
- Cached for fast predictions
- Market comparison (min, median, max salaries)

**Use Case**: "What salary can I expect as a 3-year Python developer in Bengaluru?"

---

### 3. Skill Recommendations (Association Analysis)

**File**: `modules/recommendation_engine.py`

**Algorithm**: Co-occurrence Matrix Analysis

**Purpose**: Recommend complementary skills based on job market patterns

**How it works**:
```python
# Build Co-occurrence Matrix
company_skills = df.groupby('Company')['Tech Skill'].apply(list)

# Count skill pairs appearing together
for skills in company_skills:
    for skill1, skill2 in combinations(skills, 2):
        cooccurrence[skill1][skill2] += 1

# Recommend top co-occurring skills
recommendations = cooccurrence[current_skill].sort_values()
```

**Features**:
- Identifies skills that companies hire together
- Scores based on frequency of co-occurrence
- Provides salary and job count for recommendations
- Three modes:
  1. **Complementary Skills**: "What goes well with Python?"
  2. **Job Role Skills**: "What skills do Data Scientists need?"
  3. **Learning Path**: "How do I go from my skills to Data Scientist?"

**Use Case**: "If I know Python, what other skills should I learn?"

---

## 📊 Dashboard Features

### Tab 1: Overview
- **Metrics**: Total jobs, unique skills, companies, average salary
- **Top Skills**: Bar chart of 10 most in-demand skills
- **Location Distribution**: Pie chart of job openings by city
- **Dataset Summary**: Key statistics and date ranges

### Tab 2: Visualization
- **Skill Trends**: Line charts showing demand over time for top 5 skills
- **Salary Analysis**: 
  - Box plots comparing salaries across skills
  - Scatter plot of salary vs. experience
- **Co-occurrence**: Bar chart of skill combinations that appear together

### Tab 3: Forecast
- **Skill Selection**: Choose any skill from dataset
- **Time Range**: Predict 3-12 months ahead
- **Visualization**: Line chart with historical data + forecast
- **Insights**: Growth/decline percentage, average monthly openings

### Tab 4: Salary Insights
- **Salary Predictor**: Interactive form (skill, location, experience)
- **Market Comparison**: Min, median, max salary ranges
- **Skill Analysis**: Select skill to see:
  - Comparison to market average
  - Experience correlation
  - Location-specific insights
  - Salary distribution histogram

### Tab 5: Recommendations
- **Complementary Skills**: Find skills that pair well with current skill
- **Job Role Analysis**: Discover required skills for target role
- **Learning Path**: Personalized roadmap from current skills to dream job

---

## 🚀 Setup Instructions (Local PC)

### Step 1: Prerequisites
- Python 3.8 or higher installed
- pip (comes with Python)
- Terminal/Command Prompt access

### Step 2: Download Project
1. Download or clone the project to your local machine
2. Navigate to project folder:
   ```bash
   cd tech-skill-tracker
   ```

### Step 3: Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install streamlit pandas numpy scikit-learn prophet joblib plotly
```

**Alternative** (if you have requirements.txt):
```bash
pip install -r requirements.txt
```

### Step 5: Verify Data
Ensure `/data` folder exists with `job_listings.csv`:
```bash
# On Windows
dir data

# On macOS/Linux
ls data/
```

### Step 6: Run Application
```bash
streamlit run app.py
```

### Step 7: Access Dashboard
- Browser should auto-open to `http://localhost:8501`
- If not, manually open the URL shown in terminal

### Step 8: Explore!
- Try different filters in sidebar
- Navigate through all 5 tabs
- Test forecasting, salary prediction, and recommendations

---

## 🔄 How the System Works (Data Flow)

### 1. Data Loading Phase
```
User starts app
    ↓
load_job_data() reads CSV files from /data
    ↓
Returns combined DataFrame + file count
    ↓
Cached by Streamlit (@st.cache_data)
```

### 2. Data Cleaning Phase
```
Raw DataFrame
    ↓
clean_job_data() removes duplicates
    ↓
Validates data types (date, numeric)
    ↓
Removes invalid records (negative salary/exp)
    ↓
Standardizes text fields (trim, lowercase locations)
    ↓
Returns clean DataFrame
    ↓
validate_data() checks required columns
```

### 3. ML Model Training Phase
```
Clean DataFrame
    ↓
train_salary_model() encodes features
    ↓
Splits data (80/20 train/test)
    ↓
Trains Random Forest
    ↓
Saves model + encoders
    ↓
Cached (@st.cache_resource)
```

### 4. User Interaction Phase
```
User selects filters (sidebar)
    ↓
DataFrame filtered by: date, skills, location, experience
    ↓
User clicks tab (Overview, Viz, Forecast, Salary, Rec)
    ↓
Tab-specific visualizations/predictions generated
    ↓
Plotly charts rendered
    ↓
Results displayed to user
```

### 5. Prediction Phase (Example: Forecast)
```
User selects skill + months
    ↓
forecast_skill_demand() filters data for skill
    ↓
Groups by month
    ↓
Prophet fits model to historical data
    ↓
Generates future predictions
    ↓
create_forecast_chart() visualizes
    ↓
get_forecast_insights() analyzes trends
    ↓
Results shown to user
```

---

## 📈 Performance Optimizations

### Caching Strategy
1. **@st.cache_data** (data-related):
   - `load_job_data()`: Prevents re-reading CSV files
   - `clean_job_data()`: Avoids re-cleaning on filter changes
   - `predict_salary()`: Caches prediction results

2. **@st.cache_resource** (model-related):
   - `train_salary_model()`: Prevents re-training on every run
   - `forecast_skill_demand()`: Caches forecast models

### Efficiency Techniques
- Pandas vectorized operations (no loops)
- Lazy loading (models trained only when needed)
- Filtered dataframes passed to functions (smaller data)
- Plotly for interactive charts (no server round-trips)

---

## 🎯 Use Cases

### For Job Seekers
1. **Skill Planning**: See which skills are growing in demand
2. **Salary Negotiation**: Know market rates for your profile
3. **Career Roadmap**: Get learning path from current skills to dream job
4. **Location Decisions**: Compare salary ranges across cities

### For Recruiters
1. **Market Intelligence**: Understand demand trends
2. **Salary Benchmarking**: Set competitive compensation
3. **Skill Gaps**: Identify hard-to-find skill combinations

### For Educators
1. **Curriculum Planning**: Teach in-demand skills
2. **Student Guidance**: Show career paths and requirements
3. **Industry Alignment**: Track what industry needs

---

## 🔧 Customization Guide

### Adding Your Own Data

**Option 1: Replace existing data**
1. Navigate to `/data` folder
2. Replace `job_listings.csv` with your file
3. Ensure same column structure
4. Restart app

**Option 2: Add more data**
1. Add new CSV files to `/data` folder
2. Must have same columns
3. App automatically combines all files

### Required CSV Format
```csv
Job Title,Tech Skill,Company,Location,Salary (in LPA),Experience Required (in years),Date Posted
Data Scientist,Python,Google,Bengaluru,18.5,4,2024-01-15
Backend Developer,Java,Amazon,Hyderabad,15.0,3,2024-01-12
```

### Extending Functionality

**Add new visualization**:
```python
# In app.py, under Visualization tab
with viz_tab4:  # Create new sub-tab
    st.subheader("Your Custom Chart")
    fig = px.bar(...)  # Your chart
    st.plotly_chart(fig)
```

**Add new ML model**:
1. Create `modules/your_model.py`
2. Implement train/predict functions
3. Import in `app.py`
4. Add UI elements in relevant tab

---

## 🐛 Troubleshooting

### Issue: "No data found"
**Cause**: CSV file missing or wrong location
**Solution**: 
1. Check `/data` folder exists
2. Ensure CSV file is present
3. Verify file has correct columns

### Issue: "Prophet not available"
**Cause**: Prophet not installed
**Solution**: `pip install prophet`
**Note**: App falls back to linear regression automatically

### Issue: Charts not showing
**Cause**: Plotly not installed or outdated
**Solution**: `pip install --upgrade plotly`

### Issue: Slow performance
**Cause**: Large dataset or cache issues
**Solution**:
1. Clear cache: Settings (⋮) → Clear cache
2. Reduce dataset size for testing
3. Filter data to smaller subset

### Issue: Model prediction errors
**Cause**: Insufficient training data
**Solution**: Ensure at least 10-20 records in dataset

---

## 💡 Best Practices

### Data Quality
- ✅ Clean, complete data (no missing critical fields)
- ✅ Realistic salary ranges (6-50 LPA typical in India)
- ✅ Valid dates (YYYY-MM-DD format)
- ✅ Consistent location names (use data_cleaner.py mappings)

### Usage Tips
1. **Start with filters**: Narrow down to relevant data segment
2. **Explore tabs sequentially**: Overview → Viz → Forecast → Salary → Rec
3. **Cross-reference insights**: Compare forecasts with current trends
4. **Use learning paths**: Combine recommendations from multiple sources

### Performance
- Keep dataset under 10,000 records for smooth performance
- Clear cache occasionally
- Restart app after adding new data

---

## 📚 Technical Details

### Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | ≥1.28 | Web framework |
| pandas | ≥2.0 | Data manipulation |
| numpy | ≥1.24 | Numerical operations |
| scikit-learn | ≥1.3 | Random Forest model |
| prophet | ≥1.1.4 | Time-series forecasting |
| plotly | ≥5.17 | Interactive charts |
| joblib | ≥1.3 | Model persistence |

### Browser Compatibility
- Chrome ✅
- Firefox ✅
- Safari ✅
- Edge ✅

### System Requirements
- RAM: 2GB minimum, 4GB recommended
- Storage: 500MB for app + data
- CPU: Any modern processor
- OS: Windows, macOS, Linux

---

## 🎓 Learning Resources

### Understanding the ML Models

**Prophet Documentation**: https://facebook.github.io/prophet/
- Time-series forecasting basics
- Understanding trend + seasonality

**Random Forest Guide**: https://scikit-learn.org/stable/modules/ensemble.html
- How ensemble methods work
- Feature importance

**Co-occurrence Analysis**: Basic association rule mining concept

---

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review README.md
3. Inspect error messages in app
4. Verify data format matches requirements

---

**Built with ❤️ using Streamlit, Pandas, and Machine Learning**

*Last Updated: October 2024*
