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

SENTENCE_END = (".", "!", "?", '"', ")", "]", ";")


def load_rows() -> list[dict]:
    from modules import store

    return store.fetch_postings(limit=100000)


def _ends_mid_word(description: str) -> bool:
    """True when a long description ends mid-word (no sentence punctuation)."""
    text = (description or "").strip()
    if len(text) < 500:
        return False
    last = text[-1]
    return last.isalnum() and last not in SENTENCE_END


def main() -> int:
    warn_pct = float(os.getenv("TRUNCATION_WARN_PCT", "0.3"))
    rows = load_rows()
    descriptions = [str(row.get("description") or "") for row in rows]
    lengths = [len(text) for text in descriptions]
    n = len(lengths)
    if n == 0:
        print("verdict: EMPTY — no postings in store")
        return 0

    sorted_lengths = sorted(lengths)
    median = sorted_lengths[n // 2]
    p90 = sorted_lengths[min(n - 1, int(n * 0.9))]
    empty = sum(1 for text in descriptions if not text.strip())
    short = sum(1 for length in lengths if length < 200)  # includes empties
    mid_word = sum(1 for text in descriptions if _ends_mid_word(text))
    common_caps = Counter(lengths).most_common(3)

    print(f"n={n} min={sorted_lengths[0]} max={sorted_lengths[-1]} "
          f"median={median} p90={p90}")
    print(f"empty={empty} ({empty / n:.0%}) short<200={short} ({short / n:.0%}) mid_word={mid_word} ({mid_word / n:.0%})")
    print(f"most_common_lengths={common_caps}")

    # A fixed cap shows up as an exact length repeating across many rows.
    cap_hits = [(length, count) for length, count in common_caps if count * 1.0 / n > 0.1 and length > 0]
    verdict = "OK — no truncation cap detected"
    if cap_hits:
        verdict = f"WARN — possible cap at lengths {cap_hits}"
    if empty / n > warn_pct or short / n > warn_pct:
        verdict += f" + WARN — {short / n:.0%} empty/short rows"
    if mid_word / n > 0.1:
        verdict += f" + WARN — {mid_word / n:.0%} end mid-word"

    print(f"verdict: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())