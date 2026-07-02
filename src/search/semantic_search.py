"""Deterministic semantic search helpers for job-market analysis.

This module uses local TF-IDF features projected into dense SVD vectors. It is
not a replacement for model embeddings, but it gives JobLens an offline,
testable semantic retrieval layer without adding network calls or pgvector
infrastructure for a small portfolio dataset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize


SEMANTIC_SEARCH_MODE = "semantic"
TFIDF_SEARCH_MODE = "tfidf"
HYBRID_SEARCH_MODE = "hybrid"
SEARCH_MODES = {TFIDF_SEARCH_MODE, SEMANTIC_SEARCH_MODE, HYBRID_SEARCH_MODE}


@dataclass(frozen=True)
class SemanticSearchConfig:
    n_components: int = 64
    minimum_score: float = 0.12
    dense_weight: float = 0.70
    sparse_weight: float = 0.30


DEFAULT_SEMANTIC_CONFIG = SemanticSearchConfig()


SEMANTIC_EXPANSIONS = {
    "server side": "backend backend services REST APIs databases PostgreSQL",
    "server-side": "backend backend services REST APIs databases PostgreSQL",
    "backend": "backend services REST APIs APIs databases PostgreSQL",
    "api": "REST APIs backend services API design",
    "apis": "REST APIs backend services API design",
    "database": "SQL PostgreSQL MySQL data modeling",
    "databases": "SQL PostgreSQL MySQL data modeling",
    "ml": "machine learning PyTorch TensorFlow model deployment MLflow",
    "machine learning": "machine learning PyTorch TensorFlow scikit-learn model deployment",
    "ai": "machine learning large language models NLP embeddings",
    "analytics": "SQL dashboards Tableau Power BI product metrics statistics",
    "business intelligence": "dashboards Tableau Power BI SQL analytics",
    "cloud": "AWS Docker Terraform Kubernetes Lambda EC2 S3 CloudWatch",
    "infrastructure": "AWS Terraform Kubernetes Docker CloudWatch CI/CD",
    "devops": "CI/CD Docker Kubernetes Terraform monitoring",
    "data pipeline": "data pipelines ETL Airflow Spark PySpark data warehousing",
    "data pipelines": "data pipelines ETL Airflow Spark PySpark data warehousing",
}


def normalize_search_mode(search_mode: str | None) -> str:
    normalized_mode = str(search_mode or TFIDF_SEARCH_MODE).strip().lower()
    return normalized_mode if normalized_mode in SEARCH_MODES else TFIDF_SEARCH_MODE


def get_column_text(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index, dtype=str)

    return df[column].fillna("").astype(str)


def build_job_search_documents(df: pd.DataFrame) -> pd.Series:
    """Build weighted job documents for lexical and semantic retrieval."""
    if df.empty:
        return pd.Series(dtype=str)

    return (
        (get_column_text(df, "title") + " ") * 4
        + (get_column_text(df, "role_category") + " ") * 3
        + (get_column_text(df, "skills_text") + " ") * 5
        + (get_column_text(df, "company") + " ") * 2
        + (get_column_text(df, "location") + " ") * 2
        + get_column_text(df, "description")
    ).str.strip()


def expand_semantic_query(query: str) -> str:
    """Add domain aliases so conceptual searches can match explicit skills."""
    normalized_query = re.sub(r"\s+", " ", str(query or "").strip().lower())

    if not normalized_query:
        return ""

    expansions = [
        expansion
        for trigger, expansion in SEMANTIC_EXPANSIONS.items()
        if trigger in normalized_query
    ]

    return " ".join([query, *expansions]).strip()


def build_candidate_profile_document(
    *,
    current_skills: list[str],
    resume_text: str = "",
    target_roles: list[str] | None = None,
) -> str:
    """Build a compact candidate profile document for job similarity."""
    skill_text = " ".join(str(skill) for skill in current_skills if str(skill).strip())
    role_text = " ".join(str(role) for role in target_roles or [] if str(role).strip())

    return " ".join(
        part
        for part in [
            (skill_text + " ") * 5,
            (role_text + " ") * 3,
            resume_text,
        ]
        if part.strip()
    ).strip()


def compute_semantic_scores(
    documents: pd.Series,
    query: str,
    *,
    config: SemanticSearchConfig = DEFAULT_SEMANTIC_CONFIG,
) -> np.ndarray:
    """Return zero-to-one semantic scores for documents against a query."""
    if documents.empty:
        return np.array([], dtype=float)

    expanded_query = expand_semantic_query(query)

    if not expanded_query:
        return np.zeros(len(documents), dtype=float)

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        sublinear_tf=True,
        token_pattern=r"(?u)(?<!\w)\w[\w+#./-]*(?!\w)",
        max_features=4096,
    )

    try:
        document_matrix = vectorizer.fit_transform(documents.fillna("").astype(str))
        query_vector = vectorizer.transform([expanded_query])
    except ValueError:
        return np.zeros(len(documents), dtype=float)

    sparse_scores = cosine_similarity(document_matrix, query_vector).ravel()

    max_components = min(
        config.n_components,
        max(1, document_matrix.shape[0] - 1),
        max(1, document_matrix.shape[1] - 1),
    )

    if max_components < 2:
        return np.clip(sparse_scores, 0.0, 1.0)

    svd = TruncatedSVD(n_components=max_components, random_state=42)
    document_embeddings = normalize(svd.fit_transform(document_matrix))
    query_embedding = normalize(svd.transform(query_vector))
    dense_scores = np.clip(document_embeddings @ query_embedding.T, 0.0, 1.0).ravel()

    combined_scores = (
        (dense_scores * config.dense_weight)
        + (sparse_scores * config.sparse_weight)
    )

    return np.clip(combined_scores, 0.0, 1.0)


def rank_jobs_by_semantic_query(
    df: pd.DataFrame,
    search_query: str,
    *,
    config: SemanticSearchConfig = DEFAULT_SEMANTIC_CONFIG,
) -> pd.DataFrame:
    """Filter and rank jobs using local dense semantic similarity."""
    query = str(search_query or "").strip()

    if not query:
        return df.copy()

    if df.empty:
        empty_df = df.copy()
        empty_df["semantic_relevance"] = pd.Series(dtype=float)
        return empty_df

    scores = compute_semantic_scores(
        build_job_search_documents(df),
        query,
        config=config,
    )
    relevant_mask = scores >= config.minimum_score
    ranked_df = df.loc[relevant_mask].copy()
    ranked_df["semantic_relevance"] = (scores[relevant_mask] * 100).round(1)
    ranked_df["search_mode"] = SEMANTIC_SEARCH_MODE

    return ranked_df.sort_values(
        by="semantic_relevance",
        ascending=False,
        kind="stable",
    )


def rank_jobs_by_candidate_profile(
    df: pd.DataFrame,
    *,
    current_skills: list[str],
    resume_text: str = "",
    target_roles: list[str] | None = None,
    config: SemanticSearchConfig = DEFAULT_SEMANTIC_CONFIG,
) -> pd.DataFrame:
    """Rank jobs by semantic similarity to skills/resume/profile text."""
    if df.empty:
        empty_df = df.copy()
        empty_df["resume_similarity"] = pd.Series(dtype=float)
        return empty_df

    profile_document = build_candidate_profile_document(
        current_skills=current_skills,
        resume_text=resume_text,
        target_roles=target_roles,
    )

    if not profile_document:
        empty_df = df.copy()
        empty_df["resume_similarity"] = 0.0
        return empty_df

    scores = compute_semantic_scores(
        build_job_search_documents(df),
        profile_document,
        config=SemanticSearchConfig(
            n_components=config.n_components,
            minimum_score=0.0,
            dense_weight=config.dense_weight,
            sparse_weight=config.sparse_weight,
        ),
    )
    ranked_df = df.copy()
    ranked_df["resume_similarity"] = (scores * 100).round(1)

    return ranked_df.sort_values(
        by="resume_similarity",
        ascending=False,
        kind="stable",
    )
