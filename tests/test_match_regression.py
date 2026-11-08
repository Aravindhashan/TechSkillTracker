"""Labeled-set regression for the per-job matcher (Slice 1, ticket 38).

Self-match regression: scoring a posting against its own canonical skills
must always yield 100 — any drop here means the scorer or the cue split
broke. Uses the week-1 benchmark set (`data/benchmark_labels.jsonl`).
"""

import json
from pathlib import Path

import pytest

from modules import jd_matcher

LABELS_PATH = Path("data/benchmark_labels.jsonl")


def _load_labels() -> list[dict]:
    if not LABELS_PATH.exists():
        pytest.skip("benchmark labels not built yet (run scripts/build_benchmark_labels.py)")
    rows = []
    with LABELS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_self_match_is_perfect_on_first_ten_labels():
    # Rows with zero extracted skills score 0 (vacuous) — skip those; the
    # regression is about non-empty postings matching themselves.
    labels = [row for row in _load_labels() if row["canonical_skills"]][:10]
    assert labels, "no labelable rows"
    for label in labels:
        result = jd_matcher.match_resume_to_job(label["canonical_skills"], label["job_id"])
        assert result["match_score"] == 100.0
        assert result["missing_must_have"] == []
        assert result["posting_health"] == "active"


def test_empty_resume_scores_zero_and_lists_must_haves():
    labels = _load_labels()
    assert labels
    label = labels[0]
    result = jd_matcher.match_resume_to_job([], label["job_id"])
    assert result["match_score"] == 0.0
    assert result["missing_must_have"] == label["must_have"]