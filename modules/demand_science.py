"""Demand-side science: survival, anomaly, dedup, associations, communities, embeddings.

All functions are pure-ish (they take a postings dataframe or list of records)
and degrade gracefully when optional libraries are missing.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False

try:
    from sklearn.ensemble import IsolationForest
    _HAS_IF = True
except ImportError:
    _HAS_IF = False

try:
    from gensim.models import Word2Vec
    _HAS_GENSIM = True
except ImportError:
    _HAS_GENSIM = False

try:
    from statsmodels.duration.hazard_regression import PHReg
    _HAS_PHREG = True
except ImportError:
    _HAS_PHREG = False


# ---------------------------------------------------------------------------
# Survival analysis (Kaplan-Meier + Cox via statsmodels PHReg)
# ---------------------------------------------------------------------------


def _posting_lifetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-posting frame with duration (days) and event indicator."""
    if df is None or df.empty:
        return pd.DataFrame()

    # Collapse skill-expanded rows to one row per posting.
    if "Job ID" in df.columns:
        base = df.drop_duplicates(subset=["Job ID"]).copy()
    else:
        base = df.drop_duplicates(subset=["Job Title", "Company", "Location"]).copy()

    if "first_seen" in base.columns:
        first = pd.to_datetime(base["first_seen"], errors="coerce", utc=True)
    else:
        first = pd.to_datetime(base["Date Posted"], errors="coerce", utc=True)
    if "last_seen" in base.columns:
        last = pd.to_datetime(base["last_seen"], errors="coerce", utc=True)
    else:
        last = pd.to_datetime(base["Date Posted"], errors="coerce", utc=True)

    # Right-censoring: postings still active are censored at the observation end.
    observation_end = last.max() if not last.isna().all() else pd.Timestamp.now(tz="UTC")
    duration = (last - first).dt.total_seconds() / 86400.0
    duration = duration.fillna(0).clip(lower=0)
    # If first==last (seen once) treat as censored at observation end.
    censored = (duration <= 0)
    duration = duration.where(~censored, (observation_end - first).dt.total_seconds() / 86400.0)
    duration = duration.fillna(1.0).clip(lower=1.0)

    event = (~censored).astype(int)
    # Also mark inactive postings as events (they were observed to close).
    if "is_active" in base.columns:
        inactive = ~base["is_active"].fillna(True).astype(bool)
        event = (event | inactive.astype(int)).clip(upper=1)

    base = base.copy()
    base["duration_days"] = duration.values
    base["event"] = event.values
    return base


def kaplan_meier(df: pd.DataFrame) -> pd.DataFrame:
    """Return a Kaplan-Meier survival table: time, at_risk, events, survival."""
    life = _posting_lifetimes(df)
    if life.empty:
        return pd.DataFrame(columns=["time", "at_risk", "events", "survival"])

    times = sorted(life["duration_days"].unique())
    at_risk = len(life)
    survival = 1.0
    rows = []
    for t in times:
        d = int(((life["duration_days"] == t) & (life["event"] == 1)).sum())
        n = int((life["duration_days"] >= t).sum())
        if n <= 0:
            continue
        survival *= (n - d) / n
        rows.append({"time": float(t), "at_risk": n, "events": d, "survival": round(survival, 4)})
    return pd.DataFrame(rows)


def survival_by_group(df: pd.DataFrame, group_col: str, top_n: int = 8) -> dict[str, pd.DataFrame]:
    """Kaplan-Meier curves per top group value."""
    if group_col not in df.columns:
        return {}
    life = _posting_lifetimes(df)
    if life.empty:
        return {}
    top = life[group_col].value_counts().head(top_n).index.tolist()
    result = {}
    for value in top:
        sub = life[life[group_col] == value]
        if len(sub) < 3:
            continue
        # Re-run KM on the subset by temporarily filtering df.
        subset_df = df[df[group_col] == value] if group_col in df.columns else df
        result[str(value)] = kaplan_meier(subset_df)
    return result


