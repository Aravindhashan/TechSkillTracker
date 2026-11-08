# 42: Tests

**What to build:** End-to-end tests for Slice 3: events logged on ingest, score ordering (stale > fresh), badge payload renders via the endpoint.

**Blocked by:** 39 - Posting-events logging; 40 - Ghost-risk scoring; 41 - Badge surface.

**Status:** done

- [x] `tests/test_ghost_risk_e2e.py`: ingest logs events for both postings
- [x] Stale/closed posting scores higher (label `high`) than fresh (`low`)
- [x] `POST /api/search` carries `ghost_risk` with a valid label on every result
- [x] `GhostBadge` render tests (label + null) shipped with ticket 41
- [x] Full Slice 3 suite green: posting-events + ghost-risk + e2e (10 passed)
