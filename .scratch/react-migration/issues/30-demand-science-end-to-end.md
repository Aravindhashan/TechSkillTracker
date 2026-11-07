# 30: Demand Science end-to-end

**What to build:** The Demand Science tab working end to end: survival curves, anomaly flags, PMI pairs, Louvain communities, and Word2Vec relatedness.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] All five sub-results render from `GET /api/demand-science` (survival, anomalies, PMI, communities, relatedness)
- [x] Relatedness tab shows a skill selector with related skills and similarity scores
- [x] Empty corpus returns empty arrays in the UI, not an error
- [x] At least one integration test covers the Demand Science → `GET /api/demand-science` round-trip with synthetic data
