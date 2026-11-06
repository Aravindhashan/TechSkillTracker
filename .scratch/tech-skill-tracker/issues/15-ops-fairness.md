# 15: Ops and fairness (demand audit, offline eval, free host)

**What to build:** Demand fairness audit (ROI/momentum gaps across locations, remote status, and company types after controlling for skill and experience, reported openly), offline evaluation for recommenders and semantic search (Precision@k, NDCG, holdout splits), and deploy on HF Spaces free tier.

**Blocked by:** 09 (data ingestion), 11 (demand science), 12 (global forecaster), 13 (resume skill-gap), 14 (semantic search)

**Status:** in-progress

- [ ] Demand fairness audit: group ROI/momentum by location, remote status, and company type, report gaps
- [x] Offline eval: Precision@k, NDCG, holdout splits for recommenders and semantic search (`modules/evaluation.py`)
- [ ] Deploy Streamlit app on HF Spaces (free tier)
- [x] Configure GitHub Actions cron for 6h ingestion (`.github/workflows/ingest.yml`)
- [ ] Conformal prediction intervals (optional, if time)

**Note:** This item was rewritten to be salary-free. The original salary fairness audit and the old ticket 10 (salary LightGBM) are obsolete — salary is not collected, stored, or shown anywhere in this project. Historical copies of the original wording may exist in older docs.
