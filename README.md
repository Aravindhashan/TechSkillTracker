# Tech Skill Tracker

A business intelligence dashboard for exploring tech skill demand in the Indian job market. Built with Streamlit, it combines interactive analytics, time-series forecasting, salary prediction, and skill recommendations in one app.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B?logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7%2B-F7931E?logo=scikitlearn&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-6.3%2B-3F4F75?logo=plotly&logoColor=white)

---

## Overview

Tech Skill Tracker turns a CSV of job postings into a five-tab analytics workspace:

- **Market Overview** — headline metrics, top skills, and hiring locations
- **Data Visualization** — demand trends, salary distributions, and skill co-occurrence
- **Demand Forecasting** — 3–12 month forecasts per skill with confidence intervals
- **Skill Recommendations** — complementary skills, role requirements, and a learning roadmap

The bundled dataset contains 1,000 job listings covering 50 technologies, 40 companies, and 10 Indian cities, posted between January 2023 and September 2024.

---

## Features

| Area | What it does |
| --- | --- |
| Interactive filters | Filter by date range, technology, location, and experience from the sidebar |
| Market metrics | Total openings, unique technologies, hiring companies, average salary |
| Trend analysis | Monthly posting volume for the top five skills |
| Salary analysis | Box plots by skill, salary vs. experience scatter, per-skill histograms |
| Forecasting | Selectable SARIMAX or Prophet time-series models with confidence bands and growth/decline insights |
| Recommendations | Company-level skill co-occurrence, role-based skill analysis, personalized learning paths |
| Learning resources | Curated links for popular skills plus YouTube, Udemy, Coursera, and freeCodeCamp searches |
| PDF reports | Optional ReportLab script for a formatted career report |

---

## Tech Stack

| Layer | Tools |
| --- | --- |
| UI | Streamlit |
| Data | pandas, NumPy |
| Visualization | Plotly |
| Machine learning | scikit-learn (Random Forest), statsmodels (SARIMAX, exponential smoothing), Prophet (optional) |
| Persistence | joblib |
| Reporting | ReportLab (optional) |

---

## Project Structure

```
TechSkillTrackerWithML/
├── app.py                          # Streamlit app: layout, filters, all five tabs
├── main.py                         # Placeholder entry point
├── pyproject.toml                  # Declared Python dependencies
├── PROJECT_DOCUMENTATION.md        # Extended design and usage documentation
├── data/
│   └── job_listings.csv            # 1,000 sample job postings
├── modules/
│   ├── data_loader.py              # CSV ingestion and concatenation
│   ├── data_cleaner.py             # Validation, deduplication, location normalization
│   ├── ml_forecast.py              # SARIMAX/Prophet forecasting with fallbacks
│   ├── salary_predictor.py         # Random Forest training and prediction
│   ├── recommendation_engine.py    # Co-occurrence analysis and learning paths
│   ├── learning_resources.py       # Curated and generated learning links
│   └── report_generator.py         # PDF report builder (not wired into the app)
├── reports/
│   ├── generate_report.py          # CLI PDF report from JSON input
│   ├── generate_report_simple.py   # Dependency-light fallback version
│   └── output_report.pdf           # Example generated report
├── logs/                           # Runtime logs
└── .streamlit/
    └── config.toml                 # Server binds to 0.0.0.0:5000
```

---

## Getting Started

### Prerequisites

- Python 3.11 or newer
- pip

### 1. Create a virtual environment

