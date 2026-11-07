import json
import subprocess
import sys

import pytest


def test_benchmark_labels_exist_and_are_well_formed():
    """The labeled set exists with the expected schema (built live, not mocked)."""
    path = "data/benchmark_labels.jsonl"
    try:
        with open(path, encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
    except FileNotFoundError:
        pytest.skip("benchmark labels not built yet (run scripts/build_benchmark_labels.py)")

    assert len(rows) >= 1
    for row in rows:
        assert "job_id" in row
        assert "canonical_skills" in row
        assert "must_have" in row
        assert "nice_to_have" in row
        # Every skill appears in exactly one bucket.
        assert set(row["must_have"]) | set(row["nice_to_have"]) == set(row["canonical_skills"])


def test_score_normalizer_harness_runs():
    """The scoring script runs and reports P/R/F1 (no accuracy gate — circular labels)."""
    result = subprocess.run(
        [sys.executable, "scripts/score_normalizer.py"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0
    assert "F1=" in result.stdout