# 13: Resume skill-gap (PDF/DOCX → extract → match % + missing skills)

**What to build:** Upload a PDF or DOCX resume, extract text, parse skills/experience/education, score match against live postings, and return a ranked list of missing skills by market demand and salary.

**Blocked by:** 09 (data ingestion and Postgres store)

**Status:** implemented (2026-11-07)

- [x] PDF/DOCX text extraction (pdfplumber + python-docx)
- [x] Extract skills, experience years, education from resume text
- [x] Normalize extracted skills via taxonomy (from 09)
- [x] Score match % against live posting demand
- [x] Rank missing skills by demand (frequency) and salary
- [x] Streamlit UI: upload widget → report card with match % + missing skills + learning resources

**Implemented by:** `modules/resume_analyzer.py`, `tests/test_resume_analyzer.py`, and the "Resume Analysis" tab in `app.py`.

**Notes:** Match % is coverage of distinct in-demand skills; a weighted variant (by posting frequency) is also shown. Missing skills are ranked by demand, then salary where available. Reports are persisted to the store when it is available.
