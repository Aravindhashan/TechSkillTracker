"""Ghost-risk estimate from posting lifecycle events (Slice 3).

Deterministic, no LLM: blends posting age, stale-close, and repost behavior
into a 0–1 risk score. Labeled "estimated risk" — a heuristic over this
store's history, not a prediction about any employer's system.
"""

from __future__ import annotations

from datetime import datetime, timezone

WEIGHTS = {"age": 0.3, "closed": 0.4, "repost": 0.2, "stale_seen": 0.1}


def _age_days(first_seen: str | None, now: datetime) -> float:
    if not first_seen:
        return 0.0
    try:
        first = datetime.fromisoformat(str(first_seen).replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return max(0.0, (now - first).total_seconds() / 86400.0)


def ghost_risk_score(
    job_id: str,
    first_seen: str | None = None,
    last_seen: str | None = None,
    is_active: bool = True,
    now: datetime | None = None,
) -> dict:
    """Estimate ghost risk for one posting from its event history.

    Returns {risk (0–1), label (low|medium|high), factors{...}} where higher
    risk means more likely stale/ghosted.
    """
    from modules import store

    moment = now or datetime.now(timezone.utc)
    events = store.fetch_posting_events(job_id)
    types = [str(event.get("event_type")) for event in events]
    repost_count = types.count("reposted")
    closed = "closed" in types or not bool(is_active)

    age = _age_days(first_seen, moment)
    stale_seen = 0.0
    if last_seen:
        try:
            seen = datetime.fromisoformat(str(last_seen).replace("Z", "+00:00"))
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)
            stale_seen = 1.0 if (moment - seen).total_seconds() / 86400.0 > 14 else 0.0
        except ValueError:
            stale_seen = 0.0

    factors = {
        "age": round(min(age / 30.0, 1.0), 3),
        "closed": 1.0 if closed else 0.0,
        "repost": round(min(repost_count / 2.0, 1.0), 3),
        "stale_seen": stale_seen,
    }
    risk = sum(WEIGHTS[key] * factors[key] for key in WEIGHTS)
    risk = round(min(max(risk, 0.0), 1.0), 3)
    label = "low" if risk < 0.3 else ("medium" if risk < 0.6 else "high")

    return {"risk": risk, "label": label, "factors": factors}