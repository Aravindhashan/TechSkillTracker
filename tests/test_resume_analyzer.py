import io

import pytest

from modules import resume_analyzer as ra


def make_postings():
    import pandas as pd

    rows = []
    skills = ["Python", "React", "Docker", "AWS", "SQL", "Kubernetes", "TypeScript"]
    for skill in skills:
        for _ in range(3):
            rows.append(
                {
                    "Job Title": "Dev",
                    "Tech Skill": skill,
                    "Company": "Acme",
                    "Location": "Bengaluru",
                    "Salary (in LPA)": 12.0 if skill in ("Python", "AWS") else None,
                    "Experience Required (in years)": 3.0,
                    "Date Posted": "2026-11-01",
                }
            )
    return pd.DataFrame(rows)


def test_extract_experience_years():
    assert ra.extract_experience_years("5 years of experience") == 5.0
    assert ra.extract_experience_years("3-5 years") == 4.0
    assert ra.extract_experience_years("10+ years") == 10.0
    assert ra.extract_experience_years("no experience mentioned") is None


def test_extract_education():
    edu = ra.extract_education("B.Tech in CS and MBA")
    assert "b.tech" in edu
    assert "mba" in edu


def test_analyze_resume_basic():
    df = make_postings()
    text = "Python developer with Docker and AWS experience. B.Tech degree."
    analysis = ra.analyze_resume(text, df)

    assert "Python" in analysis["resume_skills"]
    assert "Docker" in analysis["resume_skills"]
    assert "AWS" in analysis["resume_skills"]
    assert analysis["match_percentage"] > 0
    assert analysis["matched_skills"]  # at least one
    missing_names = [m["skill"] for m in analysis["missing_skills"]]
    assert "React" in missing_names
    assert "TypeScript" in missing_names

    # Missing skills sorted by demand descending
    demands = [m["demand"] for m in analysis["missing_skills"]]
    assert demands == sorted(demands, reverse=True)


def test_analyze_resume_empty_postings():
    import pandas as pd

    analysis = ra.analyze_resume("Python developer", pd.DataFrame())
    assert analysis["match_percentage"] == 0.0
    assert analysis["missing_skills"] == []
    assert analysis["total_postings"] == 0


def test_analyze_resume_no_skills():
    df = make_postings()
    analysis = ra.analyze_resume("Just a plain text resume with no tech skills.", df)
    assert analysis["resume_skills"] == []
    assert analysis["match_percentage"] == 0.0
    assert len(analysis["missing_skills"]) == len(analysis["demand_skills"])


def test_missing_skill_has_resources_and_salary():
    df = make_postings()
    text = "Python only"
    analysis = ra.analyze_resume(text, df)
    missing = {m["skill"]: m for m in analysis["missing_skills"]}
    assert "Python" not in missing
    assert "React" in missing
    assert missing["React"]["resources"]  # non-empty
    # Python and AWS have salary in the fixture
    assert missing["React"]["avg_salary"] is None or isinstance(missing["React"]["avg_salary"], float)


def test_extract_text_pdf():
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Skills: Python, Go")
    c.save()
    buf.seek(0)
    text = ra.extract_text(buf, "r.pdf")
    assert "Python" in text
    assert "Go" in text


def test_extract_text_docx():
    from docx import Document

    doc = Document()
    doc.add_paragraph("Skills: Rust, Kafka")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    text = ra.extract_text(buf, "r.docx")
    assert "Rust" in text
    assert "Kafka" in text


def test_save_report_handles_missing_store():
    analysis = ra.analyze_resume("Python", make_postings())
    # store module unavailable -> None, no crash
    rid = ra.save_report("r.pdf", analysis, store_module=None)
    # Either a real id (if a DB exists) or None — both acceptable
    assert rid is None or isinstance(rid, str)
