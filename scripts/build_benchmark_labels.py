"""Build the week-1 benchmark labeled set from the live store.

Writes `data/benchmark_labels.jsonl` — one row per posting that has a
description. Each row holds:
  - job_id, title, company, location
  - canonical_skills: from the store's `job_skills` (provisional — see below)
  - must_have / nice_to_have: split by section cues, else all skills unverified
  - years_required: parsed via ingestion.parse_experience_years

Provisional labels are derived from the store, NOT true hand-labels. The
scoring harness (`scripts/score_normalizer.py`) compares a fresh normalizer
run against them, so expect high agreement. Human review of the must/nice
split is still required before treating scores as ground truth.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MUST_CUE_RE = re.compile(
    r"(required|must have|essential|minimum qualifications|requirements?\s*:)",
    re.IGNORECASE,
)
NICE_CUE_RE = re.compile(
    r"(preferred|nice to have|bonus|plus|good to have|advantageous)",
    re.IGNORECASE,
)


def split_must_nice(description: str, skills: list[str]) -> tuple[list[str], list[str]]:
    """Split skills by section cues; default unknowns to must_have."""
    if not description:
        return list(skills), []
    must, nice = [], []
    lower = description.lower()
    for skill in skills:
        skill_lower = skill.lower()
        # Find first mention of the skill and look at surrounding context.
        idx = lower.find(skill_lower)
        window = lower[max(0, idx - 200): idx + 200] if idx >= 0 else ""
        if NICE_CUE_RE.search(window):
            nice.append(skill)
        elif MUST_CUE_RE.search(window):
            must.append(skill)
        else:
            # No cue near the mention: unverified -> must-have bucket.
            must.append(skill)
    return sorted(set(must)), sorted(set(nice))


def main() -> int:
    from modules import store
    from modules.ingestion import parse_experience_years

    rows = store.fetch_postings_with_skills(limit=100000)
    labelable = [row for row in rows if (row.get("description") or "").strip()]
    print(f"labelable={len(labelable)} of {len(rows)} postings "
          f"({len(rows) - len(labelable)} empty descriptions skipped)")

    out_path = Path(__file__).resolve().parent.parent / "data" / "benchmark_labels.jsonl"
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in labelable:
            description = row.get("description") or ""
            skills = list(row.get("skills") or [])
            must_have, nice_to_have = split_must_nice(description, skills)
            label = {
                "job_id": row.get("job_id"),
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "canonical_skills": skills,
                "must_have": must_have,
                "nice_to_have": nice_to_have,
                "years_required": parse_experience_years(description),
                "provisional": True,
            }
            handle.write(json.dumps(label, ensure_ascii=False) + "\n")

    print(f"wrote {out_path} ({len(labelable)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())