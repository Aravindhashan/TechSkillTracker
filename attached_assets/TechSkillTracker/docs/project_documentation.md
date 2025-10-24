# Tech Skill Tracker: Comprehensive BI Dashboard

## 1. Introduction

The Tech Skill Tracker is a powerful Business Intelligence (BI) dashboard built using Streamlit, designed to provide in-depth insights into the tech job market in India. It leverages data analysis, machine learning, and natural language processing to offer a comprehensive view of skill demand, salary trends, and career progression paths. This tool is invaluable for job seekers, recruiters, and HR professionals looking to understand and navigate the dynamic tech landscape.

## 2. Features

### 2.1. Interactive BI Dashboard

*   **Dynamic Visualizations:** Presents key metrics and trends through interactive charts and graphs, including top in-demand skills, job openings by location, and skill demand trends over time.
*   **Advanced Filtering:** Allows users to filter data by skills, locations, experience range, and date range for granular analysis.
*   **Animated Metrics:** Displays real-time KPIs such as most frequent skill, top company, hiring location, and average salary.
*   **Smart Insights Engine:** Generates AI-like textual insights summarizing key findings from the data.

### 2.2. Enhanced Forecasting with Prophet

*   **12-Month Trend Forecasting:** Utilizes the Prophet library for robust time-series forecasting of skill demand, providing predictions for the next 12 months.

### 2.3. Regional & Sector-Based Insights

*   **Location-Specific Analysis:** Provides detailed breakdowns of job opportunities and salary trends across various Indian cities.
*   **Sector-Based Analysis (New):** Incorporates an optional 'Sector' column in the dataset, enabling visualizations and filtering of job data by industry sector.

### 2.4. Skill Recommendation Engine

*   **ML-Powered Recommendations:** Suggests complementary skills based on co-occurrence patterns in job postings, helping users identify valuable skill combinations.

### 2.5. Job Role Classification

*   **NLP-Driven Classification:** Employs a pre-trained NLP model (DistilBERT) to classify raw job titles into standardized job roles (e.g., Data Scientist, Full Stack Developer), improving data consistency and analysis.

### 2.6. Salary Prediction Model

*   **Regression-Based Predictions:** Predicts potential salaries based on job role, skills, location, and experience using a trained regression model.

### 2.7. Personalized Learning Path Generator

*   **Dynamic Career Roadmaps:** Generates personalized learning paths based on user-defined dream jobs, current skills, and market insights, including core skills, advanced skills, soft skills, and experience-level salary expectations.

### 2.8. Personalized PDF Report Generation

*   **Comprehensive Reports:** Creates detailed PDF reports summarizing all key insights, including executive summaries, skill analysis, salary trends, geographic distribution, and now incorporating trend forecasts, skill recommendations, job classifications, and salary predictions.

## 3. Architecture

The system architecture is designed for modularity and scalability, as illustrated in the `architecture_diagram.png`.

## 4. Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd TechSkillTracker
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    (Note: A `requirements.txt` file will be generated based on the installed packages.)
4.  **Data Setup:**
    *   Create a `data` directory in the project root.
    *   Place your job posting CSV files inside the `data` directory. Ensure they have the required columns: `Job Title`, `Tech Skill`, `Company`, `Location`, `Salary (in LPA)`, `Experience Required (in years)`, `Date Posted`, and optionally `Sector`.

## 5. Usage

To run the Streamlit application:

```bash
streamlit run app.py
```

Access the dashboard in your web browser at the provided local URL (usually `http://localhost:8501`).

## 6. Project Structure

```
TechSkillTracker/
├── app.py                  # Main Streamlit application
├── data/                   # Directory for CSV data files
│   └── job_postings.csv    # Sample data file
├── models/                 # Directory for trained ML models
│   ├── nlp_model.py        # Job role classification model
│   └── salary_model.py     # Salary prediction model
├── docs/                   # Project documentation and diagrams
│   ├── architecture_diagram.mmd # Mermaid diagram source
│   ├── architecture_diagram.png # Rendered architecture diagram
│   └── project_documentation.md # This documentation file
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata (if using Poetry)
└── README.md               # Project README
```

## 7. Future Enhancements

*   Integration with live job board APIs for real-time data.
*   More sophisticated NLP models for deeper insights from job descriptions.
*   User authentication and personalized dashboards.
*   Deployment to cloud platforms for wider accessibility.

## 8. Contact

For any queries or collaborations, please contact [Your Name/Team Name] at [Your Email/Contact Info].


