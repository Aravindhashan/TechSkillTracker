# 40: Ghost-risk scoring

**What to build:** Deterministic ghost-risk estimate from posting lifecycle events (age, repost count, stale-close ratio), labeled "estimated risk".

**Blocked by:** 39 - Posting-events logging.

**Status:** done

- [x] `modules/ghost_risk.py` deterministic scorer (0–1 risk + low/medium/high label + factors)
- [x] Blends age (30d cap), closed/inactive, repost count, stale last_seen
- [x] Unit tests: fresh=low, stale/closed=high, unknown job never crashes
