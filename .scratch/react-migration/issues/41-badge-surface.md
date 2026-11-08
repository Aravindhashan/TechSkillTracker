# 41: Badge surface

**What to build:** Ghost-risk badge on Search & ROI cards + "Match a JD" detail; no new page.

**Blocked by:** 40 - Ghost-risk scoring.

**Status:** done

- [x] `/api/search` annotates each result with `ghost_risk` (risk + label)
- [x] `/api/match` includes `ghost_risk` in the response
- [x] Badge renders "Estimated risk: low/medium/high" on search cards and the Match tab
- [x] Backend tests assert `ghost_risk` present; frontend `GhostBadge` tests cover label + null rendering
