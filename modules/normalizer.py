"""Canonical skill taxonomy with an embeddings fallback.

The dashboard treats skills as plain strings, so "React", "ReactJS" and
"React.js" look like three different skills.  This module maps every variant
onto one canonical name.

Resolution order (cheapest first):

1. exact alias match from the curated taxonomy
2. fuzzy string match (``difflib``)
3. sentence-transformer cosine similarity (``all-MiniLM-L6-v2``)
4. keep the raw string as its own canonical (marked ``unmatched``)

The embedding model is loaded lazily and the whole module degrades to
alias/fuzzy matching if the model cannot be downloaded.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_CACHE = os.path.join("data", "skill_embeddings.npz")
EMBEDDING_THRESHOLD = 0.70
FUZZY_THRESHOLD = 0.88


# canonical -> aliases (canonical itself is always accepted)
TAXONOMY: dict[str, list[str]] = {
    # Languages
    "Python": ["python3", "python 3", "python programming"],
    "JavaScript": ["js", "ecmascript", "es6", "es2015"],
    "TypeScript": ["ts"],
    "Java": ["java 8", "java 11", "java 17", "core java"],
    "C++": ["cpp", "c plus plus"],
    "C#": ["csharp", "c sharp", "dotnet c#"],
    "C": ["c language", "c programming"],
    "Go": ["golang", "go lang"],
    "Rust": ["rustlang"],
    "Ruby": ["ruby language"],
    "PHP": ["php7", "php8"],
    "Kotlin": ["kotlin language"],
    "Swift": ["swift language"],
    "Scala": ["scala language"],
    "R": ["r language", "r programming", "rstudio"],
    "SQL": ["structured query language", "sql queries"],
    "Bash": ["shell scripting", "shell script", "zsh"],
    # Frontend
    "React": ["reactjs", "react.js", "react js"],
    "React Native": ["reactnative", "react native js"],
    "Next.js": ["nextjs", "next js"],
    "Angular": ["angularjs", "angular.js", "angular 2", "angular 4"],
    "Vue.js": ["vuejs", "vue.js", "vue js", "vue"],
    "Redux": ["redux toolkit", "react redux"],
    "HTML": ["html5", "html 5"],
    "CSS": ["css3", "css 3"],
    "SASS": ["scss", "sass scss"],
    "Tailwind": ["tailwindcss", "tailwind css"],
    "Bootstrap": ["bootstrap css", "bootstrap 5"],
    "Webpack": ["webpack 5"],
    "Vite": ["vitejs"],
    "Figma": ["figma design"],
    # Backend / frameworks
    "Node.js": ["nodejs", "node js", "node"],
    "Express": ["express.js", "expressjs", "express js"],
    "Django": ["django rest framework", "drf", "django framework"],
    "Flask": ["flask framework"],
    "FastAPI": ["fast api"],
    "Spring Boot": ["springboot", "spring boot 3"],
    "Laravel": ["laravel framework"],
    "Ruby on Rails": ["rails", "ror"],
    ".NET": ["dotnet", "dot net", "asp.net", "asp net", "net core"],
    "REST API": ["rest", "restful", "restful api", "rest api design"],
    "GraphQL": ["graph ql", "apollo graphql"],
    "Microservices": ["micro services", "microservice architecture"],
    "gRPC": ["grpc api"],
    # Data / ML
    "Machine Learning": ["ml", "machine-learning", "machine learning models"],
    "Deep Learning": ["dl", "deep-learning", "neural networks"],
    "NLP": ["natural language processing"],
    "Computer Vision": ["computer vision ai"],
    "TensorFlow": ["tensorflow 2", "tf2"],
    "PyTorch": ["torch", "pytorch lightning"],
    "Scikit-learn": ["sklearn", "scikit learn", "scikitlearn"],
    "NumPy": ["numpy", "np"],
    "Pandas": ["pandas library", "python pandas"],
    "Spark": ["apache spark", "pyspark", "spark sql"],
    "Hadoop": ["apache hadoop"],
    "Hive": ["apache hive"],
    "Kafka": ["apache kafka", "kafka streams"],
    "Airflow": ["apache airflow"],
    "dbt": ["data build tool"],
    "Snowflake": ["snowflake data warehouse"],
    "BigQuery": ["google bigquery"],
    "Databricks": ["databricks platform"],
    "MLflow": ["ml flow"],
    "Hugging Face": ["huggingface", "hf transformers"],
    "LangChain": ["lang chain"],
    "Transformers": ["transformer models"],
    "Tableau": ["tableau desktop"],
    "Power BI": ["powerbi", "power-bi"],
    "ETL": ["extract transform load", "elt"],
    # Databases
    "PostgreSQL": ["postgres", "psql", "postgresql database"],
    "MySQL": ["my sql"],
    "MongoDB": ["mongo", "mongo db"],
    "Redis": ["redis cache"],
    "Elasticsearch": ["elastic search", "elasticsearch 8"],
    "DynamoDB": ["amazon dynamodb", "aws dynamodb"],
    "Oracle": ["oracle db", "oracle database"],
    "SQL Server": ["mssql", "microsoft sql server", "tsql", "ms sql"],
    "Cassandra": ["apache cassandra"],
    # Cloud / DevOps
    "AWS": ["amazon web services", "aws cloud", "ec2", "s3"],
    "Azure": ["microsoft azure", "azure cloud"],
    "GCP": ["google cloud", "google cloud platform"],
    "Docker": ["dockerfile", "docker compose", "docker-compose"],
    "Kubernetes": ["k8s", "kube"],
    "Terraform": ["terraform iac", "hashicorp terraform"],
    "Ansible": ["ansible playbook"],
    "Jenkins": ["jenkins ci"],
    "CI/CD": ["cicd", "ci cd", "continuous integration", "continuous delivery"],
    "DevOps": ["dev ops", "devops engineering"],
    "Linux": ["unix", "ubuntu", "centos", "rhel", "debian"],
    "Git": ["github", "gitlab", "git version control"],
    "Helm": ["helm charts"],
    "Prometheus": ["prometheus monitoring"],
    "Grafana": ["grafana dashboards"],
    "Nginx": ["nginx server"],
    # Testing / tooling
    "Jest": ["jest testing"],
    "Cypress": ["cypress io"],
    "Selenium": ["selenium webdriver"],
    "Postman": ["postman api"],
    "Jira": ["atlassian jira"],
    # Mobile / other
    "Flutter": ["flutter dart"],
    "Dart": ["dart language"],
    "Unity": ["unity3d", "unity engine"],
    "Solidity": ["solidity smart contracts"],
}

# Aliases that are too ambiguous to match inside prose. They still work for
# exact lookups ("np" -> NumPy), but are skipped during text extraction.
_EXTRACTION_SKIP_ALIASES = {"np", "node", "rails", "torch"}


@dataclass
class NormalizedSkill:
    raw: str
    canonical: str
    confidence: float
    method: str  # alias | fuzzy | embedding | unmatched


def _boundary_pattern(alias: str, case_sensitive: bool = False) -> re.Pattern:
    escaped = re.escape(alias).replace(r"\ ", r"[\s\-_]+")
    # Word-ish boundaries that also work for C++, C#, .NET
    prefix = r"(?<![A-Za-z0-9+#/])"
    suffix = r"(?![A-Za-z0-9+#/&])"
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(prefix + escaped + suffix, flags)


class SkillNormalizer:
    """Map raw skill strings onto the canonical taxonomy."""

    def __init__(
        self,
        taxonomy: dict[str, list[str]] | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        cache_path: str | None = None,
        load_model: bool = True,
    ):
        self.taxonomy = dict(taxonomy or TAXONOMY)
        self.model_name = model_name
        self.cache_path = cache_path or os.getenv(
            "SKILL_EMBEDDING_CACHE", DEFAULT_EMBEDDING_CACHE
        )
        self._load_model = load_model
        self._model = None
        self._model_failed = False
        self._matrix_names: list[str] = []
        self._model_matrix: np.ndarray | None = None

        self._alias_to_canonical: dict[str, str] = {}
        for canonical, aliases in self.taxonomy.items():
            self._alias_to_canonical[canonical.lower()] = canonical
            for alias in aliases:
                self._alias_to_canonical.setdefault(alias.lower(), canonical)

        self._alias_keys = sorted(self._alias_to_canonical.keys(), key=len, reverse=True)
        self._extractors: list[tuple[str, str, re.Pattern]] = []
        for alias, canonical in self._alias_to_canonical.items():
            if alias in _EXTRACTION_SKIP_ALIASES or len(alias) < 1:
                continue
            self._extractors.append(
                (alias, canonical, _boundary_pattern(alias, case_sensitive=len(alias) == 1))
            )
        # longest alias first so "React Native" beats "React"
        self._extractors.sort(key=lambda item: len(item[0]), reverse=True)

    # -- taxonomy helpers ---------------------------------------------------

    def canonical_names(self) -> list[str]:
        return sorted(self.taxonomy)

    def taxonomy_entries(self) -> list[dict]:
        return [
            {"canonical": canonical, "aliases": list(aliases)}
            for canonical, aliases in sorted(self.taxonomy.items())
        ]

    def seed_store(self, with_embeddings: bool = False) -> int:
        """Persist the taxonomy to whichever store is configured.

        With ``with_embeddings`` the canonical names are embedded once and the
        vectors are stored alongside the aliases, so later similarity lookups
        do not need to re-encode the taxonomy.
        """
        from modules.store import save_skill_taxonomy

        entries = self.taxonomy_entries()
        if with_embeddings:
            model = self._ensure_model()
            if model is not None:
                vectors = model.encode(
                    [entry["canonical"] for entry in entries],
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                for entry, vector in zip(entries, vectors):
                    entry["embedding"] = [round(float(value), 5) for value in vector]
        return save_skill_taxonomy(entries)

    # -- normalisation ------------------------------------------------------

    def normalize(self, raw: str) -> NormalizedSkill:
        cleaned = (raw or "").strip()
        if not cleaned:
            return NormalizedSkill(raw, "", 0.0, "unmatched")

        key = cleaned.lower()
        if key in self._alias_to_canonical:
            return NormalizedSkill(cleaned, self._alias_to_canonical[key], 1.0, "alias")

        close = difflib.get_close_matches(key, self._alias_keys, n=1, cutoff=FUZZY_THRESHOLD)
        if close:
            return NormalizedSkill(
                cleaned, self._alias_to_canonical[close[0]], 0.9, "fuzzy"
            )

        match = self._embedding_match(cleaned)
        if match is not None:
            canonical, confidence = match
            return NormalizedSkill(cleaned, canonical, round(confidence, 3), "embedding")

        return NormalizedSkill(cleaned, cleaned, 0.0, "unmatched")

    def normalize_many(self, raw_skills: Iterable[str]) -> list[NormalizedSkill]:
        results: list[NormalizedSkill] = []
        seen: set[str] = set()
        for raw in raw_skills:
            result = self.normalize(raw)
            if not result.canonical or result.canonical in seen:
                continue
            seen.add(result.canonical)
            results.append(result)
        return results

    def extract_skills_from_text(self, text: str, max_skills: int = 40) -> list[dict]:
        """Find skill mentions in prose and return canonical skill dicts."""
        if not text:
            return []

        taken: list[tuple[int, int]] = []
        found: list[tuple[int, dict]] = []

        for _alias, canonical, pattern in self._extractors:
            for match in pattern.finditer(text):
                start, end = match.span()
                if any(not (end <= taken_start or start >= taken_end) for taken_start, taken_end in taken):
                    continue
                taken.append((start, end))
                found.append(
                    (
                        start,
                        {
                            "skill_raw": match.group(0),
                            "skill_canonical": canonical,
                            "confidence": 1.0,
                        },
                    )
                )

        found.sort(key=lambda item: item[0])
        output: list[dict] = []
        seen: set[str] = set()
        for _start, skill in found:
            if skill["skill_canonical"] in seen:
                continue
            seen.add(skill["skill_canonical"])
            output.append(skill)
            if len(output) >= max_skills:
                break
        return output

    # -- embeddings ---------------------------------------------------------

    def _ensure_model(self):
        if self._model is not None or self._model_failed or not self._load_model:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        except Exception:
            self._model_failed = True
            self._model = None
        return self._model

    def _canonical_matrix(self) -> tuple[np.ndarray | None, list[str]]:
        if self._model_matrix is not None:
            return self._model_matrix, self._matrix_names

        names = self.canonical_names()
        signature = hashlib.sha1("|".join(names).encode("utf-8")).hexdigest()

        cached = self._load_cached_embeddings(signature)
        if cached is not None:
            self._model_matrix, self._matrix_names = cached
            return self._model_matrix, self._matrix_names

        model = self._ensure_model()
        if model is None:
            return None, names

        vectors = model.encode(names, normalize_embeddings=True, show_progress_bar=False)
        self._model_matrix = np.asarray(vectors, dtype="float32")
        self._matrix_names = names
        self._save_cached_embeddings(signature, names, self._model_matrix)
        return self._model_matrix, self._matrix_names

    def _embedding_match(self, text: str) -> tuple[str, float] | None:
        model = self._ensure_model()
        if model is None:
            return None

        matrix, names = self._canonical_matrix()
        if matrix is None or not names:
            return None

        vector = np.asarray(
            model.encode([text], normalize_embeddings=True, show_progress_bar=False)[0],
            dtype="float32",
        )
        scores = matrix @ vector
        best = int(np.argmax(scores))
        confidence = float(scores[best])
        if confidence < EMBEDDING_THRESHOLD:
            return None
        return names[best], confidence

    def _load_cached_embeddings(self, signature: str):
        if not self.cache_path or not os.path.exists(self.cache_path):
            return None
        try:
            data = np.load(self.cache_path, allow_pickle=False)
            if str(data["signature"]) != signature:
                return None
            return data["vectors"], [str(name) for name in data["names"]]
        except Exception:
            return None

    def _save_cached_embeddings(self, signature: str, names: list[str], vectors: np.ndarray) -> None:
        if not self.cache_path:
            return
        try:
            parent = os.path.dirname(self.cache_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            np.savez(
                self.cache_path,
                signature=np.array(signature),
                names=np.array(names, dtype=str),
                vectors=vectors,
            )
        except Exception:
            pass


def normalize_skill_list(raw_skills: Iterable[str]) -> list[dict]:
    """Convenience helper used by ingestion and the resume pipeline."""
    normalizer = SkillNormalizer(load_model=False)
    return [
        {
            "skill_raw": item.raw,
            "skill_canonical": item.canonical,
            "confidence": item.confidence,
        }
        for item in normalizer.normalize_many(raw_skills)
    ]


if __name__ == "__main__":  # small manual smoke test
    import sys

    normalizer = SkillNormalizer()
    for value in sys.argv[1:] or ["ReactJS", "react.js", "K8s", "Golang", "C++"]:
        result = normalizer.normalize(value)
        print(json.dumps(result.__dict__, indent=2))