def cox_regression(df: pd.DataFrame) -> dict[str, Any]:
    """Cox PH on skill + location covariates. Returns coefficients or error."""
    if not _HAS_PHREG:
        return {"error": "statsmodels PHReg unavailable"}
    life = _posting_lifetimes(df)
    if life.empty or life["event"].sum() < 3:
        return {"error": "not enough events for Cox regression"}

    # Build covariate matrix from top skills and locations.
    top_skills = life["Tech Skill"].value_counts().head(8).index.tolist() if "Tech Skill" in life.columns else []
    top_locations = life["Location"].value_counts().head(5).index.tolist() if "Location" in life.columns else []

    cov_cols = []
    for skill in top_skills:
        col = f"skill_{skill}"
        life[col] = (life["Tech Skill"] == skill).astype(int)
        cov_cols.append(col)
    for loc in top_locations:
        col = f"loc_{loc}"
        life[col] = (life["Location"] == loc).astype(int)
        cov_cols.append(col)

    if not cov_cols:
        return {"error": "no covariates"}

    try:
        model = PHReg.from_formula(
            "duration_days ~ " + " + ".join(cov_cols),
            data=life,
            status=life["event"],
        )
        res = model.fit()
        params = res.params
        summary = []
        for name in cov_cols:
            summary.append(
                {
                    "covariate": name,
                    "coef": round(float(params.get(name, 0)), 4),
                    "exp_coef": round(float(np.exp(params.get(name, 0))), 4),
                    "p_value": round(float(res.pvalues.get(name, 1)), 4),
                }
            )
        return {"coefficients": summary, "n": len(life), "events": int(life["event"].sum())}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Anomaly detection (Isolation Forest + z-scores)
# ---------------------------------------------------------------------------


def anomaly_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Flag anomalous postings using z-scores on experience and IsolationForest.

    Returns a dataframe of flagged rows with a reason.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()
    work["Experience Required (in years)"] = pd.to_numeric(
        work["Experience Required (in years)"], errors="coerce"
    )

    flagged = []
    # Z-score on experience per skill
    for skill, group in work.groupby("Tech Skill"):
        exp = group["Experience Required (in years)"]
        if exp.notna().sum() < 5:
            continue
        mean = exp.mean()
        std = exp.std()
        if std and std > 0:
            z = (exp - mean) / std
            for idx in group.index[z.abs() > 2.5]:
                flagged.append(
                    {
                        "Job Title": work.loc[idx, "Job Title"],
                        "Tech Skill": skill,
                        "Location": work.loc[idx, "Location"],
                        "Experience Required (in years)": work.loc[idx, "Experience Required (in years)"],
                        "reason": f"experience z-score {z.loc[idx]:.2f}",
                    }
                )

    # IsolationForest on experience (if enough data)
    if _HAS_IF and len(work) >= 20:
        features = work[["Experience Required (in years)"]].fillna(work["Experience Required (in years)"].median())
        iso = IsolationForest(contamination=0.05, random_state=42)
        preds = iso.fit_predict(features)
        for idx in work.index[preds == -1]:
            row = work.loc[idx]
            if not any(f["Job Title"] == row["Job Title"] and f["Tech Skill"] == row["Tech Skill"] for f in flagged):
                flagged.append(
                    {
                        "Job Title": row["Job Title"],
                        "Tech Skill": row["Tech Skill"],
                        "Location": row["Location"],
                        "Experience Required (in years)": row["Experience Required (in years)"],
                        "reason": "isolation forest outlier",
                    }
                )

    return pd.DataFrame(flagged)


# ---------------------------------------------------------------------------
# MinHash LSH dedup
# ---------------------------------------------------------------------------


def _shingles(text: str, k: int = 3) -> set[str]:
    words = re.findall(r"\w+", (text or "").lower())
    if len(words) < k:
        return set(words)
    return set(" ".join(words[i : i + k]) for i in range(len(words) - k + 1))


def _minhash_signature(shingles: set[str], num_perm: int = 128) -> list[int]:
    if not shingles:
        return [0] * num_perm
    sig = []
    for i in range(num_perm):
        min_hash = min(hash(f"{i}:{s}") & 0xFFFFFFFF for s in shingles)
        sig.append(min_hash)
    return sig


def minhash_dedupe(records: list[dict], threshold: float = 0.7) -> list[dict]:
    """Deduplicate records by MinHash similarity on title+company+description."""
    if not records:
        return []

    sigs = []
    for rec in records:
        text = f"{rec.get('title', '')} {rec.get('company', '')} {rec.get('description', '')}"
        sigs.append(_minhash_signature(_shingles(text)))

    # Union-find over pairs above threshold.
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            # Jaccard estimate from MinHash
            matches = sum(1 for a, b in zip(sigs[i], sigs[j]) if a == b)
            sim = matches / len(sigs[i])
            if sim >= threshold:
                union(i, j)

    # Keep one representative per cluster (first occurrence).
    seen_roots = set()
    result = []
    for i, rec in enumerate(records):
        root = find(i)
        if root in seen_roots:
            continue
        seen_roots.add(root)
        result.append(rec)
    return result


