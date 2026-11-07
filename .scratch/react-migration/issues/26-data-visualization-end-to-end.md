# 26: Data Visualization end-to-end

**What to build:** The Data Visualization tab working end to end: monthly demand-trends line chart and skill co-occurrence bar chart from the backend.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] Frontend page renders demand trends from `GET /api/market/demand-trends`
- [x] Frontend page renders co-occurrence bars from `GET /api/market/skill-pairs`
- [x] Header skill/location filters flow into both charts (verified with filtered request)
- [x] Empty-data state shows a helpful message instead of a blank chart
- [x] At least one integration test covers the Data Visualization → `/api/market/*` round-trip
