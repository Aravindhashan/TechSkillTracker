import numpy as np

from modules import semantic_search as ss


RECORDS = [
    {
        "job_id": "python-job",
        "title": "Python Data Engineer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Build python data pipelines with sql and airflow.",
        "skills": ["Python", "SQL", "Airflow"],
        "posted_at": "2026-11-01",
    },
    {
        "job_id": "react-job",
        "title": "React Frontend Engineer",
        "company": "Beta",
        "location": "Remote",
        "description": "Build react frontend experiences with typescript.",
        "skills": ["React", "TypeScript"],
        "posted_at": "2026-11-02",
    },
    {
        "job_id": "k8s-job",
        "title": "Platform Engineer",
        "company": "Gamma",
        "location": "Hyderabad",
        "description": "Operate kubernetes clusters and docker workloads.",
        "skills": ["Kubernetes", "Docker"],
        "posted_at": "2026-10-28",
    },
    {
        "job_id": "ml-job",
        "title": "Machine Learning Engineer",
        "company": "Delta",
        "location": "Pune",
        "description": "Train python machine learning models with pandas.",
        "skills": ["Python", "Pandas", "Machine Learning"],
        "posted_at": "2026-10-20",
    },
]


class FakeEmbedder:
    """Deterministic bag-of-words embedder so tests never download a model."""

    vocab = {
        "python": 0,
        "data": 1,
        "react": 2,
        "frontend": 3,
        "sql": 4,
        "kubernetes": 5,
        "docker": 6,
        "machine": 7,
        "learning": 8,
        "typescript": 9,
    }

    def __init__(self):
        self.calls = 0

    def __call__(self, texts):
        self.calls += 1
        matrix = np.zeros((len(texts), len(self.vocab)), dtype="float32")
        for row, text in enumerate(texts):
            lowered = text.lower()
            for token, column in self.vocab.items():
                if token in lowered:
                    matrix[row, column] += 1.0
        return matrix


def _engine(tmp_path, **kwargs):
    return ss.SemanticSearchEngine(cache_path=tmp_path / "index.npz", **kwargs)


def test_semantic_search_ranks_matching_record_first(tmp_path):
    engine = _engine(tmp_path, embedder=FakeEmbedder(), allow_models=False)
    engine.build(RECORDS)

    results = engine.search("python data", top_k=2, rerank=False)

    assert results[0]["job_id"] == "python-job"
    assert results[0]["score"] >= results[1]["score"]


def test_lexical_fallback_when_embeddings_unavailable(tmp_path):
    engine = _engine(tmp_path, embedder=None, allow_models=False)
    engine.build(RECORDS)

    results = engine.search("kubernetes", top_k=1)

    assert results[0]["job_id"] == "k8s-job"


def test_reranker_can_reorder_candidates(tmp_path):
    class FakeReranker:
        def predict(self, pairs):
            return [1.0 if "react" in document.lower() else 0.0 for _, document in pairs]

    engine = _engine(
        tmp_path,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(),
        allow_models=False,
    )
    engine.build(RECORDS)

    results = engine.search("frontend engineer", top_k=2, rerank=True)

    assert results[0]["job_id"] == "react-job"


def test_empty_corpus_returns_no_results(tmp_path):
    engine = _engine(tmp_path, embedder=FakeEmbedder(), allow_models=False)
    engine.build([])

    assert engine.search("python") == []


def test_embeddings_are_cached_between_builds(tmp_path):
    embedder = FakeEmbedder()
    engine = _engine(tmp_path, embedder=embedder, allow_models=False)

    engine.build(RECORDS)
    calls_after_first_build = embedder.calls

    second = _engine(tmp_path, embedder=embedder, allow_models=False)
    second.build(RECORDS)

    assert (tmp_path / "index.npz").exists()
    assert embedder.calls == calls_after_first_build  # cache hit, no re-embedding
    assert second.search("sql", top_k=1)[0]["job_id"] == "python-job"


def test_posting_text_includes_description_and_skills():
    text = ss.posting_text(RECORDS[0])

    assert "python data pipelines" in text.lower()
    assert "Airflow" in text
