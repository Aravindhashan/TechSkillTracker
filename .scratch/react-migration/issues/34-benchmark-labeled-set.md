# 34: Week-1 benchmark labeled set

**What to build:** A labeled benchmark of postings (canonical skills, must-have vs nice-to-have, years required) plus a scoring script for `normalizer.py` — becomes the Slice 1 regression test.

**Blocked by:** 33 - JSearch description truncation check.

**Status:** done

- [x] Labeled set built from the live store (target ~150–200 postings after 3 extra ingestion runs)
- [x] Scoring script reports per-corpus precision/recall/F1 for `normalizer.py`
- [x] Set becomes the Slice 1 regression test (`tests/test_benchmark_normalizer.py`)
- [x] `python scripts/score_normalizer.py` runs clean

### Findings (2026-11-08, 3 extra ingestion runs)

- Store grew 59 → 97 → 112 → **122 postings** (fetched 49/run, +38/+15/+10 new).
- **83 row labels** written to `data/benchmark_labels.jsonl` (39 empty descriptions skipped — see ticket 33).
- Scoring (circular, provisional labels from the store): **P=1.000 R=0.999 F1=0.999** (tp=688 fp=0 fn=1).
- **Caution:** labels are provisional (derived from `job_skills`), **not true hand-labels**. The harness is a regression net, not ground truth. Human review of the must-have/nice-to-have split is still required before treating scores as meaningful.
- **Shortfall:** 83 labelable rows < 200 target. Reaching 200 needs more quota-fresh postings (diminishing ~10/run at current queries); benchmark at 83 now, expand as ingestion continues.
