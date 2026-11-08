# 35: Deterministic jd_matcher engine

**What to build:** `match_resume_to_job()` per plan: weighted must-have coverage, experience gap, title similarity, posting health. No LLM.

**Blocked by:** 34 - Week-1 benchmark labeled set.

**Status:** done

- [x] `modules/jd_matcher.py` deterministic engine (no LLM, no network, no writes)
- [x] Score = 0.7 * must coverage + 0.3 * nice coverage (0–100), own formula
- [x] Must-have vs nice-to-have split by nearest preceding section cue
- [x] Experience gap + title similarity + posting health + confidence returned
- [x] Unit tests cover cue split, seeded scoring, unknown-job error
