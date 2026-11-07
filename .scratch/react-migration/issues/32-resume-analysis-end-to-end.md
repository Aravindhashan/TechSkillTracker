# 32: Resume Analysis end-to-end

**What to build:** The Resume Analysis tab working end to end: PDF/DOCX upload, match metrics, and missing-skills table with learning resources.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] File upload accepts PDF and DOCX via `POST /api/resume/analyze`
- [x] Skill-gap report renders match metrics and missing skills ranked by demand with learning resources
- [x] Unsupported file types return 415 and unparseable files return 422 (verified end to end)
- [x] Matched-skills section renders skills already covered
- [x] At least one integration test covers PDF and DOCX upload
