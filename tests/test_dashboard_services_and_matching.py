import pandas as pd
import pytest

from src.dashboard.services import (
    filter_jobs,
    generate_candidate_report_markdown,
    get_candidate_fit_summary,
    get_job_match_details,
    get_positive_job_matches,
    get_recommended_skills,
    read_uploaded_jobs_csv,
    validate_uploaded_jobs_csv,
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

    assert len(filtered_df) == 1

    returned_titles = set(filtered_df["title"].tolist())

    assert "AWS Cloud Engineer" in returned_titles
    assert "Machine Learning Engineer" not in returned_titles

def test_filter_jobs_does_not_match_only_generic_engineer_word() -> None:
    jobs_df = make_sample_jobs_df()

    filtered_df = filter_jobs(
        df=jobs_df,
        target_roles=["Software Engineer"],
        location="Any",
        experience_level="Any",
    )

    returned_titles = set(filtered_df["title"].tolist())

    assert "Machine Learning Engineer" not in returned_titles
    assert "AWS Cloud Engineer" not in returned_titles

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


def test_get_positive_job_matches_excludes_zero_score_jobs() -> None:
    jobs_df = make_sample_jobs_df()

    job_match_df = get_job_match_details(
        filtered_jobs=jobs_df,
        user_skills=["PyTorch"],
    )

    positive_matches_df = get_positive_job_matches(job_match_df)

    assert not positive_matches_df.empty
    assert all(positive_matches_df["job_match_score"] > 0)
    assert "Data Scientist" not in set(positive_matches_df["title"])
    assert "Machine Learning Engineer" in set(positive_matches_df["title"])


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


def test_candidate_fit_summary_handles_zero_skill_overlap() -> None:
    jobs_df = pd.DataFrame(
        [
            {
                "title": "Backend Software Engineer",
                "clean_title": "backend software engineer",
                "company": "TestCo",
                "location": "Remote",
                "experience_level": "Senior",
                "role_category": "Software Engineering",
                "extracted_skills": ["Go", "Java", "SQL"],
                "skills_text": "Go, Java, SQL",
            }
        ]
    )

    role_skill_weights = build_role_skill_weights(jobs_df)
    role_scores_df = score_roles(jobs_df, user_skills=["Python", "Docker"])
    recommended_skills_df = get_recommended_skills(
        jobs_df=jobs_df,
        user_skills=["Python", "Docker"],
        role_skill_weights=role_skill_weights,
        top_n=3,
    )

    summary = get_candidate_fit_summary(
        filtered_jobs=jobs_df,
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
    )

    assert "no overlap" in summary["summary"]
    assert "strongest fit" not in summary["summary"]
    assert summary["matched_skills"] == []
    assert summary["missing_skills"]


def test_filter_jobs_returns_empty_for_no_matches() -> None:
    jobs_df = make_sample_jobs_df()

    filtered_df = filter_jobs(
        df=jobs_df,
        target_roles=["Cybersecurity Analyst"],
        location="Ottawa ON",
        experience_level="Senior Level",
    )

    assert filtered_df.empty

def test_validate_uploaded_jobs_csv_accepts_valid_file() -> None:
    uploaded_df = pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "company": "TestCo",
                "location": "Toronto ON",
                "description": "Analyze data using Python, SQL, Pandas, and statistics.",
                "experience_level": "Entry Level",
            }
        ]
    )

    is_valid, message = validate_uploaded_jobs_csv(uploaded_df)

    assert is_valid is True
    assert message == "Uploaded CSV is valid."


def test_validate_uploaded_jobs_csv_rejects_missing_required_columns() -> None:
    uploaded_df = pd.DataFrame(
        [
            {
                "job_title": "Data Scientist",
                "company": "TestCo",
                "location": "Toronto ON",
                "description": "Analyze data using Python and SQL.",
            }
        ]
    )

    is_valid, message = validate_uploaded_jobs_csv(uploaded_df)

    assert is_valid is False
    assert "missing required columns" in message
    assert "experience_level" in message
    assert "title" in message


def test_validate_uploaded_jobs_csv_rejects_blank_required_values() -> None:
    uploaded_df = pd.DataFrame(
        [
            {
                "title": "Data Scientist",
                "company": "",
                "location": "Toronto ON",
                "description": "Analyze data using Python and SQL.",
                "experience_level": "Entry Level",
            }
        ]
    )

    is_valid, message = validate_uploaded_jobs_csv(uploaded_df)

    assert is_valid is False
    assert "blank values" in message
    assert "company" in message

