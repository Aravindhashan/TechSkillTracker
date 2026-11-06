import pandas as pd

from modules import skill_roi


def _row(job_id, skill, month, title, location="Bengaluru", experience=3.0):
    return {
        "Job ID": job_id,
        "Job Title": title,
        "Tech Skill": skill,
        "Company": "Acme",
        "Location": location,
        "Experience Required (in years)": experience,
        "Date Posted": f"2024-{month:02d}-15",
    }


def _growing_frame():
    rows = []
    for month in range(1, 9):
        # Python demand grows by 2 postings/month; React stays flat.
        for index in range(4 + 2 * month):
            rows.append(_row(f"py-{month}-{index}", "Python", month, "Backend Engineer"))
        for index in range(4):
            rows.append(_row(f"re-{month}-{index}", "React", month, "Frontend Engineer"))
    return pd.DataFrame(rows)


def test_compute_skill_roi_returns_ranked_rows():
    result = skill_roi.compute_skill_roi(_growing_frame())

    assert result
    assert {"skill", "demand", "share_pct", "momentum", "roi_score", "confidence"}.issubset(
        result[0]
    )
    assert result[0]["skill"] == "Python"


def test_growing_skill_has_positive_momentum():
    result = skill_roi.compute_skill_roi(_growing_frame())
    python = next(row for row in result if row["skill"] == "Python")

    assert python["momentum"] > 0


def test_roi_output_contains_no_salary_terms():
    result = skill_roi.compute_skill_roi(_growing_frame())

    for row in result:
        assert not any("salary" in key.lower() for key in row)


def test_empty_frame_returns_empty_list():
    assert skill_roi.compute_skill_roi(pd.DataFrame()) == []


def test_single_posting_is_low_confidence():
    frame = pd.DataFrame([_row("job-1", "Python", 1, "Backend Engineer")])

    result = skill_roi.compute_skill_roi(frame)

    assert result
    assert result[0]["confidence"] == "low"
