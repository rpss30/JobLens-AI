import pandas as pd

from src.search.semantic_search import (
    HYBRID_SEARCH_MODE,
    SEMANTIC_SEARCH_MODE,
    TFIDF_SEARCH_MODE,
    build_candidate_profile_document,
    expand_semantic_query,
    normalize_search_mode,
    rank_jobs_by_candidate_profile,
    rank_jobs_by_semantic_query,
)


def make_semantic_jobs_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "title": "Backend Developer",
                "company": "APIForge",
                "location": "Montreal QC",
                "role_category": "Software Engineering",
                "skills_text": "Python, REST APIs, PostgreSQL, Docker",
                "description": "Build backend services and REST APIs with Python.",
            },
            {
                "title": "Machine Learning Engineer",
                "company": "Vector AI",
                "location": "Vancouver BC",
                "role_category": "AI/ML",
                "skills_text": "Python, PyTorch, TensorFlow, MLflow",
                "description": "Deploy machine learning models and ML platforms.",
            },
            {
                "title": "Analytics Engineer",
                "company": "InsightCo",
                "location": "Toronto ON",
                "role_category": "Analytics",
                "skills_text": "SQL, dbt, Tableau, dashboards",
                "description": "Build BI dashboards and product metrics.",
            },
        ]
    )


def test_expand_semantic_query_adds_domain_aliases() -> None:
    expanded_query = expand_semantic_query("server-side database work")

    assert "backend services" in expanded_query
    assert "PostgreSQL" in expanded_query


def test_rank_jobs_by_semantic_query_matches_conceptual_backend_search() -> None:
    ranked_df = rank_jobs_by_semantic_query(
        make_semantic_jobs_df(),
        "server-side database APIs",
    )

    assert ranked_df.iloc[0]["title"] == "Backend Developer"
    assert ranked_df.iloc[0]["semantic_relevance"] > 0
    assert ranked_df.iloc[0]["search_mode"] == SEMANTIC_SEARCH_MODE


def test_rank_jobs_by_semantic_query_returns_empty_for_unrelated_query() -> None:
    ranked_df = rank_jobs_by_semantic_query(
        make_semantic_jobs_df(),
        "quantum cryptography hardware",
    )

    assert ranked_df.empty
    assert "semantic_relevance" in ranked_df.columns


def test_rank_jobs_by_candidate_profile_prioritizes_related_jobs() -> None:
    ranked_df = rank_jobs_by_candidate_profile(
        make_semantic_jobs_df(),
        current_skills=["PyTorch", "model deployment", "MLflow"],
        target_roles=["Machine Learning Engineer"],
    )

    assert ranked_df.iloc[0]["title"] == "Machine Learning Engineer"
    assert ranked_df.iloc[0]["resume_similarity"] > 0


def test_build_candidate_profile_document_weights_skills_and_roles() -> None:
    document = build_candidate_profile_document(
        current_skills=["Python", "SQL"],
        target_roles=["Data Engineer"],
        resume_text="Built Airflow pipelines.",
    )

    assert document.count("Python") == 5
    assert document.count("Data Engineer") == 3
    assert "Airflow pipelines" in document


def test_normalize_search_mode_defaults_to_tfidf() -> None:
    assert normalize_search_mode("semantic") == SEMANTIC_SEARCH_MODE
    assert normalize_search_mode("hybrid") == HYBRID_SEARCH_MODE
    assert normalize_search_mode("unexpected") == TFIDF_SEARCH_MODE
