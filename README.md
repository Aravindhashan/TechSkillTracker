# Tech Skill Tracker

A business intelligence dashboard for exploring tech skill demand in the Indian job market. It combines interactive analytics, time-series forecasting, semantic job search, and skill recommendations in one app.

> **Current architecture (React rewrite, branch `react-migrated`):** a Vite + React + TypeScript frontend (`frontend/`) talks to a FastAPI backend (`backend/`, see `backend/main.py`). The legacy Streamlit app (`app.py`) is retained for reference on `main` and remains deployable. Set `VITE_API_BASE` (default `http://localhost:8000`) to point the frontend at the backend; run the backend with `uvicorn backend.main:app --reload`.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B?logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7%2B-F7931E?logo=scikitlearn&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-6.3%2B-3F4F75?logo=plotly&logoColor=white)

---

## Overview

Tech Skill Tracker turns live job postings into an eight-tab analytics workspace:

- **Market Overview** — headline metrics, top skills, and hiring locations
- **Data Visualization** — demand trends and skill co-occurrence
- **Demand Forecasting** — 3–12 month forecasts per skill with confidence intervals
- **Skill Recommendations** — complementary skills, role requirements, and a learning roadmap
- **Resume Analysis** — PDF/DOCX skill-gap scoring
- **Demand Science** — survival, anomaly, PMI, community, and relatedness analysis
- **Search & ROI** - semantic job search plus demand-based skill ROI
- **Fairness Audit** - demand gaps by location, remote status, and company type (controlled for skill and experience)

The app ingests live job postings from JSearch (and optionally Jobspy) on a 6-hour schedule and stores them in SQLite (local) or Postgres (production). There is no bundled static dataset.

---

## Features

| Area | What it does |
| --- | --- |
| Interactive filters | Filter by date range, technology, location, and experience from the sidebar |
| Market metrics | Total openings, unique technologies, and hiring companies |
| Trend analysis | Monthly posting volume for the top five skills |
| Forecasting | Selectable SARIMAX or Prophet time-series models with confidence bands and growth/decline insights |
| Recommendations | Company-level skill co-occurrence, role-based skill analysis, personalized learning paths |
| Semantic search | Sentence-transformer embeddings, FAISS retrieval, optional cross-encoder reranking |
| Skill ROI | Demand momentum + controlled OLS premium per skill (no salary inputs) |
| Learning resources | Curated links for popular skills plus YouTube, Udemy, Coursera, and freeCodeCamp searches |
| PDF reports | Optional ReportLab script for a formatted career report |

---

## Tech Stack

| Layer | Tools |
| --- | --- |
| UI | React (Vite + TypeScript, `frontend/`); legacy: Streamlit (`app.py`) |
| Data | pandas, NumPy |
| Visualization | Plotly (both UIs) |
| Machine learning | scikit-learn (Random Forest), statsmodels (SARIMAX, exponential smoothing), Prophet (optional) |
| Persistence | joblib |
| Reporting | ReportLab (optional) |

---

## Project Structure

