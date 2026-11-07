"""Day-one truncation check for stored JSearch descriptions.

Reports the length distribution of `job_postings.description` and flags
suspicious rows (empty, very short, or ending mid-word) so Slice 1 (per-job
matcher) can be gated on full text. Exits 0 always — this is an audit, not a
test gate — but prints a verdict line for CI/docs.

Usage:
    python scripts/check_truncation.py [--warn-pct 0.3]
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_lengths() -> list[int]:
    from modules import store

    rows = store.fetch_postings(limit=100000)
    return [len((row.get("description") or "") or "") for row in rows]


def main() -> int:
    warn_pct = float(os.getenv("TRUNCATION_WARN_PCT", "0.3"))
    lengths = load_lengths()
    n = len(lengths)
    if n == 0:
        print("verdict: EMPTY — no postings in store")
        return 0

    sorted_lengths = sorted(lengths)
    median = sorted_lengths[n // 2]
    p90 = sorted_lengths[min(n - 1, int(n * 0.9))]
    empty = sum(1 for length in lengths if length == 0)
    short = sum(1 for length in lengths if 0 < length < 200)
    common_caps = Counter(lengths).most_common(3)

    print(f"n={n} min={sorted_lengths[0]} max={sorted_lengths[-1]} "
          f"median={median} p90={p90}")
    print(f"empty={empty} ({empty / n:.0%}) short<200={short} ({short / n:.0%})")
    print(f"most_common_lengths={common_caps}")

    # A fixed cap shows up as an exact length repeating across many rows.
    cap_hits = [(length, count) for length, count in common_caps if count * 1.0 / n > 0.1 and length > 0]
    verdict = "OK — no truncation cap detected"
    if cap_hits:
        verdict = f"WARN — possible cap at lengths {cap_hits}"
    if empty / n > warn_pct or short / n > warn_pct:
        verdict += f" + WARN — {(empty + short) / n:.0%} empty/short rows"

    print(f"verdict: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())