# ---------------------------------------------------------------------------
# PMI association mining (per-posting co-occurrence)
# ---------------------------------------------------------------------------


def skill_pmi(df: pd.DataFrame, min_count: int = 2) -> list[dict[str, Any]]:
    """Pointwise mutual information on skill pairs within the same posting."""
    if df is None or df.empty or "Tech Skill" not in df.columns:
        return []

    # Build per-posting skill sets.
    if "Job ID" in df.columns:
        grouped = df.groupby("Job ID")["Tech Skill"].apply(lambda s: set(s.dropna()))
    else:
        grouped = df.groupby(["Job Title", "Company", "Location"])["Tech Skill"].apply(lambda s: set(s.dropna()))

    skill_counts: Counter = Counter()
    pair_counts: Counter = Counter()
    n_docs = 0
    for skills in grouped:
        skills = {s for s in skills if s and str(s).lower() != "nan"}
        if not skills:
            continue
        n_docs += 1
        for s in skills:
            skill_counts[s] += 1
        for a, b in combinations(sorted(skills), 2):
            pair_counts[(a, b)] += 1

    if n_docs == 0:
        return []

    results = []
    for (a, b), n_ab in pair_counts.items():
        if n_ab < min_count:
            continue
        p_a = skill_counts[a] / n_docs
        p_b = skill_counts[b] / n_docs
        p_ab = n_ab / n_docs
        if p_a <= 0 or p_b <= 0 or p_ab <= 0:
            continue
        pmi = math.log(p_ab / (p_a * p_b))
        results.append(
            {
                "skill_a": a,
                "skill_b": b,
                "cooccurrence": int(n_ab),
                "pmi": round(pmi, 3),
            }
        )
    results.sort(key=lambda r: r["pmi"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Louvain community detection on skill graph
# ---------------------------------------------------------------------------


def skill_communities(df: pd.DataFrame) -> dict[str, int]:
    """Run Louvain on a skill co-occurrence graph; return {skill: community_id}."""
    if not _HAS_NX or df is None or df.empty:
        return {}

    # Per-posting co-occurrence edges.
    if "Job ID" in df.columns:
        grouped = df.groupby("Job ID")["Tech Skill"].apply(lambda s: list(set(s.dropna())))
    else:
        grouped = df.groupby(["Job Title", "Company", "Location"])["Tech Skill"].apply(lambda s: list(set(s.dropna())))

    G = nx.Graph()
    for skills in grouped:
        skills = [s for s in skills if s and str(s).lower() != "nan"]
        for s in skills:
            G.add_node(s)
        for a, b in combinations(skills, 2):
            if G.has_edge(a, b):
                G[a][b]["weight"] += 1
            else:
                G.add_edge(a, b, weight=1)

    if G.number_of_nodes() == 0:
        return {}

    try:
        communities = nx.community.louvain_communities(G, weight="weight", seed=42)
    except Exception:
        return {}

    mapping = {}
    for cid, members in enumerate(communities):
        for m in members:
            mapping[m] = cid
    return mapping


# ---------------------------------------------------------------------------
# Word2Vec skill relatedness
# ---------------------------------------------------------------------------


def skill_relatedness(df: pd.DataFrame, top_n: int = 5) -> dict[str, list[tuple[str, float]]]:
    """Train Word2Vec on posting skill sequences; return top-N similar skills."""
    if not _HAS_GENSIM or df is None or df.empty:
        return {}

    if "Job ID" in df.columns:
        grouped = df.groupby("Job ID")["Tech Skill"].apply(lambda s: [x for x in s.dropna().tolist()])
    else:
        grouped = df.groupby(["Job Title", "Company", "Location"])["Tech Skill"].apply(lambda s: [x for x in s.dropna().tolist()])

    sentences = [list(skills) for skills in grouped if skills and len(skills) >= 2]
    if len(sentences) < 5:
        return {}

    try:
        model = Word2Vec(sentences, vector_size=50, window=5, min_count=2, workers=1, epochs=20, seed=42)
    except Exception:
        return {}

    result = {}
    for skill in model.wv.index_to_key:
        try:
            similar = model.wv.most_similar(skill, topn=top_n)
            result[skill] = [(s, round(float(score), 3)) for s, score in similar]
        except Exception:
            continue
    return result
