# 25: Market Overview end-to-end

**What to build:** The Market Overview tab working end to end against the FastAPI backend: last-24h metric cards, top-skills bar, location pie (state-wise), and Recent Job Postings table with Apply Now buttons.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Frontend page renders metric cards from `GET /api/market/overview`
- [x] Top-skills bar renders from `GET /api/market/top-skills`
- [x] Location pie renders state-wise distribution from `GET /api/market/locations`
- [x] Recent Job Postings table renders from `GET /api/market/recent-postings` with Apply Now links
- [x] Header skill/location filters flow into all Overview queries (verified with filtered request)
- [x] At least one integration test covers the Overview → `/api/market/*` round-trip
