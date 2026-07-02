import pandas as pd

from src.resume.resume_analyzer import (
    PRIVACY_NOTE,
    analyze_resume_against_jobs,
    extract_resume_skills,
    merge_candidate_skills,
)


def make_resume_jobs_df() -> pd.DataFrame:
    rows = [
        {
            "title": "Backend Software Engineer",
            "company": "APIWorks",
            "location": "Toronto, ON",
            "experience_level": "Entry Level",
            "role_category": "Software Engineering",
            "description": "Build REST APIs with Python, PostgreSQL, Docker, and AWS.",
            "extracted_skills": ["Python", "REST APIs", "PostgreSQL", "Docker", "AWS"],
        },
        {
            "title": "Machine Learning Engineer",
            "company": "ModelLab",
            "location": "Vancouver, BC",
            "experience_level": "Entry Level",
            "role_category": "AI/ML",
            "description": "Train PyTorch models and deploy MLflow pipelines.",
            "extracted_skills": ["Python", "PyTorch", "MLflow", "model deployment"],
        },
        {
            "title": "Analytics Engineer",
            "company": "MetricWorks",
            "location": "Calgary, AB",
            "experience_level": "Entry Level",
            "role_category": "Analytics",
            "description": "Build dashboards with SQL, dbt, Tableau, and product metrics.",
            "extracted_skills": ["SQL", "dbt", "Tableau", "product metrics"],
        },
    ]
    jobs_df = pd.DataFrame(rows)
    jobs_df["skills_text"] = jobs_df["extracted_skills"].apply(lambda skills: " ".join(skills))
    return jobs_df


def test_extract_resume_skills_uses_aliases_without_false_java_match() -> None:
    resume_text = """
    Built Node.js and JavaScript services with Postgres, REST API endpoints,
    Docker containers, AWS Lambda, and CI/CD workflows.
    """

    skills = extract_resume_skills(resume_text)

    assert "node.js" in skills
    assert "javascript" in skills
    assert "postgresql" in skills
    assert "rest apis" in skills
    assert "ci/cd" in skills
    assert "java" not in skills


def test_merge_candidate_skills_deduplicates_normalized_inputs() -> None:
    merged_skills = merge_candidate_skills(
        current_skills=["Python", "Postgres"],
        resume_skills=["python", "postgresql", "docker"],
    )

    assert merged_skills == ["python", "postgresql", "docker"]


def test_analyze_resume_against_jobs_returns_explainable_match() -> None:
    resume_text = """
    Software engineering project: built FastAPI REST APIs with Python,
    PostgreSQL, Docker, AWS, automated CI/CD, and monitoring dashboards.
    """

    analysis = analyze_resume_against_jobs(
        jobs_df=make_resume_jobs_df(),
        resume_text=resume_text,
        current_skills=["SQL"],
        target_roles=["Backend Engineer"],
    )

    assert analysis["provided"] is True
    assert analysis["privacy_note"] == PRIVACY_NOTE
    assert analysis["fit_score"] > 0
    assert "python" in analysis["combined_skills"]
    assert "backend engineering" in analysis["experience_areas"]
    assert "api development" in analysis["project_keywords"]
    assert analysis["matched_skills"]
    assert analysis["learning_priorities"]
    assert analysis["suggested_resume_keywords"]
    assert analysis["top_matching_jobs"][0]["title"] == "Backend Software Engineer"
    assert analysis["top_matching_jobs"][0]["fit_score"] > 0
    assert analysis["top_matching_jobs"][0]["explanation"]


def test_analyze_resume_against_jobs_handles_empty_profile() -> None:
    analysis = analyze_resume_against_jobs(
        jobs_df=make_resume_jobs_df(),
        resume_text="",
        current_skills=[],
    )

    assert analysis["provided"] is False
    assert analysis["fit_score"] == 0.0
    assert analysis["top_matching_jobs"] == []
    assert "Add resume text" in analysis["explanation"]
