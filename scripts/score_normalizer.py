"""Score SkillNormalizer against the benchmark labeled set.

Compares a fresh `SkillNormalizer.extract_skills_from_text()` run on each
labeled posting's stored description against `canonical_skills` from
`data/benchmark_labels.jsonl`. Prints per-posting precision/recall and the
overall micro-averaged P/R/F1. Exits 0 always (audit, not a CI gate).

Usage:
    python scripts/score_normalizer.py [--labels data/benchmark_labels.jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_labels(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score(labels: list[dict]) -> dict:
    from modules import store
    from modules.normalizer import SkillNormalizer

    by_id = {item.get("job_id"): item for item in store.fetch_postings(limit=100000)}
    normalizer = SkillNormalizer(load_model=False)

    tp = fp = fn = 0
    for label in labels:
        posting = by_id.get(label.get("job_id"))
        if not posting:
            continue
        text = posting.get("description") or ""
        predicted = {item["skill_canonical"] for item in normalizer.extract_skills_from_text(text)}
        expected = set(label.get("canonical_skills") or [])
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4),
            "recall": round(recall, 4), "f1": round(f1, 4)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Score normalizer vs benchmark labels")
    parser.add_argument("--labels", default="data/benchmark_labels.jsonl")
    args = parser.parse_args()

    labels = load_labels(args.labels)
    print(f"labels={len(labels)}")
    result = score(labels)
    print(f"tp={result['tp']} fp={result['fp']} fn={result['fn']} "
          f"P={result['precision']:.3f} R={result['recall']:.3f} F1={result['f1']:.3f}")
    print("note: provisional labels derive from the store, so expect high "
          "agreement — treat this as a regression harness, not ground truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())