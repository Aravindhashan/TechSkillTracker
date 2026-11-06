"""Resume parsing and skill-gap analysis.

Extracts text from a PDF or DOCX resume, pulls out skills/experience/education,
and scores the resume against live job postings: a match percentage plus the
top missing skills ranked by market demand (and salary where available).
"""

from __future__ import annotations

import io
import re
from collections import Counter, defaultdict
from typing import Any, BinaryIO

import pandas as pd

from modules.learning_resources import get_learning_resources
from modules.normalizer import SkillNormalizer

DEGREE_KEYWORDS = [
    "b.tech", "btech", "b.e", "be ", "b.sc", "bsc", "b.com", "bcom",
    "bca", "bachelor", "m.tech", "mtech", "m.e", "me ", "m.sc", "msc",
    "m.com", "mcom", "mca", "master", "mba", "phd", "ph.d", "doctorate",
    "diploma", "associate",
]

EXPERIENCE_RE = re.compile(
    r"(\d{1,2})\s*(?:\+|\bplus\b)?\s*(?:-|to|–)?\s*(\d{1,2})?\s*(?:\+)?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)

# Rough section headers we recognise; used to bound experience/education search.
SECTION_HEADERS = re.compile(
    r"(?im)^(experience|work experience|professional experience|employment|"
    r"education|academic|qualifications|skills|technical skills|core competencies)\s*[:\-]?\s*$"
)


def _to_file_like(file: Any) -> Any:
    if isinstance(file, (bytes, bytearray)):
        return io.BytesIO(file)
    return file


def extract_text_from_pdf(file: Any) -> str:
    import pdfplumber

    text_parts: list[str] = []
    handle = _to_file_like(file)
    with pdfplumber.open(handle) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file: Any) -> str:
    from docx import Document

    handle = _to_file_like(file)
    document = Document(handle)
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def extract_text(file: Any, filename: str | None = None) -> str:
    name = (filename or getattr(file, "name", "") or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    if name.endswith(".docx"):
        return extract_text_from_docx(file)
    # Fall back to treating the payload as plain text.
    handle = _to_file_like(file)
    data = handle.read() if hasattr(handle, "read") else file
    if isinstance(data, (bytes, bytearray)):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return str(data)


def extract_experience_years(text: str) -> float | None:
    if not text:
        return None
    match = EXPERIENCE_RE.search(text)
    if not match:
        return None
    low = float(match.group(1))
    high = float(match.group(2)) if match.group(2) else low
    if high < low:
        low, high = high, low
    if high > 40:
        return None
    return round((low + high) / 2, 1)


def extract_education(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    found: list[str] = []
    for keyword in DEGREE_KEYWORDS:
        if keyword in lowered and keyword not in found:
            found.append(keyword)
    # Dedupe case-insensitively while preserving order.
    seen: set[str] = set()
    result: list[str] = []
    for item in found:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _skill_demand(postings_df: pd.DataFrame) -> Counter:
    """Return skill -> posting count from postings."""
    if postings_df is None or postings_df.empty:
        return Counter()

    counts: Counter = Counter()

    for _, row in postings_df.iterrows():
        skill = str(row.get("Tech Skill", "")).strip()
        if not skill or skill.lower() == "nan":
            continue
        counts[skill] += 1

    return counts


def analyze_resume(
    text: str,
    postings_df: pd.DataFrame,
    normalizer: SkillNormalizer | None = None,
) -> dict[str, Any]:
    """Analyse a resume against live postings.

    Returns a dict with:
      - ``resume_skills``: canonical skills found in the resume
      - ``experience_years``: best-effort years of experience
      - ``education``: degree keywords found
      - ``demand_skills``: distinct skills in demand
      - ``matched_skills``: in-demand skills the resume covers
      - ``missing_skills``: in-demand skills the resume lacks, ranked by demand
      - ``match_percentage``: coverage of distinct in-demand skills
      - ``weighted_match_percentage``: coverage weighted by posting frequency
      - ``total_postings``: number of postings analysed
    """
    normalizer = normalizer or SkillNormalizer(load_model=False)

    extracted = normalizer.extract_skills_from_text(text or "")
    resume_canonical = {item["skill_canonical"] for item in extracted}
    resume_raw = {item["skill_raw"]: item["skill_canonical"] for item in extracted}

    counts = _skill_demand(postings_df)
    demand_skills = set(counts)

    matched = sorted(resume_canonical & demand_skills)
    missing_raw = sorted(demand_skills - resume_canonical, key=lambda skill: (-counts[skill],))

    missing_details: list[dict[str, Any]] = []
    total_demand = sum(counts.values()) or 1
    for skill in missing_raw:
        missing_details.append(
            {
                "skill": skill,
                "demand": int(counts[skill]),
                "percentage": round(counts[skill] / len(postings_df) * 100, 1)
                if postings_df is not None and not postings_df.empty
                else 0.0,
                "resources": get_learning_resources(skill),
            }
        )

    match_pct = (
        round(len(matched) / len(demand_skills) * 100, 1) if demand_skills else 0.0
    )
    weighted = (
        round(
            sum(counts[skill] for skill in matched) / total_demand * 100,
            1,
        )
        if demand_skills
        else 0.0
    )

    return {
        "resume_skills": sorted(resume_canonical),
        "resume_skill_details": [
            {"raw": raw, "canonical": canonical}
            for raw, canonical in sorted(resume_raw.items())
        ],
        "experience_years": extract_experience_years(text or ""),
        "education": extract_education(text or ""),
        "demand_skills": sorted(demand_skills),
        "matched_skills": matched,
        "missing_skills": missing_details,
        "match_percentage": match_pct,
        "weighted_match_percentage": weighted,
        "total_postings": len(postings_df) if postings_df is not None else 0,
        "total_demand_skills": len(demand_skills),
    }


def save_report(
    filename: str,
    analysis: dict[str, Any],
    store_module=None,
) -> str | None:
    """Persist an analysis to the store; returns the resume_id or None."""
    if store_module is None:
        try:
            from modules import store as store_module
        except Exception:
            return None
    try:
        return store_module.save_resume_report(
            filename=filename,
            extracted_skills=analysis.get("resume_skills", []),
            experience_years=analysis.get("experience_years"),
            education=", ".join(analysis.get("education", [])) or None,
            report=analysis,
        )
    except Exception:
        return None
