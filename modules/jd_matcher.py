"""Deterministic per-job resume matcher (Slice 1).

Compares a resume's canonical skills against one stored posting and returns a
weighted coverage score. No LLM, no network, no DB writes — the caller owns
persistence. Empty descriptions degrade to title/skills-only matching with a
low-confidence flag (see FINAL_IMPLEMENTATION_PLAN.md Phase 0 gate).

Score = weighted coverage (must-haves heaviest):
    0.7 * must_coverage + 0.3 * nice_coverage
(normalized to 0–100). When the posting has no must-haves, the must term
counts as fully covered; same for nice-to-haves.
"""

from __future__ import annotations

import difflib

from modules.ingestion import parse_experience_years

MUST_WEIGHT = 0.7
NICE_WEIGHT = 0.3

MUST_CUE = ("required", "must have", "essential", "minimum qualifications", "requirements")
NICE_CUE = ("preferred", "nice to have", "bonus", "plus", "good to have", "advantageous", "optional")


def _canonicalize(skills: list[str]) -> set[str]:
    from modules.normalizer import SkillNormalizer

    normalizer = SkillNormalizer(load_model=False)
    return {result.canonical for result in normalizer.normalize_many(skills or []) if result.canonical}


def _cue_sections(description: str) -> list[tuple[int, str]]:
    """Locate cue keywords with positions, sorted by position."""
    lower = (description or "").lower()
    hits: list[tuple[int, str]] = []
    for cue in MUST_CUE + NICE_CUE:
        start = 0
        while True:
            index = lower.find(cue, start)
            if index < 0:
                break
            kind = "nice" if cue in NICE_CUE else "must"
            hits.append((index, kind))
            start = index + len(cue)
    hits.sort()
    return hits


def _skill_index(lower: str, skill: str) -> int:
    """First boundary-delimited occurrence of `skill` (never inside a longer word).

    Mirrors the normalizer's boundary rule so "Java" never matches inside
    "JavaScript".
    """
    import re

    pattern = re.compile(
        rf"(?<![A-Za-z0-9+#/]){re.escape(skill.lower())}(?![A-Za-z0-9+#/&])",
        re.IGNORECASE,
    )
    match = pattern.search(lower)
    return match.start() if match else -1


def split_must_nice(
    description: str, job_skills: list[str]
) -> tuple[list[str], list[str]]:
    """Split canonical skills into must-have vs nice-to-have by section cues.

    Each skill takes the kind of the nearest preceding cue (within 300 chars);
    skills with no preceding cue default to must-have (unverified).
    """
    must: list[str] = []
    nice: list[str] = []
    lower = (description or "").lower()
    sections = _cue_sections(description)
    for skill in sorted(set(job_skills)):
        index = _skill_index(lower, skill)
        kind = "must"  # unverified default
        if index >= 0:
            preceding = [hit for hit in sections if hit[0] <= index and index - hit[0] <= 300]
            if preceding:
                kind = preceding[-1][1]
        (nice if kind == "nice" else must).append(skill)
    return must, nice


def _posting_by_id(job_id: str) -> dict | None:
    from modules import store

    postings = store.fetch_postings_with_skills()
    for posting in postings:
        if str(posting.get("job_id")) == str(job_id):
            return posting
    return None


def match_resume_to_job(
    resume_skills: list[str],
    job_id: str,
    resume_years: float | None = None,
    resume_title: str | None = None,
) -> dict:
    """Score a resume against one posting. Raises KeyError for unknown jobs.

    Returns {match_score, matched_skills, missing_must_have,
    missing_nice_to_have, experience_gap, title_similarity, posting_health,
    confidence}.
    """
    posting = _posting_by_id(job_id)
    if posting is None:
        raise KeyError(f"job_id not found: {job_id}")

    resume_canonical = _canonicalize(list(resume_skills or []))
    job_skills = list(posting.get("skills") or [])
    description = posting.get("description") or ""

    must_have, nice_to_have = split_must_nice(description, job_skills)

    matched = sorted(resume_canonical & set(job_skills))
    missing_must = sorted(set(must_have) - resume_canonical)
    missing_nice = sorted(set(nice_to_have) - resume_canonical)

    # Weights renormalize over non-empty buckets so an empty nice-to-have
    # bucket does not hand out free points (empty resume must score 0).
    buckets = []
    weights = []
    if must_have:
        buckets.append(len(set(must_have) & resume_canonical) / len(must_have))
        weights.append(MUST_WEIGHT)
    if nice_to_have:
        buckets.append(len(set(nice_to_have) & resume_canonical) / len(nice_to_have))
        weights.append(NICE_WEIGHT)
    weighted = (
        sum(bucket * weight for bucket, weight in zip(buckets, weights)) / sum(weights)
        if buckets
        else 0.0
    )
    match_score = round(weighted * 100, 1)

    required_years = posting.get("experience_years")
    if required_years is None:
        required_years = parse_experience_years(description)
    experience_gap = (
        round(float(required_years) - float(resume_years), 1)
        if required_years is not None and resume_years is not None
        else None
    )

    job_title = posting.get("title") or ""
    title_similarity = (
        round(difflib.SequenceMatcher(None, (resume_title or "").lower(), job_title.lower()).ratio(), 3)
        if resume_title
        else None
    )

    is_active = bool(posting.get("is_active"))
    posting_health = "active" if is_active else "closed"
    confidence = "low" if not description.strip() else ("high" if must_have else "medium")

    try:
        from modules import ghost_risk

        risk = ghost_risk.ghost_risk_score(
            str(posting.get("job_id")),
            first_seen=posting.get("first_seen"),
            last_seen=posting.get("last_seen"),
            is_active=is_active,
        )
        ghost = {"risk": risk["risk"], "label": risk["label"]}
    except Exception:
        ghost = None

    return {
        "match_score": match_score,
        "matched_skills": matched,
        "missing_must_have": missing_must,
        "missing_nice_to_have": missing_nice,
        "experience_gap": experience_gap,
        "title_similarity": title_similarity,
        "posting_health": posting_health,
        "confidence": confidence,
        "ghost_risk": ghost,
    }