```
TechSkillTrackerWithML/
├── app.py                          # Streamlit app
├── main.py                         # Placeholder entry point
├── pyproject.toml                  # Declared Python dependencies
├── requirements-ingest.txt         # Lightweight deps for the scheduled ingestion job
├── .env.example                    # Template for secrets (copy to .env)
├── .github/workflows/ingest.yml    # 6-hour ingestion cron
├── data/                           # Local SQLite store (gitignored) + raw payloads
├── modules/
│   ├── data_loader.py              # Live store loader
│   ├── data_cleaner.py             # Validation, deduplication, location normalization
│   ├── ml_forecast.py              # SARIMAX/Prophet/GB/Croston forecasting
│   ├── normalizer.py               # Skill taxonomy + embedding normalization
│   ├── ingestion.py                # JSearch + Jobspy ingestion
│   ├── jobspy_adapter.py           # Opt-in Jobspy fallback
│   ├── store.py                    # SQLite/Postgres persistence
│   ├── env.py                      # .env loader
│   ├── resume_analyzer.py          # Resume skill-gap analysis
│   ├── recommendation_engine.py    # Co-occurrence analysis and learning paths
│   ├── demand_science.py           # Survival, anomaly, dedup, PMI, communities
│   ├── semantic_search.py          # Embeddings + FAISS + cross-encoder reranking
│   ├── skill_roi.py                # Demand-based skill ROI regression
│   └── learning_resources.py       # Curated and generated learning links
├── tests/                     # pytest suite
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

## Data

The app reads only from the live ingestion store (SQLite locally, Postgres in production). There is no bundled CSV. The store exposes one row per posting-skill pair with these fields:

| Column | Type | Example |
| --- | --- | --- |
| `Job Title` | string | `Data Scientist` |
| `Tech Skill` | string | `Python` |
| `Company` | string | `Google` |
| `Location` | string | `Bengaluru` |
| `Experience Required (in years)` | numeric | `4` |
| `Date Posted` | date (`YYYY-MM-DD`) | `2024-01-15` |

Cleaning rules applied on load:

- Exact duplicate rows are dropped.
- Dates are required; rows without a valid posting date are removed.
- Experience is coerced to numeric. Missing values are kept so live postings still count toward skill demand.
- Experience must be between 0 and 50 years.
- Text fields are trimmed, and city aliases are normalized (for example `bangalore` → `Bengaluru`, `bombay` → `Mumbai`, including `Mumbai, Maharashtra, India`).

To populate data, run the ingestion job: `python -m modules.ingestion` (see "Live data pipeline").

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
- **Job role analysis** matches the entered title against `Job Title` and ranks skills by frequency.
- **Learning path** compares your current skills with role requirements and sorts gaps by demand.

Results are cached with `@st.cache_data` and `@st.cache_resource` so models and aggregations are not rebuilt on every interaction.

---

## Using the Dashboard

1. Narrow the dataset with the sidebar filters.
2. Start at **Market Overview** for the headline numbers.
3. Use **Data Visualization** to inspect demand trends and skill combinations.
4. Open **Demand Forecasting**, pick a skill and horizon, then click **Generate Forecast**.
5. In **Skill Recommendations**, try all three modes: complementary skills, a target role, and a full learning roadmap.

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
| "No data found" | Store is empty | Run `python -m modules.ingestion` to ingest postings |
| "Data validation failed" | Missing required columns | Check the store schema (`modules/store.py`) |
| Forecast unavailable | Fewer than two months for that skill | Choose a skill with more history or widen the date filter |
| Weak or flat forecast | Sparse monthly counts | Treat results as directional, not precise |
| "Statsmodels not available" | Package not installed | `pip install statsmodels` |
| Charts blank | Plotly version mismatch | `pip install --upgrade plotly` |
| App opens on the wrong port | Config or CLI override | Check `.streamlit/config.toml` or pass `--server.port` |
| Model refuses a prediction | Skill/location not in training data | Choose values present in the dataset |

---

## Limitations

- The corpus is whatever the scheduled ingestion run has collected so far; forecasts and ROI scores need several months of history to stabilise.
- Skill ROI is an association in observed postings, not a causal effect.
- Co-occurrence is computed at the company level, which is a proxy for skills hired together rather than a formal association-rule model.

---

## Documentation

- `PROJECT_DOCUMENTATION.md` — architecture, data flow, and an extended walkthrough (historical; describes the pre-live, pre-salary-removal era)

---

## Live data pipeline (JSearch)

The dashboard can read from a scheduled ingestion store instead of static CSVs.

**Sources.** Postings come from two free sources:

- **JSearch** (Google Jobs aggregation, includes LinkedIn/Indeed/Glassdoor listings
  through a licensed API) — the primary, reliable source.
- **Jobspy** (Indeed + Glassdoor scraping) — a free, best-effort second source that
  runs locally and degrades gracefully when the boards block the runner. LinkedIn is
  never scraped. Both sources are deduplicated by a normalized title+company+location
  key and by MinHash near-duplicate matching, preferring the record with the richest description.

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

## Deploy on Hugging Face Spaces (free)

The app runs as a Streamlit Space with no code changes required beyond
`requirements.txt` (mirrors `pyproject.toml` + the `search` extra).

1. Push `main` to GitHub, then create a Space at <https://huggingface.co/new-space>
   with SDK **Streamlit** and this repo.
2. Set **Space variables** (Settings → Variables and secrets):
   - `DATABASE_URL` — Neon free Postgres pooler URL
     (`postgresql://user:password@host/dbname?sslmode=require`)
   - `JSEARCH_API_KEY` — JSearch (OpenWebNinja) key, 200 free requests/month
   - `PYTHON_VERSION` — `3.11` (Spaces supports 3.11/3.12; 3.13 wheels for
     `torch` / `faiss-cpu` are unreliable)
3. Set the **same two secrets** on the GitHub repo (`JSEARCH_API_KEY`,
   `DATABASE_URL`) so the 6-hour Actions cron writes to Neon too.
4. The Space boots against Neon via `prod.py` root; Actions keeps the store
   fresh. Spaces disk is ephemeral, so Postgres (not the local SQLite file)
   is the source of truth in production.

**Local usage.**

```bash
cp .env.example .env          # add JSEARCH_API_KEY
python -m modules.ingestion --dry-run     # fetch, print, write nothing
python -m modules.ingestion              # fetch and upsert
python -m modules.ingestion --jobspy     # also run the opt-in scraper
```

The app prefers the live store. If it is empty, the app shows a message with instructions to run ingestion.

**What live data does and does not include.** JSearch returns titles, companies,
locations, descriptions, and posting dates. Salary is intentionally not collected or
used anywhere in this project, so missing salary fields never block a posting and
skill-demand counts stay complete.

---

## Team

- Om Aravindhashan S (23MID0222)
- Raghul (23MID0322)

---

## Acknowledgements

Built with Streamlit, pandas, NumPy, scikit-learn, statsmodels, Plotly, joblib, and ReportLab.

## License

No license file is included in this repository. Contact the authors before redistributing or using the project commercially.
