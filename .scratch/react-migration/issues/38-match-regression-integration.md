# 38: Regression + integration tests

**What to build:** Labeled-set regression for the matcher plus endpoint round-trip coverage.

**Blocked by:** 34 - Week-1 benchmark labeled set; 35 - Deterministic jd_matcher engine; 36 - POST /api/match endpoint.

**Status:** done

- [x] Labeled-set regression: self-match scores 100 on the benchmark set (`tests/test_match_regression.py`)
- [x] Empty-resume regression scores 0 and lists all must-haves
- [x] Endpoint round-trip: full-skills resume scores 100 via `POST /api/match`
- [x] Weights renormalize over non-empty buckets (empty nice-to-have gives no free points)

### Notes
- Regression caught a real bug: empty nice-to-have bucket awarded free 30 points to an empty resume. Fixed by renormalizing weights over non-empty buckets.
- Two labeled rows have zero extracted skills (score 0 vacuously) — skipped in the self-match test.
