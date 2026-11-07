# 28: Search & ROI end-to-end

**What to build:** The Search & ROI tab working end to end: semantic job search with ranked postings and the demand-based skill ROI table/chart.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] Search returns ranked postings with scores from `POST /api/search`
- [x] Lexical fallback works when embeddings are unavailable
- [x] ROI table renders momentum, premium, roi_score, and confidence from `GET /api/roi`
- [x] ROI chart renders top skills by demand ROI score
- [x] At least one integration test covers search and ROI (fake embedder, no model download)
