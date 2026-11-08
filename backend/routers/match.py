"""Per-job resume matcher endpoint (deterministic, stateless)."""

from __future__ import annotations

import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request

from backend.schemas import MatchRequest, MatchResponse

router = APIRouter(prefix="/api/match", tags=["match"])

RATE_LIMIT = 60  # requests per minute per client IP
WINDOW_SECONDS = 60
_hits: dict[str, deque[float]] = {}


def _rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    window = _hits.setdefault(client_ip, deque())
    while window and now - window[0] > WINDOW_SECONDS:
        window.popleft()
    if not window and client_ip in _hits:
        del _hits[client_ip]  # evict stale IPs so _hits cannot grow unbounded
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