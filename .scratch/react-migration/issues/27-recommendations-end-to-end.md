# 27: Skill Recommendations end-to-end

**What to build:** The Skill Recommendations tab working end to end in all three modes: complementary skills, role analysis, and learning roadmap.

**Blocked by:** 25 - Market Overview end-to-end.

**Status:** done

- [x] Complementary mode returns ranked skills from `POST /api/recommendations`
- [x] Role mode returns skill frequency/percentage from `POST /api/recommendations`
- [x] Learning-path mode returns prioritized missing skills from `POST /api/recommendations`
- [x] Empty/no-match result shows a status message with an empty list (200), not an error
- [x] At least one integration test covers each mode