**Windows (PowerShell)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install streamlit pandas numpy plotly scikit-learn joblib statsmodels
```

Prophet is optional; install it to enable the Prophet forecasting engine:

```bash
pip install prophet
```

The PDF report scripts additionally require:

```bash
pip install reportlab
```

> The forecasting tab lets you choose Auto, SARIMAX, Prophet, or Linear Regression. Auto tries SARIMAX first, then Prophet, then exponential smoothing, then linear regression.

### 3. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:5000**. The port comes from `.streamlit/config.toml`; if you prefer Streamlit's default, run `streamlit run app.py --server.port 8501`.

---

## Dataset

The app loads every `*.csv` file in `data/` and concatenates them, so you can split or extend the data without changing code. Required columns:

| Column | Type | Example |
| --- | --- | --- |
| `Job Title` | string | `Data Scientist` |
| `Tech Skill` | string | `Python` |
| `Company` | string | `Google` |
| `Location` | string | `Bengaluru` |
| `Salary (in LPA)` | numeric | `18.5` |
| `Experience Required (in years)` | numeric | `4` |
| `Date Posted` | date (`YYYY-MM-DD`) | `2024-01-15` |

Cleaning rules applied on load:

- Exact duplicate rows are dropped.
- Dates are required; rows without a valid posting date are removed.
- Salary and experience are coerced to numeric. Missing values are kept so live
  postings still count toward skill demand, and charts that need those fields
  ignore them.
- Salaries must be between 0 and 200 LPA; experience between 0 and 50 years.
- Text fields are trimmed, and city aliases are normalized (for example `bangalore` → `Bengaluru`, `bombay` → `Mumbai`, including `Mumbai, Maharashtra, India`).

To use your own data, replace or add CSVs in `data/` and restart the app.

---

## How the Models Work

### Demand forecasting — `modules/ml_forecast.py`

1. Filters postings for the selected skill and aggregates them by month.
2. Runs the selected engine — `Auto`, `SARIMAX`, `Prophet`, or `Linear Regression`.
3. `Auto` fits `SARIMAX(1, 1, 1)` first, then Prophet, then Holt-Winters exponential smoothing, then linear regression as the final fallback.
4. SARIMAX and Prophet return confidence intervals; forecasts are clipped at zero.
5. Reports growth or decline versus the latest historical month over the selected horizon.

The model needs at least two months of data for the selected skill, and at least four months to use SARIMAX.

### Skill recommendations — `modules/recommendation_engine.py`

- Groups skills by company and counts pairs that appear together, producing a symmetric co-occurrence matrix.
- **Complementary skills** ranks technologies that co-occur with the selected skill.
- **Job role analysis** matches the entered title against `Job Title` and ranks skills by frequency and average salary.
- **Learning path** compares your current skills with role requirements and sorts gaps by `frequency × 0.6 + average salary × 0.4`.

Results are cached with `@st.cache_data` and `@st.cache_resource` so models and aggregations are not rebuilt on every interaction.

---

## Using the Dashboard

1. Narrow the dataset with the sidebar filters.
2. Start at **Market Overview** for the headline numbers.
3. Use **Data Visualization** to inspect trends, salary spread, and skill combinations.
4. Open **Demand Forecasting**, pick a skill and horizon, then click **Generate Forecast**.
5. In **Skill Recommendations**, try all three modes: complementary skills, a target role, and a full learning roadmap.

---

## PDF Reports

The app itself does not export PDFs. Two standalone scripts generate a formatted report:

```bash
# Built-in example data
python reports/generate_report.py --output reports/output_report.pdf

