from pathlib import Path

from src.dashboard.services import (
    CANADA_JOBS_SNAPSHOT_PATH,
    filter_jobs,
    get_available_locations,
    get_dataset_snapshot_summary,
    get_job_match_details,
    load_processed_jobs_from_csv,
)
from src.ingestion.canada_jobs import TARGET_ROLE_CATEGORIES
from src.matching.match_engine import score_roles


CANADA_SEARCH_CASES = {
    "AI / ML Roles": {
        "expected_best_role": "AI/ML",
        "target_roles": [
            "Machine Learning Engineer",
            "AI Engineer",
            "ML Platform Engineer",
        ],
        "current_skills": [
            "Python",
            "PyTorch",
            "TensorFlow",
            "Docker",
            "AWS",
            "model deployment",
        ],
    },
    "Data Science Roles": {
        "expected_best_role": "Data Science",
        "target_roles": ["Data Scientist"],
        "current_skills": [
            "Python",
            "SQL",
            "Pandas",
            "scikit-learn",
            "statistics",
        ],
    },
    "Cloud / AWS Roles": {
        "expected_best_role": "Cloud/AWS",
        "target_roles": [
            "Cloud Engineer",
            "DevOps Engineer",
            "Platform Engineer",
            "Site Reliability Engineer",
        ],
        "current_skills": [
            "AWS",
            "Docker",
            "Terraform",
            "Kubernetes",
            "CI/CD",
        ],
    },
    "Software Engineering Roles": {
        "expected_best_role": "Software Engineering",
        "target_roles": [
            "Backend Engineer",
            "Software Engineer",
            "Full Stack Engineer",
        ],
        "current_skills": [
            "Python",
            "REST APIs",
            "PostgreSQL",
            "Docker",
            "AWS",
        ],
    },
    "Analytics Roles": {
        "expected_best_role": "Analytics",
        "target_roles": [
            "Data Analyst",
            "Business Intelligence Analyst",
        ],
        "current_skills": [
            "SQL",
            "Tableau",
            "Power BI",
            "statistics",
            "data visualization",
        ],
    },
    "Data Engineering Roles": {
        "expected_best_role": "Data Engineering",
        "target_roles": [
            "Data Engineer",
            "Analytics Engineer",
        ],
        "current_skills": [
            "Python",
            "SQL",
            "AWS",
            "Airflow",
            "Snowflake",
        ],
    },
}


def test_canada_jobs_snapshot_is_packaged_and_enriched():
    snapshot_path = Path(CANADA_JOBS_SNAPSHOT_PATH)

    assert snapshot_path.exists()

    jobs_df = load_processed_jobs_from_csv(str(snapshot_path))

    assert len(jobs_df) >= 40
    assert jobs_df["company"].nunique() >= 12
    assert jobs_df["location"].nunique() >= 8
    assert jobs_df["job_id"].is_unique
    assert jobs_df["source_url"].is_unique
    assert jobs_df["extracted_skills"].apply(bool).all()
    assert (
        jobs_df["skill_extraction_provider"].eq("groq").mean()
        >= 0.95
    )
    assert jobs_df["source"].nunique() >= 2
    assert TARGET_ROLE_CATEGORIES.issubset(set(jobs_df["role_category"]))


def test_canada_jobs_snapshot_exposes_dataset_locations_and_metadata():
    jobs_df = load_processed_jobs_from_csv(CANADA_JOBS_SNAPSHOT_PATH)
    locations = get_available_locations(jobs_df)
    summary = get_dataset_snapshot_summary(jobs_df)

    assert "Toronto, ON" in locations
    assert "Vancouver, BC" in locations
    assert "Montreal, QC" in locations
    assert "Ottawa, ON" in locations
    assert "Calgary, AB" in locations
    assert "Remote, Canada" in locations
    assert summary["job_count"] == len(jobs_df)
    assert summary["company_count"] >= 12
    assert summary["location_count"] >= 8
    assert summary["refreshed_date"]


def test_canada_jobs_snapshot_supports_dashboard_searches():
    jobs_df = load_processed_jobs_from_csv(CANADA_JOBS_SNAPSHOT_PATH)

    for case in CANADA_SEARCH_CASES.values():
        filtered_jobs_df = filter_jobs(
            df=jobs_df,
            target_roles=case["target_roles"],
            location="Any",
            experience_level="Any",
        )

        assert not filtered_jobs_df.empty

        job_match_details_df = get_job_match_details(
            filtered_jobs=filtered_jobs_df,
            user_skills=case["current_skills"],
        )

        assert not job_match_details_df.empty
        assert (job_match_details_df["job_match_score"] > 0).any()
        assert job_match_details_df["source_url"].str.startswith("http").all()

        role_scores_df = score_roles(
            filtered_jobs_df,
            user_skills=case["current_skills"],
        )

        assert not role_scores_df.empty
        expected_role_rows = role_scores_df[
            role_scores_df["role_category"] == case["expected_best_role"]
        ]

        assert not expected_role_rows.empty
        assert expected_role_rows.iloc[0]["weighted_match_score"] > 0
