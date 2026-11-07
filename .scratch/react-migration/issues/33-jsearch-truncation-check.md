# 33: JSearch description truncation check

**What to build:** A day-one check comparing stored JSearch description lengths and flagging cut-off text — gates the per-job matcher (Slice 1) because must-have detection and experience parsing depend on full text.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] Script reports description-length distribution (n, min, max, median, p90, empty count)
- [x] Script flags suspicious short/cut-off descriptions with a warning, not a crash
- [x] `docs` findings recorded in this ticket (or a short note) with the gate verdict
- [x] `python scripts/check_truncation.py` runs clean on the live store

### Findings (live store, 2026-11-07)

```text
n=59 min=0 max=6605 median=2525 p90=5236
empty=19 (32%) short<200=0 (0%)
most_common_lengths=[(0, 19), (3997, 2), (4038, 2)]
verdict: OK — no truncation cap detected + WARN — 32% empty/short rows
```

**Verdict:** No fixed-cap truncation (lengths vary widely; longest 6605 chars — likely full text). **Gate passes with a warning:** 19/59 postings (32%) have *no* description at all. Slice 1 must handle empty descriptions gracefully (title/skills-only match + low-confidence flag) rather than failing the experience emphasis parse.