# Custom JSON input
python reports/generate_report.py --input reports/input.json --output reports/output_report.pdf
```

`reports/generate_report_simple.py` provides a lighter version, and `modules/report_generator.py` contains a reusable builder for integrating reports into the dashboard. All three require `reportlab`.

The JSON input accepts fields such as `name`, `email`, `skills`, `target_role`, `missing_skills`, `demand_forecast`, `salary_prediction`, `short_term_plan`, and `long_term_plan`.

---

## Configuration

`.streamlit/config.toml` currently sets:

```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000
```

Change `port` or `address` there, or override at launch with `--server.port`. The `headless` setting is useful for containers and remote servers; remove it if you want Streamlit to open a browser automatically.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| "No data found" | No CSV in `data/`, or columns renamed | Check the file and verify the required column names |
| "Data validation failed" | Missing required columns | Compare the header with the schema above |
| Forecast unavailable | Fewer than two months for that skill | Choose a skill with more history or widen the date filter |
| Weak or flat forecast | Sparse monthly counts | Treat results as directional, not precise |
| "Statsmodels not available" | Package not installed | `pip install statsmodels` |
| PDF script fails on import | ReportLab missing | `pip install reportlab` |
| Charts blank | Plotly version mismatch | `pip install --upgrade plotly` |
| App opens on the wrong port | Config or CLI override | Check `.streamlit/config.toml` or pass `--server.port` |
| Model refuses a prediction | Skill/location not in training data | Choose values present in the dataset |

---

## Limitations

- The bundled data is a 1,000-row sample, not a live market feed. Forecasts and salary estimates reflect that sample only.
- Salaries are annual figures in lakhs per annum (LPA) and apply to the Indian market.
- Label encoding treats skills and locations as independent categories, so the salary model cannot generalize to unseen values.
- Co-occurrence is computed at the company level, which is a proxy for skills hired together rather than a formal association-rule model.

---

## Documentation

- `PROJECT_DOCUMENTATION.md` — architecture, data flow, and an extended walkthrough
- `reports/README.md` — PDF report usage

---

## Live data pipeline (JSearch)

The dashboard can read from a scheduled ingestion store instead of static CSVs.

**Sources.** Postings come from the [JSearch](https://openwebninja.com) API (Google Jobs
aggregation, includes LinkedIn/Indeed/Glassdoor listings through a licensed API). A
Jobspy scraper exists as an **opt-in** fallback and is disabled by default
(`ENABLE_JOBSPY=true` enables it; LinkedIn is never scraped unless explicitly allowed).

**Storage.** `DATABASE_URL` selects Neon/Supabase Postgres in production; without it the
pipeline writes to the local SQLite file `data/techskill.db`. Tables:

| Table | Purpose |
| --- | --- |
| `job_postings` | One row per posting, deduped by `job_id`, with `first_seen` / `last_seen` |
| `job_skills` | Extracted skills per posting (raw + canonical) |
| `skill_taxonomy` | Canonical skills and their aliases |
| `resume_jobs` | Skill-gap reports (used by the resume feature) |
| `ingest_runs` | Per-run audit trail (fetched / inserted / updated / status) |

**Skill normalisation.** `modules/normalizer.py` resolves variants such as
`ReactJS` / `React.js` to `React` using a curated alias table, then a fuzzy match,
then `all-MiniLM-L6-v2` embeddings when the model is available. Extraction from
job descriptions uses the same taxonomy, so `Java` never matches inside `JavaScript`.

**Cadence.** `.github/workflows/ingest.yml` runs every 6 hours
(`0 */6 * * *`) and upserts by `job_id`. The JSearch free plan allows 200 requests
per month; one search per run is about 120 searches per 30-day month, so the
pipeline stays inside the quota. Set repository secrets `JSEARCH_API_KEY` and
`DATABASE_URL`.

**Local usage.**

```bash
cp .env.example .env          # add JSEARCH_API_KEY
python -m modules.ingestion --dry-run     # fetch, print, write nothing
python -m modules.ingestion              # fetch and upsert
python -m modules.ingestion --jobspy     # also run the opt-in scraper
```

The app prefers the live store when it has rows and offers a sidebar
**Data source** switch when both live and bundled CSV data are present.

**What live data does and does not include.** JSearch returns titles, companies,
locations, descriptions, and posting dates, but Indian listings frequently omit
salary. Missing salaries are stored as `NULL` and the salary tab reports `N/A`
instead of dropping the posting, so skill-demand counts stay complete.

---

## Team

- Om Aravindhashan S (23MID0222)
- Raghul (23MID0322)

---

## Acknowledgements

Built with Streamlit, pandas, NumPy, scikit-learn, statsmodels, Plotly, joblib, and ReportLab.

## License

No license file is included in this repository. Contact the authors before redistributing or using the project commercially.
