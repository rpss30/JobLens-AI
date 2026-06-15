from pathlib import Path

from src.dashboard.services import (
    GREENHOUSE_AI_DEMO_PATH,
    filter_jobs,
    get_job_match_details,
    load_processed_jobs_from_csv,
)
from src.matching.match_engine import score_roles


GREENHOUSE_DEMO_SEARCH_CASES = {
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
            "scikit-learn",
            "Docker",
            "AWS",
            "model deployment",
        ],
    },
    "Data Science Roles": {
        "expected_best_role": "Data Science",
        "target_roles": [
            "Data Scientist",
            "Junior Data Scientist",
        ],
        "current_skills": [
            "Python",
            "SQL",
            "Pandas",
            "NumPy",
            "scikit-learn",
            "statistics",
            "data visualization",
        ],
    },
    "Cloud / AWS Roles": {
        "expected_best_role": "Cloud/AWS",
        "target_roles": [
            "AWS Cloud Engineer",
            "Cloud Engineer",
            "Junior DevOps Engineer",
            "Platform Engineer",
        ],
        "current_skills": [
            "AWS",
            "EC2",
            "S3",
            "Lambda",
            "Docker",
            "Terraform",
            "Kubernetes",
        ],
    },
    "Software Engineering Roles": {
        "expected_best_role": "Software Engineering",
        "target_roles": [
            "Backend Developer",
            "Backend Engineer",
            "Software Engineer",
            "Full Stack Developer",
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
            "Product Analyst",
            "Business Intelligence Analyst",
            "Business Analyst",
        ],
        "current_skills": [
            "SQL",
            "Tableau",
            "Power BI",
            "statistics",
            "data visualization",
            "A/B testing",
        ],
    },
    "Data Engineering Roles": {
        "expected_best_role": "Data Engineering",
        "target_roles": [
            "Data Engineer",
            "Junior Data Engineer",
            "Cloud Data Engineer",
            "Analytics Engineer",
        ],
        "current_skills": [
            "Python",
            "SQL",
            "Pandas",
            "AWS",
            "Docker",
            "PostgreSQL",
        ],
    },
}


def test_greenhouse_ai_demo_dataset_is_packaged_for_dashboard() -> None:
    demo_dataset_path = Path(GREENHOUSE_AI_DEMO_PATH)

    assert demo_dataset_path.exists()

    demo_jobs_df = load_processed_jobs_from_csv(str(demo_dataset_path))

    assert not demo_jobs_df.empty
    assert 20 <= len(demo_jobs_df) <= 40

    required_columns = {
        "title",
        "company",
        "location",
        "experience_level",
        "role_category",
        "extracted_skills",
        "skills_text",
    }

    assert required_columns.issubset(set(demo_jobs_df.columns))

    assert not demo_jobs_df.duplicated(subset=["company", "title"]).any()
    assert demo_jobs_df["skills_text"].fillna("").str.strip().ne("").all()
    assert demo_jobs_df["extracted_skills"].apply(bool).all()
    assert "Entry Level" in set(demo_jobs_df["experience_level"].tolist())

    role_categories = set(demo_jobs_df["role_category"].dropna().tolist())

    assert {
        "AI/ML",
        "Software Engineering",
        "Data Science",
        "Data Engineering",
        "Cloud/AWS",
        "Analytics",
    }.issubset(role_categories)


def test_greenhouse_ai_demo_dataset_supports_sidebar_presets() -> None:
    demo_jobs_df = load_processed_jobs_from_csv(GREENHOUSE_AI_DEMO_PATH)

    for case in GREENHOUSE_DEMO_SEARCH_CASES.values():
        filtered_jobs_df = filter_jobs(
            df=demo_jobs_df,
            target_roles=case["target_roles"],
            location="Any",
            experience_level="Entry Level",
        )

        assert not filtered_jobs_df.empty

        job_match_details_df = get_job_match_details(
            filtered_jobs=filtered_jobs_df,
            user_skills=case["current_skills"],
        )

        assert not job_match_details_df.empty
        assert (job_match_details_df["job_match_score"] > 0).any()

        role_scores_df = score_roles(
            filtered_jobs_df,
            user_skills=case["current_skills"],
        )

        assert not role_scores_df.empty
        assert role_scores_df.iloc[0]["role_category"] == case["expected_best_role"]
        assert role_scores_df.iloc[0]["weighted_match_score"] > 0
