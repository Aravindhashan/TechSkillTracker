# 29: Fairness Audit end-to-end

**What to build:** The Fairness Audit tab working end to end: by-location, by-remote, and by-company-type tables with adjusted gaps and confidence level.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] Frontend page renders by-location, by-remote, and by-company-type tables from `GET /api/fairness`
- [x] Adjusted gaps and confidence level propagate to the UI
- [x] Low-confidence state is shown when history is thin
- [x] At least one integration test covers the Fairness Audit → `GET /api/fairness` round-trip
