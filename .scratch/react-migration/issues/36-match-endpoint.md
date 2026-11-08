# 36: POST /api/match endpoint

**What to build:** The stateless, rate-limited per-job match endpoint wrapping `jd_matcher`.

**Blocked by:** 35 - Deterministic jd_matcher engine.

**Status:** done

- [x] `POST /api/match` returns match score + matched/missing skills for a stored posting
- [x] Stateless: parsed skills + `job_id` in, no DB writes (resumes never persisted)
- [x] In-memory rate limit (60/min/IP) returns 429 when exceeded
- [x] Unknown `job_id` returns 404; malformed payload returns 422
- [x] Pydantic request/response schemas
