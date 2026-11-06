# 12: Global forecaster + MAPE backtest

**What to build:** Replace per-skill SARIMAX/Prophet with one LightGBM model across all skills using lag and calendar features. Backtest each engine and report MAPE so Auto selects by measured accuracy instead of availability.

**Blocked by:** 09 (data ingestion and Postgres store)

**Status:** implemented (2026-11-07)

- [x] Build lag + calendar features from monthly posting counts
- [x] Train global gradient-boosting model for all skills (LightGBM API, sklearn HGBR backend)
- [x] Backtest SARIMAX/Prophet/Linear/GradientBoosting/Croston, report MAPE per skill
- [x] Auto engine selects best by MAPE (fallback to availability if no backtest)
- [x] Croston/intermittent-demand model for niche skills with many zeros

**Implemented by:** `modules/ml_forecast.py` (rewritten), `tests/test_ml_forecast.py`, and the Forecasting Engine selector in `app.py`.

**Notes:** LightGBM is optional; the implementation uses scikit-learn's `HistGradientBoostingRegressor` when LightGBM is absent. MAPE comparison is shown in the forecast insights. Croston uses the Syntetos-Boylan Approximation for intermittent demand.