def test_read_uploaded_jobs_csv_rejects_bad_csv_format(tmp_path) -> None:
    bad_csv_path = tmp_path / "bad_csv_format.csv"

    bad_csv_path.write_text(
        "\n".join(
            [
                "title,company,location,description,experience_level",
                'Data Scientist,TestCo,Toronto ON,"Analyze data using Python and SQL.",Entry Level',
                'Cloud Engineer,CloudTest,Vancouver BC,"Build AWS infrastructure using AWS and Docker.",Entry Level,EXTRA_COLUMN',
                'Backend Developer,APITest,Montreal QC,"Build REST APIs using Python and PostgreSQL.",Entry Level',
            ]
        )
    )

    with pytest.raises(pd.errors.ParserError):
        read_uploaded_jobs_csv(bad_csv_path)

def test_generate_candidate_report_markdown_includes_key_sections() -> None:
    jobs_df = make_sample_jobs_df()
    current_skills = ["Python", "SQL", "Pandas"]
    target_roles = ["Data Scientist"]

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=target_roles,
        location="Toronto ON",
        experience_level="Entry Level",
    )

    role_skill_weights = build_role_skill_weights(filtered_jobs)

    role_scores_df = score_roles(
        filtered_jobs,
        user_skills=current_skills,
    )

    recommended_skills_df = get_recommended_skills(
        jobs_df=filtered_jobs,
        user_skills=current_skills,
        role_skill_weights=role_skill_weights,
        top_n=10,
    )

    job_match_details_df = get_job_match_details(
        filtered_jobs=filtered_jobs,
        user_skills=current_skills,
    )

    report_markdown = generate_candidate_report_markdown(
        current_skills=current_skills,
        target_roles=target_roles,
        location="Toronto ON",
        experience_level="Entry Level",
        filtered_jobs=filtered_jobs,
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
        job_match_details_df=job_match_details_df,
        candidate_fit_summary={
            "summary": (
                "Your strongest fit is <strong>Data Science</strong> "
                "with a strong weighted match."
            ),
            "matched_skills": ["Python", "SQL", "Pandas"],
            "missing_skills": ["statistics"],
        },
        dataset_name="test_dataset",
    )

    assert "# JobLens AI Candidate Skill-Gap Report" in report_markdown
    assert "## Analysis Inputs" in report_markdown
    assert "## Fit Overview" in report_markdown
    assert "## Candidate Fit Summary" in report_markdown
    assert "## Recommended Skills to Learn" in report_markdown
    assert "## Role Score Breakdown" in report_markdown
    assert "## Top Matching Jobs" in report_markdown

    assert "test_dataset" in report_markdown
    assert "Data Scientist" in report_markdown
    assert "Toronto ON" in report_markdown
    assert "Entry Level" in report_markdown
    assert "Python, SQL, Pandas" in report_markdown
    assert "Data Science" in report_markdown

    assert "<strong>" not in report_markdown
    assert "</strong>" not in report_markdown


def test_generate_candidate_report_markdown_excludes_zero_score_top_jobs() -> None:
    jobs_df = make_sample_jobs_df()
    current_skills = ["PyTorch"]

    role_skill_weights = build_role_skill_weights(jobs_df)
    role_scores_df = score_roles(jobs_df, user_skills=current_skills)
    recommended_skills_df = get_recommended_skills(
        jobs_df=jobs_df,
        user_skills=current_skills,
        role_skill_weights=role_skill_weights,
        top_n=10,
    )
    job_match_details_df = get_job_match_details(
        filtered_jobs=jobs_df,
        user_skills=current_skills,
    )

    report_markdown = generate_candidate_report_markdown(
        current_skills=current_skills,
        target_roles=["Machine Learning Engineer"],
        location="Any",
        experience_level="Any",
        filtered_jobs=jobs_df,
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
        job_match_details_df=job_match_details_df,
        dataset_name="test_dataset",
    )

    top_jobs_section = report_markdown.split("## Top Matching Jobs", 1)[1]

    assert "Machine Learning Engineer" in top_jobs_section
    assert "Data Scientist" not in top_jobs_section
