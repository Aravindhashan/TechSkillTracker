"""Per-job resume matcher endpoint (deterministic, stateless)."""

from __future__ import annotations

import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request

from backend.schemas import MatchBatchRequest, MatchBatchResponse, MatchRequest, MatchResponse

router = APIRouter(prefix="/api/match", tags=["match"])

RATE_LIMIT = 60  # requests per minute per client IP
WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = {}


def _rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    # Evict stale IPs so _hits cannot grow unbounded.
    for stale_ip in [ip for ip, stamps in _hits.items() if not any(now - ts <= WINDOW_SECONDS for ts in stamps)]:
        del _hits[stale_ip]
    window = _hits.setdefault(client_ip, deque())
    while window and now - window[0] > WINDOW_SECONDS:
        window.popleft()
    if len(window) >= RATE_LIMIT:
        return True
    window.append(now)
    return False


@router.post("", response_model=MatchResponse)
def match(request: Request, payload: MatchRequest) -> MatchResponse:
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")

    from modules import jd_matcher

    try:
        result = jd_matcher.match_resume_to_job(
            list(payload.resume_skills or []),
            payload.job_id,
            resume_years=payload.resume_years,
            resume_title=payload.resume_title,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"job_id not found: {payload.job_id}")

    return MatchResponse(job_id=payload.job_id, **result)


@router.post("/batch", response_model=MatchBatchResponse)
def match_batch(request: Request, payload: MatchBatchRequest) -> MatchBatchResponse:
    """Score many postings in one request (fixes per-card N+1 fan-out).

    One batch counts as one rate-limit hit regardless of size.
    """
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")

    from modules import jd_matcher

    results: list[MatchResponse] = []
    for job_id in dict.fromkeys(str(jid) for jid in (payload.job_ids or [])):
        try:
            result = jd_matcher.match_resume_to_job(
                list(payload.resume_skills or []),
                job_id,
                resume_years=payload.resume_years,
                resume_title=payload.resume_title,
            )
        except KeyError:
            continue  # unknown ids are skipped; callers key results by job_id
        results.append(MatchResponse(job_id=job_id, **result))
    return MatchBatchResponse(results=results)