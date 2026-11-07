# 31: Demand Forecasting end-to-end

**What to build:** The Demand Forecasting tab working end to end: free-text skill entry with suggestions, months ahead and engine controls, forecast chart with confidence band, and insights.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] Free-text skill input accepts any skill with datalist suggestions from top skills
- [x] Forecast chart renders monthly forecast values with confidence interval band from `GET /api/forecast/{skill}`
- [x] Growth/decline insight and model selection metadata render below the chart
- [x] Unknown skill returns 404 and invalid engine returns 422 (verified end to end)
- [x] Header skill filter pre-fills the forecast skill
- [x] At least one integration test covers auto-selection and fallback
