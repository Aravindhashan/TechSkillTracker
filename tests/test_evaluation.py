import pandas as pd

from modules import evaluation as ev
from modules.semantic_search import SemanticSearchEngine


def _row(job_id, skill, date="2024-06-15"):
    return {
        "Job ID": job_id,
        "Job Title": f"{skill} Engineer",
        "Tech Skill": skill,
        "Company": "Acme",
        "Location": "Bengaluru",
        "Experience Required (in years)": 3.0,
        "Date Posted": date,
    }


def _frame(postings):
    rows = []
    for job_id, skills, date in postings:
        for skill in skills:
            rows.append(_row(job_id, skill, date))
    return pd.DataFrame(rows)


def _toy_frame():
    # Python+SQL co-occur in train; train split must not leak test postings.
    return _frame(
        [
            ("train-1", ["Python", "SQL"], "2024-01-15"),
            ("train-2", ["Python", "SQL"], "2024-02-15"),
            ("train-3", ["React", "TypeScript"], "2024-03-15"),
            ("train-4", ["React", "TypeScript"], "2024-04-15"),
            ("test-1", ["Python", "SQL"], "2024-11-15"),
            ("test-2", ["Python", "SQL"], "2024-12-15"),
        ]
    )


# -- metric primitives -------------------------------------------------------


def test_precision_and_recall_at_k():
    assert ev.precision_at_k(["a", "b", "c"], {"a", "c"}, 2) == 0.5
    assert ev.recall_at_k(["a", "b", "c"], {"a", "c"}, 2) == 0.5
    assert ev.precision_at_k([], {"a"}, 3) == 0.0


def test_ndcg_prefers_relevant_first():
    ranked_good = ev.ndcg_at_k(["a", "b"], {"a"}, 2)
    ranked_bad = ev.ndcg_at_k(["b", "a"], {"a"}, 2)

    assert ranked_good == 1.0
    assert ranked_bad < ranked_good


def test_ndcg_accepts_graded_relevance():
    score = ev.ndcg_at_k(["b", "a"], {"a": 0.5, "b": 1.0}, 2)

    assert score == 1.0  # strongest gain first is ideal


# -- splits ------------------------------------------------------------------


def test_temporal_split_holds_out_latest_postings():
    train, test = ev.split_dataframe(_toy_frame(), 0.33, "temporal")

    assert set(test["Job ID"]) == {"test-1", "test-2"} or "test-1" in set(test["Job ID"])
    assert not set(train["Job ID"]) & set(test["Job ID"])  # no leakage


def test_random_split_is_seeded_and_leak_free():
    frame = _toy_frame()
    train_a, test_a = ev.split_dataframe(frame, 0.33, "random", seed=7)
    train_b, test_b = ev.split_dataframe(frame, 0.33, "random", seed=7)

    assert set(test_a["Job ID"]) == set(test_b["Job ID"])
    assert not set(train_a["Job ID"]) & set(test_a["Job ID"])


def test_split_records_temporal_uses_posted_at():
    records = [
        {"job_id": f"job-{index}", "posted_at": f"2024-{index:02d}-15"}
        for index in range(1, 11)
    ]

    train, test = ev.split_records(records, 0.2, "temporal")

    assert [record["job_id"] for record in test] == ["job-9", "job-10"]
    assert len(train) == 8


# -- recommender evaluation --------------------------------------------------


def test_recommender_holdout_recovers_strong_pair():
    result = ev.evaluate_recommendations_holdout(
        _toy_frame(), test_fraction=0.33, strategy="temporal", top_n=5, ks=(1, 3)
    )

    # In test, Python co-occurs with SQL, which the train split also pairs.
    assert result["n_queries"] >= 2
    assert result["precision@1"] > 0
    assert result["ndcg@1"] > 0


def test_recommender_evaluation_with_injected_stub():
    def stub(df, skill, top_n=5):
        if skill == "Python":
            return [{"skill": "SQL"}], "success"
        return [], "No strong skill associations found"

    result = ev.evaluate_recommendations_holdout(
        _toy_frame(),
        test_fraction=0.33,
        strategy="temporal",
        top_n=5,
        ks=(1,),
        recommender=stub,
    )

    # One of the two test skills is covered, so coverage is 1/2.
    assert result["coverage"] == 0.5


def test_empty_frame_returns_zero_metrics():
    result = ev.evaluate_recommendations_holdout(pd.DataFrame())

    assert result["n_queries"] == 0
    assert result["precision@1"] == 0.0


# -- semantic search evaluation ----------------------------------------------


class _WordEmbedder:
    """Bag-of-words embedder so search eval never downloads a model."""

    vocab = {"python": 0, "sql": 1, "react": 2, "typescript": 3}

    def __call__(self, texts):
        import numpy as np

        matrix = np.zeros((len(texts), len(self.vocab)), dtype="float32")
        for row, text in enumerate(texts):
            lowered = text.lower()
            for token, column in self.vocab.items():
                if token in lowered:
                    matrix[row, column] += 1.0
        return matrix


_SEARCH_RECORDS = [
    {"job_id": "train-1", "title": "Python Engineer", "skills": ["Python", "SQL"],
     "posted_at": "2024-01-15", "description": "python sql work"},
    {"job_id": "train-2", "title": "Python Engineer", "skills": ["Python", "SQL"],
     "posted_at": "2024-02-15", "description": "python sql work"},
    {"job_id": "train-3", "title": "React Engineer", "skills": ["React", "TypeScript"],
     "posted_at": "2024-03-15", "description": "react typescript work"},
    {"job_id": "train-4", "title": "Python Engineer", "skills": ["Python", "SQL"],
     "posted_at": "2024-04-15", "description": "python sql work"},
    {"job_id": "test-1", "title": "Python Engineer", "skills": ["Python", "SQL"],
     "posted_at": "2024-11-15", "description": "python sql work"},
    {"job_id": "test-2", "title": "React Engineer", "skills": ["React", "TypeScript"],
     "posted_at": "2024-12-15", "description": "react typescript work"},
]


def test_search_holdout_scores_matching_retrieval():
    result = ev.evaluate_search_holdout(
        _SEARCH_RECORDS, embedder=_WordEmbedder(), test_fraction=0.33, top_k=3, ks=(1,)
    )

    assert result["n_queries"] == 2
    assert result["precision@1"] > 0
    assert result["ndcg@1"] > 0


def test_evaluate_search_with_lexical_engine():
    train, test = ev.split_records(_SEARCH_RECORDS, 0.33, "temporal")
    engine = SemanticSearchEngine(embedder=None, allow_models=False)
    engine.build(train)

    result = ev.evaluate_search(engine, test, train, top_k=3, ks=(1,))

    assert result["n_queries"] == 2
    assert result["precision@1"] > 0


def test_search_evaluation_empty_inputs():
    engine = SemanticSearchEngine(embedder=_WordEmbedder())
    engine.build([])

    assert ev.evaluate_search(engine, [], [], ks=(1,))["n_queries"] == 0
    assert ev.evaluate_search_holdout([], embedder=_WordEmbedder())["n_queries"] == 0
