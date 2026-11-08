import pytest

from modules import jd_matcher


def test_split_must_nice_uses_section_cues():
    description = (
        "Required: Python, SQL. "
        "Bonus: LangChain is a plus. "
        "Preferred: PyTorch."
    )
    must, nice = jd_matcher.split_must_nice(description, ["Python", "SQL", "LangChain", "PyTorch"])
    assert "LangChain" in nice
    assert "PyTorch" in nice
    assert "Python" in must
    assert "SQL" in must


def test_split_must_nice_defaults_unknowns_to_must():
    must, nice = jd_matcher.split_must_nice("We need Python developers.", ["Python"])
    assert must == ["Python"]
    assert nice == []


def test_match_unknown_job_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "m.db"))
    from modules import store

    store.init_db()
    with pytest.raises(KeyError):
        jd_matcher.match_resume_to_job(["Python"], "no-such-job")


def test_match_scores_against_seeded_posting(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "m2.db"))
    from modules import store

    store.init_db()
    store.upsert_postings(
        [
            {
                "job_id": "job-1",
                "source": "jsearch",
                "title": "AI/ML Engineer",
                "company": "YMinds.AI",
                "location": "Chennai",
                "description": "Required: Python, PyTorch. Preferred: LangChain.",
                "url": "https://example.com/job",
                "employment_type": "FULLTIME",
                "is_remote": False,
                "experience_years": 5.0,
                "posted_at": "2026-11-07",
            }
        ],
        {
            "job-1": [
                {"skill_raw": "Python", "skill_canonical": "Python", "confidence": 1.0},
                {"skill_raw": "PyTorch", "skill_canonical": "PyTorch", "confidence": 1.0},
                {"skill_raw": "LangChain", "skill_canonical": "LangChain", "confidence": 1.0},
            ]
        },
    )

    result = jd_matcher.match_resume_to_job(["Python", "PyTorch"], "job-1", resume_years=3.0, resume_title="AI Engineer")
    # Must-haves fully covered (0.7) but LangChain (nice) missing (0.3 * 0).
    assert result["match_score"] == 70.0
    assert result["matched_skills"] == ["PyTorch", "Python"]
    assert result["missing_must_have"] == []
    assert result["missing_nice_to_have"] == ["LangChain"]
    assert result["experience_gap"] == 2.0
    assert result["title_similarity"] is not None
    assert result["posting_health"] == "active"
    assert result["confidence"] == "high"

    partial = jd_matcher.match_resume_to_job(["Python"], "job-1")
    assert partial["missing_must_have"] == ["PyTorch"]
    assert partial["match_score"] < result["match_score"]