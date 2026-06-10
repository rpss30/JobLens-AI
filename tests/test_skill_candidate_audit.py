import pandas as pd

from scripts.audit_skill_candidates import (
    build_skill_candidate_report,
    clean_candidate_term,
    extract_candidate_terms,
)


def test_extract_candidate_terms_finds_terms_from_skill_context():
    description = (
        "We are looking for experience with PostgreSQL, MySQL, and cloud platforms. "
        "Knowledge of dashboards is helpful."
    )

    candidates = extract_candidate_terms(description)

    assert "mysql" in candidates
    assert "postgresql" in candidates


def test_clean_candidate_term_removes_generic_database_modifiers():
    assert clean_candidate_term("relational PostgreSQL") == "postgresql"
    assert clean_candidate_term("etc") == ""


def test_build_skill_candidate_report_excludes_existing_skills_and_keeps_new_candidates():
    df = pd.DataFrame(
        [
            {
                "job_id": "1",
                "description": "Experience with PostgreSQL, MySQL, and Superset.",
                "extracted_skills": "['postgresql', 'mysql']",
            },
            {
                "job_id": "2",
                "description": "Experience with PostgreSQL, MySQL, and Superset.",
                "extracted_skills": "['postgresql', 'mysql']",
            },
        ]
    )

    report = build_skill_candidate_report(df)
    candidate_terms = report["candidate_term"].tolist()

    assert "postgresql" not in candidate_terms
    assert "mysql" not in candidate_terms
    assert "superset" in candidate_terms