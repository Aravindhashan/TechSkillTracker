import pytest

from modules.normalizer import SkillNormalizer


@pytest.fixture(scope="module")
def normalizer():
    # load_model=False keeps tests fast and offline; embeddings are optional.
    return SkillNormalizer(load_model=False)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ReactJS", "React"),
        ("react.js", "React"),
        ("React JS", "React"),
        ("NodeJS", "Node.js"),
        ("node.js", "Node.js"),
        ("k8s", "Kubernetes"),
        ("Golang", "Go"),
        ("sklearn", "Scikit-learn"),
        ("Postgres", "PostgreSQL"),
        ("tailwind", "Tailwind"),
    ],
)
def test_alias_normalization(normalizer, raw, expected):
    result = normalizer.normalize(raw)
    assert result.canonical == expected
    assert result.method == "alias"


def test_canonical_names_are_idempotent(normalizer):
    for canonical in normalizer.canonical_names():
        assert normalizer.normalize(canonical).canonical == canonical


def test_fuzzy_match_for_typos(normalizer):
    result = normalizer.normalize("Kuberneties")
    assert result.canonical == "Kubernetes"
    assert result.method == "fuzzy"


def test_unknown_skill_is_kept_not_dropped(normalizer):
    result = normalizer.normalize("Fortran 90")
    assert result.canonical == "Fortran 90"
    assert result.method == "unmatched"


def test_embedding_fallback_maps_unseen_variant(tmp_path):
    import numpy as np

    class FakeModel:
        def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
            vectors = []
            for text in texts:
                lowered = str(text).lower()
                if lowered.startswith("golang") or lowered == "go":
                    vectors.append([1.0, 0.0, 0.0])
                else:
                    vectors.append([0.0, 1.0, 0.0])
            return np.asarray(vectors, dtype="float32")

    normalizer = SkillNormalizer(
        load_model=True,
        cache_path=str(tmp_path / "embeddings.npz"),
    )
    normalizer._model = FakeModel()

    result = normalizer.normalize("Golangista")
    assert result.method == "embedding"
    assert result.canonical == "Go"
    assert result.confidence == pytest.approx(1.0)


def test_normalize_many_deduplicates(normalizer):
    results = normalizer.normalize_many(["React", "ReactJS", "react.js", "Python"])
    assert [item.canonical for item in results] == ["React", "Python"]


def test_extract_from_text_avoids_substring_false_positives(normalizer):
    text = "We build with JavaScript, TypeScript and Node.js. Java is not required."
    skills = {item["skill_canonical"] for item in normalizer.extract_skills_from_text(text)}

    assert {"JavaScript", "TypeScript", "Node.js", "Java"} <= skills

    only_js = {item["skill_canonical"] for item in normalizer.extract_skills_from_text("JavaScript only")}
    assert only_js == {"JavaScript"}


def test_extract_prefers_longest_alias(normalizer):
    skills = [item["skill_canonical"] for item in normalizer.extract_skills_from_text("React Native developer")]
    assert skills == ["React Native"]


def test_extract_cpp_and_csharp(normalizer):
    skills = {item["skill_canonical"] for item in normalizer.extract_skills_from_text("C++ and C# services")}
    assert {"C++", "C#"} <= skills


def test_extract_respects_max_skills(normalizer):
    text = "Python Java Go Rust React Angular Vue TypeScript SQL Docker Kubernetes AWS Azure"
    skills = normalizer.extract_skills_from_text(text, max_skills=5)
    assert len(skills) == 5


def test_taxonomy_seeds_store(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "taxonomy.db"))

    from modules import store

    store.init_db()
    assert normalizer_seed() > 0
    assert any(entry["canonical"] == "React" for entry in store.fetch_skill_taxonomy())


def normalizer_seed():
    return SkillNormalizer(load_model=False).seed_store()
