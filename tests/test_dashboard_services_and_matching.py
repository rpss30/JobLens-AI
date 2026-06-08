import pandas as pd

from src.dashboard.services import (
    filter_jobs,
    get_job_match_details,
    get_recommended_skills,
)
from src.matching.match_engine import (
    build_role_skill_weights,
    score_roles,
)


def make_sample_jobs_df() -> pd.DataFrame:
    """Create a small processed-style jobs dataframe for tests."""

    return pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "clean_title": "data scientist",
                "company": "Northstar Analytics",
                "location": "Toronto ON",
                "experience_level": "Entry Level",
                "role_category": "Data Science",
                "extracted_skills": ["Python", "SQL", "Pandas", "statistics"],
                "skills_text": "Python, SQL, Pandas, statistics",
            },
            {
                "title": "Machine Learning Engineer",
                "clean_title": "machine learning engineer",
                "company": "Vector AI",
                "location": "Vancouver BC",
                "experience_level": "Entry Level",
                "role_category": "AI/ML",
                "extracted_skills": ["Python", "PyTorch", "Docker", "AWS"],
                "skills_text": "Python, PyTorch, Docker, AWS",
            },
            {
                "title": "AWS Cloud Engineer",
                "clean_title": "aws cloud engineer",
                "company": "CloudWorks",
                "location": "Toronto ON",
                "experience_level": "Entry Level",
                "role_category": "Cloud/AWS",
                "extracted_skills": ["AWS", "Docker", "Terraform", "Lambda"],
                "skills_text": "AWS, Docker, Terraform, Lambda",
            },
            {
                "title": "Backend Developer",
                "clean_title": "backend developer",
                "company": "APIForge",
                "location": "Montreal QC",
                "experience_level": "Mid Level",
                "role_category": "Software Engineering",
                "extracted_skills": ["Python", "REST APIs", "PostgreSQL", "Docker"],
                "skills_text": "Python, REST APIs, PostgreSQL, Docker",
            },
        ]
    )


def test_filter_jobs_by_target_role_location_and_experience() -> None:
    jobs_df = make_sample_jobs_df()

    filtered_df = filter_jobs(
        df=jobs_df,
        target_roles=["Data Scientist"],
        location="Toronto ON",
        experience_level="Entry Level",
    )

    assert len(filtered_df) == 1
    assert filtered_df.iloc[0]["title"] == "Data Scientist"
    assert filtered_df.iloc[0]["location"] == "Toronto ON"


def test_filter_jobs_allows_any_location_and_experience() -> None:
    jobs_df = make_sample_jobs_df()

    filtered_df = filter_jobs(
        df=jobs_df,
        target_roles=["Cloud Engineer"],
        location="Any",
        experience_level="Any",
    )

    assert len(filtered_df) == 2

    returned_titles = set(filtered_df["title"].tolist())

    assert "Machine Learning Engineer" in returned_titles
    assert "AWS Cloud Engineer" in returned_titles

def test_get_job_match_details_calculates_job_level_scores() -> None:
    jobs_df = make_sample_jobs_df()

    job_match_df = get_job_match_details(
        filtered_jobs=jobs_df,
        user_skills=["Python", "SQL", "Pandas"],
    )

    assert not job_match_df.empty
    assert "job_match_score" in job_match_df.columns
    assert "matched_skills_preview" in job_match_df.columns
    assert "missing_skills_preview" in job_match_df.columns

    top_job = job_match_df.iloc[0]

    assert top_job["title"] == "Data Scientist"
    assert top_job["job_match_score"] == 75.0
    assert top_job["matched_skills_count"] == 3
    assert top_job["missing_skills_count"] == 1


def test_build_role_skill_weights_returns_weights_by_category() -> None:
    jobs_df = make_sample_jobs_df()

    role_skill_weights = build_role_skill_weights(jobs_df)

    assert "Data Science" in role_skill_weights
    assert "AI/ML" in role_skill_weights
    assert "Cloud/AWS" in role_skill_weights

    assert "python" in role_skill_weights["Data Science"]
    assert role_skill_weights["Data Science"]["python"] >= 1


def test_score_roles_returns_weighted_and_unweighted_scores() -> None:
    jobs_df = make_sample_jobs_df()

    role_scores_df = score_roles(
        jobs_df,
        user_skills=["Python", "SQL", "Pandas"],
    )

    assert not role_scores_df.empty

    expected_columns = {
        "role_category",
        "sample_size",
        "weighted_match_score",
        "unweighted_match_score",
        "matched_skills",
        "missing_skills",
        "matched_weight",
        "total_possible_weight",
        "role_skill_weights",
    }

    assert expected_columns.issubset(set(role_scores_df.columns))

    best_role = role_scores_df.iloc[0]["role_category"]
    assert best_role == "Data Science"


def test_get_recommended_skills_excludes_user_skills() -> None:
    jobs_df = make_sample_jobs_df()
    role_skill_weights = build_role_skill_weights(jobs_df)

    recommended_skills_df = get_recommended_skills(
        jobs_df=jobs_df,
        user_skills=["Python", "SQL"],
        role_skill_weights=role_skill_weights,
        top_n=10,
    )

    assert not recommended_skills_df.empty
    assert "skill" in recommended_skills_df.columns
    assert "score" in recommended_skills_df.columns
    assert "job_count" in recommended_skills_df.columns
    assert "avg_weight" in recommended_skills_df.columns

    recommended_skills = {
        skill.lower()
        for skill in recommended_skills_df["skill"].tolist()
    }

    assert "python" not in recommended_skills
    assert "sql" not in recommended_skills
    assert "docker" in recommended_skills

def test_score_roles_returns_zero_for_empty_user_skills() -> None:
    jobs_df = make_sample_jobs_df()

    role_scores_df = score_roles(
        jobs_df,
        user_skills=[],
    )

    assert not role_scores_df.empty
    assert all(role_scores_df["weighted_match_score"] == 0)
    assert all(role_scores_df["unweighted_match_score"] == 0)

def test_get_recommended_skills_empty_when_user_has_all_skills() -> None:
    jobs_df = make_sample_jobs_df()
    role_skill_weights = build_role_skill_weights(jobs_df)

    all_skills = [
        "Python",
        "SQL",
        "Pandas",
        "statistics",
        "PyTorch",
        "Docker",
        "AWS",
        "Terraform",
        "Lambda",
        "REST APIs",
        "PostgreSQL",
    ]

    recommended_skills_df = get_recommended_skills(
        jobs_df=jobs_df,
        user_skills=all_skills,
        role_skill_weights=role_skill_weights,
        top_n=10,
    )

    assert recommended_skills_df.empty

def test_filter_jobs_returns_empty_for_no_matches() -> None:
    jobs_df = make_sample_jobs_df()

    filtered_df = filter_jobs(
        df=jobs_df,
        target_roles=["Cybersecurity Analyst"],
        location="Ottawa ON",
        experience_level="Senior Level",
    )

    assert filtered_df.empty